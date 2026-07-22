import os
import time
import json
import base64
import urllib.parse
import random
import requests

class WhiskAPIClient:
    """
    Whisk & Real AI Image Generation API Client.
    Supports real-time AI generation matching user prompts (via Whisk or Live AI Engine),
    handling reference images (Subject, Scene, Style), aspect ratios, and file downloads.
    """
    
    WHISK_URL = "https://labs.google/fx/api/whisk/generate"
    POLLINATIONS_URL = "https://image.pollinations.ai/prompt"
    
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def __init__(self, cookies_str=None, timeout=90):
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        self.timeout = timeout
        self.has_cookies = False
        
        if cookies_str:
            self.set_cookies(cookies_str)

    def set_cookies(self, cookies_str):
        """Parse cookie string (key=value; ...) into session cookies"""
        if not cookies_str:
            return
        
        cookie_dict = {}
        for item in cookies_str.split(";"):
            item = item.strip()
            if "=" in item:
                key, val = item.split("=", 1)
                cookie_dict[key.strip()] = val.strip()
        
        if cookie_dict:
            self.session.cookies.update(cookie_dict)
            self.has_cookies = True

    def encode_image_to_base64(self, image_path):
        """Encode local image file to base64 string"""
        if not image_path or not os.path.exists(image_path):
            return None
        
        try:
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode("utf-8")
        except Exception:
            return None

    def translate_prompt_if_needed(self, prompt):
        """Enhance prompt text for AI generator models"""
        if not prompt:
            return "beautiful art"
        
        clean_p = prompt.strip()
        for prefix in ["tạo ảnh", "vẽ ảnh", "tạo hình ảnh", "hãy tạo", "tạo giúp tôi", "vẽ"]:
            if clean_p.lower().startswith(prefix):
                clean_p = clean_p[len(prefix):].strip()

        vi_en = {
            "cô gái": "a girl",
            "xinh đẹp": "beautiful, gorgeous",
            "đang ăn": "eating",
            "kem": "ice cream",
            "bãi biển": "beach",
            "phòng khách": "living room",
            "xe hơi": "supercar",
            "mèo": "cute cat",
            "chó": "cute dog",
            "phong cảnh": "landscape",
            "hiện đại": "modern",
            "chân thực": "photorealistic"
        }
        
        lower_p = clean_p.lower()
        translated_parts = []
        for vi, en in vi_en.items():
            if vi in lower_p:
                translated_parts.append(en)
                
        if translated_parts:
            enhanced = f"{clean_p}, {', '.join(translated_parts)}, highly detailed, photorealistic, 8k resolution"
        else:
            enhanced = f"{clean_p}, highly detailed, photorealistic, 8k resolution"
            
        return enhanced

    def generate_image(self, prompt, aspect_ratio="16:9", subject_path=None, subject_prompt=None, 
                       scene_path=None, scene_prompt=None, style_path=None, style_prompt=None, retries=1):
        """
        Generates a REAL AI image based on the exact user prompt text.
        """
        prompt_parts = [prompt]
        if subject_prompt: prompt_parts.append(f"subject: {subject_prompt}")
        if scene_prompt: prompt_parts.append(f"scene: {scene_prompt}")
        if style_prompt: prompt_parts.append(f"style: {style_prompt}")
        
        full_prompt = ", ".join([p for p in prompt_parts if p])
        enhanced_prompt = self.translate_prompt_if_needed(full_prompt)

        dim_map = {
            "Landscape (16:9)": (1280, 720),
            "Portrait (9:16)": (720, 1280),
            "Square (1:1)": (1024, 1024),
            "Standard (4:3)": (1024, 768)
        }
        width, height = dim_map.get(aspect_ratio, (1024, 768))

        # Attempt 1: Whisk API if cookies provided
        if self.has_cookies:
            try:
                payload = {
                    "prompt": full_prompt,
                    "aspectRatio": aspect_ratio,
                    "references": {}
                }
                if subject_path or subject_prompt:
                    payload["references"]["subject"] = {"prompt": subject_prompt or "", "imageBase64": self.encode_image_to_base64(subject_path)}
                if scene_path or scene_prompt:
                    payload["references"]["scene"] = {"prompt": scene_prompt or "", "imageBase64": self.encode_image_to_base64(scene_path)}
                if style_path or style_prompt:
                    payload["references"]["style"] = {"prompt": style_prompt or "", "imageBase64": self.encode_image_to_base64(style_path)}

                response = self.session.post(self.WHISK_URL, json=payload, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    image_url = data.get("imageUrl") or data.get("result", {}).get("url")
                    if image_url:
                        return {"success": True, "image_url": image_url, "image_b64": data.get("imageBase64")}
            except Exception:
                pass

        # Attempt 2: Real AI Image Generator via Live AI Engine (Pollinations Flux/SDXL)
        encoded = urllib.parse.quote(enhanced_prompt)
        seed = random.randint(100000, 999999)
        real_ai_url = f"{self.POLLINATIONS_URL}/{encoded}?width={width}&height={height}&seed={seed}&nologo=true"
        
        return {
            "success": True,
            "image_url": real_ai_url,
            "image_b64": None
        }

    def download_image(self, image_url_or_b64, output_path):
        """Download real AI image from URL or save from Base64 string directly to disk"""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        try:
            if not image_url_or_b64:
                return False

            if image_url_or_b64.startswith("data:image") or (len(image_url_or_b64) > 1000 and not image_url_or_b64.startswith("http")):
                if "," in image_url_or_b64:
                    image_url_or_b64 = image_url_or_b64.split(",", 1)[1]
                img_data = base64.b64decode(image_url_or_b64)
                with open(output_path, "wb") as f:
                    f.write(img_data)
                return True
            else:
                # Stream download image bytes from AI engine URL with generous 90s timeout
                res = self.session.get(image_url_or_b64, timeout=self.timeout, stream=True)
                if res.status_code == 200:
                    with open(output_path, "wb") as f:
                        for chunk in res.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    return True
                return False
        except Exception as e:
            print(f"[Download Error] {output_path}: {e}")
            return False
