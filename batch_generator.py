import os
import sys
import csv
import json
import time
import re
import hashlib
import unicodedata
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from whisk_api import WhiskAPIClient

def generate_smart_filename(prompt, index, extension="png"):
    """
    Generate Smart Filename based on Prompt Slug, Order Index, and Hash.
    Example: "Tạo ảnh 1 cô gái xinh đẹp đang ăn kem" -> "001_co_gai_xinh_dep_dang_an_kem_8a3f.png"
    """
    if not prompt:
        slug = "image"
    else:
        # Clean prefix words like "tạo ảnh", "vẽ"
        clean = prompt.strip()
        for prefix in ["tạo ảnh", "vẽ ảnh", "tạo hình ảnh", "hãy tạo", "tạo giúp tôi", "vẽ"]:
            if clean.lower().startswith(prefix):
                clean = clean[len(prefix):].strip()
                
        # Normalize unicode to remove Vietnamese diacritics
        nfkd = unicodedata.normalize('NFKD', clean)
        ascii_str = ''.join([c for c in nfkd if not unicodedata.combining(c)])
        
        # Replace non-alphanumeric characters with underscore
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', ascii_str).strip('_').lower()
        
        # Truncate to 35 characters for readable clean filenames
        if len(slug) > 35:
            slug = slug[:35].rstrip('_')
            
        if not slug:
            slug = "image"

    # Short hash based on prompt text to guarantee uniqueness
    hash_suffix = hashlib.md5(f"{prompt}_{index}_{time.time()}".encode('utf-8')).hexdigest()[:4]
    
    return f"{index:03d}_{slug}_{hash_suffix}.{extension}"

class BatchProcessor:
    """
    Batch Automation Processor for reading prompt files (CSV/TXT/JSON),
    executing parallel requests, downloading images with Smart Naming to disk, and generating reports.
    """
    
    def __init__(self, cookies_str=None, output_dir="./images", threads=10, aspect_ratio="16:9"):
        self.client = WhiskAPIClient(cookies_str=cookies_str)
        self.output_dir = output_dir
        self.threads = max(1, min(threads, 50))
        self.aspect_ratio = aspect_ratio
        self.is_running = False
        self.stop_requested = False

    def load_prompts_from_file(self, filepath):
        """Read prompts from CSV, TXT, or JSON file"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        ext = os.path.splitext(filepath)[1].lower()
        items = []

        if ext == ".csv":
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    prompt = row.get("Prompt") or row.get("prompt") or row.get("STT") or ""
                    if not prompt:
                        values = list(row.values())
                        prompt = values[1] if len(values) > 1 else values[0] if values else ""
                    
                    if prompt:
                        items.append({
                            "id": idx + 1,
                            "prompt": prompt.strip(),
                            "subject_path": row.get("Subject_Path", "").strip(),
                            "subject_prompt": row.get("Subject_Prompt", "").strip(),
                            "scene_path": row.get("Scene_Path", "").strip(),
                            "scene_prompt": row.get("Scene_Prompt", "").strip(),
                            "style_path": row.get("Style_Path", "").strip(),
                            "style_prompt": row.get("Style_Prompt", "").strip()
                        })

        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for idx, entry in enumerate(data):
                        if isinstance(entry, str):
                            items.append({"id": idx + 1, "prompt": entry.strip()})
                        elif isinstance(entry, dict):
                            entry["id"] = idx + 1
                            items.append(entry)

        else: # Default TXT (one prompt per line)
            with open(filepath, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    line = line.strip()
                    if line:
                        items.append({"id": idx + 1, "prompt": line})

        return items

    def process_single_item(self, item, start_index=1, log_callback=None):
        """Process a single prompt item: API request + download image with Smart Naming"""
        if self.stop_requested:
            return {"id": item["id"], "status": "stopped", "error": "User cancelled"}

        idx = item["id"]
        prompt = item["prompt"]
        item_order = start_index + idx - 1
        
        if log_callback:
            log_callback(f"🚀 [Luồng] Đang xử lý #{idx}: '{prompt[:40]}...'", "info")

        # Call API
        result = self.client.generate_image(
            prompt=prompt,
            aspect_ratio=self.aspect_ratio,
            subject_path=item.get("subject_path"),
            subject_prompt=item.get("subject_prompt"),
            scene_path=item.get("scene_path"),
            scene_prompt=item.get("scene_prompt"),
            style_path=item.get("style_path"),
            style_prompt=item.get("style_prompt")
        )

        if not result["success"]:
            if log_callback:
                log_callback(f"❌ [Lỗi] #{idx}: {result.get('error')}", "error")
            return {
                "id": idx,
                "prompt": prompt,
                "status": "error",
                "error": result.get("error"),
                "file_path": None,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        # Smart Image Naming
        smart_filename = generate_smart_filename(prompt, item_order, extension="png")
        save_path = os.path.join(self.output_dir, smart_filename)
        
        target = result.get("image_url") or result.get("image_b64")
        dl_success = self.client.download_image(target, save_path)

        if dl_success:
            if log_callback:
                log_callback(f"✅ [Tải thành công] #{idx} -> {smart_filename}", "success")
            return {
                "id": idx,
                "prompt": prompt,
                "status": "success",
                "file_path": save_path,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            if log_callback:
                log_callback(f"❌ [Lỗi tải file] #{idx}: Không thể lưu ảnh vào {save_path}", "error")
            return {
                "id": idx,
                "prompt": prompt,
                "status": "error",
                "error": "Lỗi lưu file ảnh",
                "file_path": None,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    def run_batch(self, items, start_index=1, progress_callback=None, log_callback=None):
        """
        Run batch processing across items using ThreadPoolExecutor.
        """
        self.is_running = True
        self.stop_requested = False
        os.makedirs(self.output_dir, exist_ok=True)
        
        results = []
        total = len(items)

        if log_callback:
            log_callback(f"⚡ Bắt đầu tiến trình tự động với {self.threads} luồng song song...", "info")

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            future_to_item = {
                executor.submit(self.process_single_item, item, start_index, log_callback): item 
                for item in items
            }

            completed = 0
            for future in as_completed(future_to_item):
                if self.stop_requested:
                    break
                
                try:
                    res = future.result()
                    results.append(res)
                except Exception as exc:
                    item = future_to_item[future]
                    results.append({
                        "id": item["id"],
                        "prompt": item["prompt"],
                        "status": "error",
                        "error": str(exc),
                        "file_path": None,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

                completed += 1
                if progress_callback:
                    progress_callback(completed, total, results)

        self.is_running = False
        
        # Export summary report CSV
        report_path = os.path.join(self.output_dir, "results_summary.csv")
        self.export_report(results, report_path)
        
        if log_callback:
            log_callback(f"📊 [Hoàn thành] Đã xuất báo cáo chi tiết ra: {report_path}", "success")

        return results

    def stop(self):
        self.stop_requested = True

    def export_report(self, results, output_csv):
        """Write execution results to summary CSV file"""
        fieldnames = ["id", "prompt", "status", "file_path", "error", "timestamp"]
        with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in sorted(results, key=lambda x: x["id"]):
                writer.writerow(r)

# ==============================================================================
# CLI EXECUTION MAIN
# ==============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Whisk Automated Batch Image Generator & Downloader")
    parser.add_argument("-i", "--input", required=True, help="Path to input prompt file (.csv, .txt, .json)")
    parser.add_argument("-o", "--output", default="./images", help="Output directory to save images (default: ./images)")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Number of concurrent threads (default: 10)")
    parser.add_argument("-c", "--cookies", default=None, help="Whisk Session Cookies string")
    parser.add_argument("-r", "--ratio", default="16:9", help="Aspect Ratio (default: 16:9)")

    args = parser.parse_args()

    processor = BatchProcessor(
        cookies_str=args.cookies,
        output_dir=args.output,
        threads=args.threads,
        aspect_ratio=args.ratio
    )

    try:
        items = processor.load_prompts_from_file(args.input)
        print(f"[Whisk Batch Engine] Loaded {len(items)} prompts from {args.input}")
        
        def cli_log(msg, mtype):
            print(f"[{mtype.upper()}] {msg}")

        def cli_progress(curr, total, res):
            pct = int((curr / total) * 100)
            print(f"Progress: {curr}/{total} ({pct}%) completed...")

        results = processor.run_batch(items, progress_callback=cli_progress, log_callback=cli_log)
        print("\n[Done] All images generated and downloaded successfully with Smart Naming!")

    except Exception as e:
        print(f"[Fatal Error] {e}")
        sys.exit(1)
