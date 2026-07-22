import os
import sys
import time
import json
import random
import threading
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from whisk_api import WhiskAPIClient
from batch_generator import BatchProcessor

# ==============================================================================
# COLOR PALETTE & STYLES (Light & Blue Replica Theme from Screenshot)
# ==============================================================================
BG_MAIN = "#f0f4f8"
BG_CARD = "#ffffff"
BG_INPUT = "#ffffff"
BORDER_COLOR = "#cbd5e1"
HEADER_BLUE = "#0284c7"
TEXT_MAIN = "#1e293b"
TEXT_MUTED = "#64748b"

COLOR_GOLD = "#eab308"      # Nút Chọn
COLOR_BLUE = "#0284c7"      # Nút Kiểm tra / Standard Blue
COLOR_RED = "#ef4444"       # Nút Xóa / Delete
COLOR_GREEN = "#10b981"     # Nút Bắt đầu
COLOR_ORANGE = "#f59e0b"    # Nút Chi tiết lỗi

CONFIG_FILE = "config.json"

class WhiskTkinterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Whisk Image Generator Pro by creatornow.com.vn")
        self.geometry("1400x900")
        self.configure(bg=BG_MAIN)

        self.prompts = [
            "A breathtaking panoramic illustration of earthy futuristic landscape with glowing waterfalls",
            "A dramatic editorial illustration of three cybernetic warriors in neon armor",
            "A majestic and slightly menacing oil painting of a mythical dragon over ancient ruins",
            "A sweeping illustrated map of the Austro-Hungarian empire in steampunk style",
            "Realistic photography of a sleek high-tech AI camera lens with soft studio lighting"
        ]
        self.statuses = ["Đang chờ"] * len(self.prompts)
        self.processor = None
        self.is_running = False

        self.setup_styles()
        self.init_ui()
        self.load_state()  # Load saved state on startup
        
        # Intercept window close event to automatically save state
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Base Widgets Styling
        style.configure(".", background=BG_MAIN, foreground=TEXT_MAIN, font=("Segoe UI", 10))
        style.configure("TLabelframe", background=BG_CARD, bordercolor=BORDER_COLOR)
        style.configure("TLabelframe.Label", background=BG_CARD, foreground="#0f172a", font=("Segoe UI", 10, "bold"))

        # Treeview (Prompt Table - Dark Header & Clean White Lines)
        style.configure("Treeview", background="#ffffff", foreground=TEXT_MAIN, fieldbackground="#ffffff", rowheight=28)
        style.configure("Treeview.Heading", background="#1e293b", foreground="#ffffff", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#0284c7")], foreground=[("selected", "#ffffff")])

        # Progressbar
        style.configure("TProgressbar", thickness=10, troughcolor="#e2e8f0", background=HEADER_BLUE)

    def init_ui(self):
        # 0. Top System Menu Bar (Tools, License, Help)
        sys_bar = tk.Frame(self, bg="#ffffff", height=26)
        sys_bar.pack(fill="x", side="top")
        tk.Label(sys_bar, text="🔧 Toolcs   📜 License   ❓ Help", font=("Segoe UI", 9), fg="#475569", bg="#ffffff").pack(side="left", padx=12, pady=3)

        # 1. Header Banner - Blue Gradient
        header_frame = tk.Frame(self, bg=HEADER_BLUE, height=55)
        header_frame.pack(fill="x", side="top")
        
        # Logo Box Red
        logo_box = tk.Frame(header_frame, bg="#dc2626", width=38, height=38)
        logo_box.pack(side="left", padx=(14, 10), pady=8)
        logo_box.pack_propagate(False)
        tk.Label(logo_box, text="C", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#dc2626").pack()
        tk.Label(logo_box, text="CREATOR NOW", font=("Segoe UI", 5, "bold"), fg="#ffffff", bg="#dc2626").pack()

        brand_lbl = tk.Label(header_frame, text="Whisk Image Generator Pro", font=("Segoe UI", 16, "bold"), fg="#ffffff", bg=HEADER_BLUE)
        brand_lbl.pack(side="left", pady=4)
        sub_lbl = tk.Label(header_frame, text="by creatornow.com.vn", font=("Segoe UI", 10, "italic"), fg="#e0f2fe", bg=HEADER_BLUE)
        sub_lbl.pack(side="left", padx=8, pady=4)

        # 2. Workspace Layout
        workspace = tk.Frame(self, bg=BG_MAIN)
        workspace.pack(fill="both", expand=True, padx=12, pady=12)

        # Left Panel
        left_panel = tk.Frame(workspace, bg=BG_MAIN, width=470)
        left_panel.pack(side="left", fill="both", padx=(0, 6))

        # Right Panel
        right_panel = tk.Frame(workspace, bg=BG_MAIN)
        right_panel.pack(side="right", fill="both", expand=True, padx=(6, 0))

        self.build_left_panel(left_panel)
        self.build_right_panel(right_panel)

    def build_left_panel(self, parent):
        # ----------------------------------------------------------------------
        # Group 1: Reference Images
        # ----------------------------------------------------------------------
        ref_lf = ttk.LabelFrame(parent, text="🖼️ Ảnh Tham Chiếu (Reference Images)")
        ref_lf.pack(fill="x", pady=(0, 10))

        self.ref_widgets = {}
        for key, title, hint in [
            ("Subject", "Subject:", "VD: 'young woman, brown eyes, long black hair, oval face' - Mô tả chi tiết khuôn mặt để AI copy chính xác hơn"),
            ("Scene", "Scene:", "VD: 'modern office, glass windows, natural lighting' - Mô tả chi tiết môi trường"),
            ("Style", "Style:", "VD: 'realistic photography, soft lighting, professional portrait' - Mô tả phong cách nghệ thuật")
        ]:
            item_frame = tk.Frame(ref_lf, bg=BG_CARD)
            item_frame.pack(fill="x", padx=10, pady=4)

            tk.Label(item_frame, text=title, font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w")

            row_frame = tk.Frame(item_frame, bg=BG_CARD)
            row_frame.pack(fill="x", pady=2)

            entry_path = tk.Entry(row_frame, bg=BG_INPUT, fg=TEXT_MAIN, relief="solid", bd=1)
            entry_path.pack(side="left", fill="x", expand=True, padx=(0, 4))

            btn_browse = tk.Button(row_frame, text="📁 Chọn", bg=COLOR_GOLD, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=lambda k=key: self.browse_ref(k))
            btn_browse.pack(side="left", padx=2)

            btn_check = tk.Button(row_frame, text="🔍 Kiểm tra", bg=COLOR_BLUE, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=lambda k=key: self.check_ref(k))
            btn_check.pack(side="left", padx=2)

            btn_clear = tk.Button(row_frame, text="✖", bg=COLOR_RED, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=lambda k=key: self.clear_ref(k))
            btn_clear.pack(side="left", padx=2)

            tk.Label(item_frame, text="Prompt:", font=("Segoe UI", 8, "bold"), fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w")
            entry_prompt = tk.Entry(item_frame, bg=BG_INPUT, fg=TEXT_MUTED, relief="solid", bd=1)
            entry_prompt.insert(0, hint)
            entry_prompt.pack(fill="x", pady=(0, 4))

            self.ref_widgets[key] = (entry_path, entry_prompt)

        # ----------------------------------------------------------------------
        # Group 2: Settings
        # ----------------------------------------------------------------------
        sett_lf = ttk.LabelFrame(parent, text="⚙️ Cài đặt (Settings)")
        sett_lf.pack(fill="x", pady=(0, 10))

        sett_frame = tk.Frame(sett_lf, bg=BG_CARD)
        sett_frame.pack(fill="x", padx=10, pady=6)

        tk.Label(sett_frame, text="🔑 Cookies:", font=("Segoe UI", 9, "bold"), fg=TEXT_MAIN, bg=BG_CARD).pack(anchor="w")
        self.txt_cookies = tk.Text(sett_frame, bg=BG_INPUT, fg=TEXT_MAIN, height=3, relief="solid", bd=1)
        self.txt_cookies.pack(fill="x", pady=(2, 4))

        cookie_btns_frame = tk.Frame(sett_frame, bg=BG_CARD)
        cookie_btns_frame.pack(fill="x", pady=(0, 6))

        btn_save_cookies = tk.Button(cookie_btns_frame, text="💾 Lưu Cookies", bg=COLOR_BLUE, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=self.save_cookies)
        btn_save_cookies.pack(side="left", fill="x", expand=True, padx=(0, 2))

        btn_check_cookies = tk.Button(cookie_btns_frame, text="🔍 Kiểm tra Cookies", bg=COLOR_GOLD, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=self.check_cookies)
        btn_check_cookies.pack(side="right", fill="x", expand=True, padx=(2, 0))

        # Grid settings
        grid_f = tk.Frame(sett_frame, bg=BG_CARD)
        grid_f.pack(fill="x")

        tk.Label(grid_f, text="Số luồng:", bg=BG_CARD, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=3)
        self.spin_threads = tk.Spinbox(grid_f, from_=1, to=50, width=6, bg=BG_INPUT, fg=TEXT_MAIN, relief="solid", bd=1)
        self.spin_threads.delete(0, "end")
        self.spin_threads.insert(0, "10")
        self.spin_threads.grid(row=0, column=1, sticky="w", padx=4)

        tk.Label(grid_f, text="Tỷ lệ:", bg=BG_CARD, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=(10, 4))
        self.cmb_ratio = ttk.Combobox(grid_f, values=["Landscape (16:9)", "Portrait (9:16)", "Square (1:1)", "Standard (4:3)"], width=14)
        self.cmb_ratio.current(0)
        self.cmb_ratio.grid(row=0, column=3, sticky="w")

        tk.Label(grid_f, text="Thư mục:", bg=BG_CARD, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=3)
        self.entry_outdir = tk.Entry(grid_f, bg=BG_INPUT, fg=TEXT_MAIN, relief="solid", bd=1, width=20)
        self.entry_outdir.insert(0, "./images")
        self.entry_outdir.grid(row=1, column=1, columnspan=2, sticky="we", padx=4)
        btn_browse_dir = tk.Button(grid_f, text="...", bg=COLOR_BLUE, fg="#ffffff", relief="flat", command=self.browse_outdir)
        btn_browse_dir.grid(row=1, column=3, sticky="w")

        # ----------------------------------------------------------------------
        # Control Action Buttons Row
        # ----------------------------------------------------------------------
        act_frame = tk.Frame(parent, bg=BG_MAIN)
        act_frame.pack(fill="x", pady=6)

        self.btn_start = tk.Button(act_frame, text="▶ Bắt đầu", bg=COLOR_GREEN, fg="#ffffff", font=("Segoe UI", 10, "bold"), relief="flat", height=2, command=self.start_batch)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_stop = tk.Button(act_frame, text="⏹ Dừng", bg=COLOR_BLUE, fg="#ffffff", font=("Segoe UI", 10, "bold"), relief="flat", height=2, state="disabled", command=self.stop_batch)
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=2)

        btn_retry = tk.Button(act_frame, text="🔄 Retry với prompt hiện tại", bg="#0891b2", fg="#ffffff", font=("Segoe UI", 10, "bold"), relief="flat", height=2, command=self.retry_batch)
        btn_retry.pack(side="left", fill="x", expand=True, padx=2)

        btn_err = tk.Button(act_frame, text="⚠️ Chi tiết lỗi", bg=COLOR_ORANGE, fg="#ffffff", font=("Segoe UI", 10, "bold"), relief="flat", height=2, command=self.show_errors)
        btn_err.pack(side="left", fill="x", expand=True, padx=2)

    def build_right_panel(self, parent):
        # Prompts Management LabelFrame
        prompts_lf = ttk.LabelFrame(parent, text="📋 Prompts Management")
        prompts_lf.pack(fill="both", expand=True, pady=(0, 10))

        # Notebook
        self.notebook = ttk.Notebook(prompts_lf)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=6)

        # Tab 1: Table Editor
        tab_table = tk.Frame(self.notebook, bg=BG_CARD)
        self.notebook.add(tab_table, text="📊 Table Editor")

        # Treeview Table
        self.tree = ttk.Treeview(tab_table, columns=("STT", "Prompt", "Status"), show="headings", height=8)
        self.tree.heading("STT", text="STT")
        self.tree.heading("Prompt", text="Prompt")
        self.tree.heading("Status", text="Tiến độ")

        self.tree.column("STT", width=50, anchor="center")
        self.tree.column("Prompt", width=500, anchor="w")
        self.tree.column("Status", width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

        # Toolbar Buttons Group 1 & 2
        tb_frame = tk.Frame(tab_table, bg=BG_CARD)
        tb_frame.pack(fill="x", padx=4, pady=4)

        btn_add = tk.Button(tb_frame, text="➕ Thêm dòng", bg=COLOR_BLUE, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=self.add_prompt)
        btn_add.pack(side="left", padx=2)
        btn_del = tk.Button(tb_frame, text="➖ Xóa dòng", bg=COLOR_BLUE, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=self.del_prompt)
        btn_del.pack(side="left", padx=2)
        btn_up = tk.Button(tb_frame, text="⬆ Lên", bg=COLOR_BLUE, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=self.move_up)
        btn_up.pack(side="left", padx=2)
        btn_down = tk.Button(tb_frame, text="⬇ Xuống", bg=COLOR_BLUE, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=self.move_down)
        btn_down.pack(side="left", padx=2)

        btn_clear_all = tk.Button(tb_frame, text="🗑 Xóa tất cả", bg=COLOR_BLUE, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=self.clear_all)
        btn_clear_all.pack(side="right", padx=2)
        btn_sync = tk.Button(tb_frame, text="🔄 Sync Text ↔ Table", bg=COLOR_BLUE, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=self.sync_text_to_table)
        btn_sync.pack(side="right", padx=2)
        btn_export = tk.Button(tb_frame, text="💾 Export ra file", bg=COLOR_BLUE, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=self.export_file)
        btn_export.pack(side="right", padx=2)
        btn_import = tk.Button(tb_frame, text="📁 Import từ file", bg=COLOR_BLUE, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=self.import_file)
        btn_import.pack(side="right", padx=2)

        # Tab 2: Text Editor
        tab_text = tk.Frame(self.notebook, bg=BG_CARD)
        self.notebook.add(tab_text, text="📝 Text Editor")

        btn_apply = tk.Button(tab_text, text="🔄 Cập nhật vào Bảng Prompt", bg=COLOR_BLUE, fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", command=self.sync_text_to_table)
        btn_apply.pack(anchor="w", pady=4, padx=4)

        self.txt_editor = scrolledtext.ScrolledText(tab_text, bg=BG_INPUT, fg=TEXT_MAIN, height=8, relief="solid", bd=1)
        self.txt_editor.pack(fill="both", expand=True, padx=4, pady=4)

        # Progress Section
        prog_frame = ttk.LabelFrame(parent, text="📊 Tiến độ")
        prog_frame.pack(fill="x", pady=(0, 10))

        prog_inner = tk.Frame(prog_frame, bg=BG_CARD)
        prog_inner.pack(fill="x", padx=10, pady=6)

        tk.Label(prog_inner, text="Tổng thể:", bg=BG_CARD, fg=TEXT_MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        self.pbar = ttk.Progressbar(prog_inner, length=100, mode="determinate")
        self.pbar.pack(fill="x", pady=2)

        self.lbl_progress = tk.Label(prog_inner, text="Sẵn sàng", bg=BG_CARD, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold"))
        self.lbl_progress.pack(anchor="w", pady=(2, 4))

        metrics_f = tk.Frame(prog_inner, bg=BG_CARD)
        metrics_f.pack(fill="x")

        self.lbl_success = tk.Label(metrics_f, text="✓ Thành công: 0", bg="#dcfce7", fg="#15803d", font=("Segoe UI", 9, "bold"), padx=8, pady=3)
        self.lbl_error = tk.Label(metrics_f, text="❌ Lỗi: 0", bg="#fee2e2", fg="#b91c1c", font=("Segoe UI", 9, "bold"), padx=8, pady=3)
        self.lbl_pending = tk.Label(metrics_f, text="⏳ Đang chờ: 0", bg="#fef3c7", fg="#92400e", font=("Segoe UI", 9, "bold"), padx=8, pady=3)

        self.lbl_success.pack(side="left", padx=(0, 6))
        self.lbl_error.pack(side="left", padx=6)
        self.lbl_pending.pack(side="left", padx=6)

        # Log Section
        log_frame = ttk.LabelFrame(parent, text="📜 Log")
        log_frame.pack(fill="both", expand=True)

        log_inner = tk.Frame(log_frame, bg=BG_CARD)
        log_inner.pack(fill="both", expand=True, padx=10, pady=4)

        self.txt_log = scrolledtext.ScrolledText(log_inner, bg="#ffffff", fg=TEXT_MAIN, font=("Consolas", 9), height=5, relief="solid", bd=1)
        self.txt_log.pack(fill="both", expand=True)

        btn_clear_log = tk.Button(log_inner, text="🗑 Xóa log", bg=COLOR_BLUE, fg="#ffffff", font=("Segoe UI", 8, "bold"), relief="flat", command=lambda: self.txt_log.delete("1.0", "end"))
        btn_clear_log.pack(anchor="e", pady=4)

    # --------------------------------------------------------------------------
    # STATE PERSISTENCE (SAVE & LOAD STATE TO DISK)
    # --------------------------------------------------------------------------
    def save_state(self):
        """Save full application state to config.json"""
        try:
            state = {
                "cookies": self.txt_cookies.get("1.0", "end").strip(),
                "threads": self.spin_threads.get(),
                "aspect_ratio": self.cmb_ratio.get(),
                "output_dir": self.entry_outdir.get(),
                "ref_subject_path": self.ref_widgets["Subject"][0].get(),
                "ref_subject_prompt": self.ref_widgets["Subject"][1].get(),
                "ref_scene_path": self.ref_widgets["Scene"][0].get(),
                "ref_scene_prompt": self.ref_widgets["Scene"][1].get(),
                "ref_style_path": self.ref_widgets["Style"][0].get(),
                "ref_style_prompt": self.ref_widgets["Style"][1].get(),
                "prompts": self.prompts
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[State Save Warning] {e}")

    def load_state(self):
        """Restore full application state from config.json"""
        if not os.path.exists(CONFIG_FILE):
            return

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)

            if "cookies" in state:
                self.txt_cookies.delete("1.0", "end")
                self.txt_cookies.insert("1.0", state["cookies"])

            if "threads" in state:
                self.spin_threads.delete(0, "end")
                self.spin_threads.insert(0, str(state["threads"]))

            if "aspect_ratio" in state and state["aspect_ratio"]:
                self.cmb_ratio.set(state["aspect_ratio"])

            if "output_dir" in state and state["output_dir"]:
                self.entry_outdir.delete(0, "end")
                self.entry_outdir.insert(0, state["output_dir"])

            # Restore References
            for k in ["Subject", "Scene", "Style"]:
                path_key = f"ref_{k.lower()}_path"
                prompt_key = f"ref_{k.lower()}_prompt"
                if path_key in state and state[path_key]:
                    self.ref_widgets[k][0].delete(0, "end")
                    self.ref_widgets[k][0].insert(0, state[path_key])
                if prompt_key in state and state[prompt_key]:
                    self.ref_widgets[k][1].delete(0, "end")
                    self.ref_widgets[k][1].insert(0, state[prompt_key])

            # Restore Prompts List
            if "prompts" in state and isinstance(state["prompts"], list) and len(state["prompts"]) > 0:
                self.prompts = state["prompts"]
                self.statuses = ["Đang chờ"] * len(self.prompts)
                self.load_table_data()

            self.log("💾 Đã khôi phục toàn bộ trạng thái và cài đặt từ phiên làm việc trước!", "info")
        except Exception as e:
            print(f"[State Load Error] {e}")

    def on_close(self):
        """Handle window close event: save state then destroy"""
        self.save_state()
        self.destroy()

    # --------------------------------------------------------------------------
    # TABLE LOGIC & HANDLERS
    # --------------------------------------------------------------------------
    def log(self, message, msg_type="info"):
        now_str = datetime.now().strftime("[%H:%M:%S]")
        self.txt_log.insert("end", f"{now_str} {message}\n")
        self.txt_log.see("end")

    def load_table_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, (p, s) in enumerate(zip(self.prompts, self.statuses)):
            self.tree.insert("", "end", values=(idx + 1, p, s))

        self.update_metrics()

    def update_metrics(self):
        succ = self.statuses.count("Thành công")
        err = self.statuses.count("Lỗi")
        pend = self.statuses.count("Đang chờ")

        self.lbl_success.config(text=f"✓ Thành công: {succ}")
        self.lbl_error.config(text=f"❌ Lỗi: {err}")
        self.lbl_pending.config(text=f"⏳ Đang chờ: {pend}")

    def browse_ref(self, key):
        fn = filedialog.askopenfilename(title=f"Chọn ảnh tham chiếu [{key}]", filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if fn:
            self.ref_widgets[key][0].delete(0, "end")
            self.ref_widgets[key][0].insert(0, fn)
            self.log(f"Đã chọn ảnh tham chiếu [{key}]: {fn}")
            self.save_state()

    def check_ref(self, key):
        path = self.ref_widgets[key][0].get()
        if not path:
            messagebox.showwarning("Cảnh báo", f"Tham chiếu [{key}] chưa chọn file ảnh!")
        else:
            messagebox.showinfo("Thông báo", f"Tham chiếu [{key}] HỢP LỆ!\nPath: {path}")

    def clear_ref(self, key):
        self.ref_widgets[key][0].delete(0, "end")
        self.save_state()

    def check_cookies(self):
        cookies = self.txt_cookies.get("1.0", "end").strip()
        if not cookies:
            self.log("⚠️ Chưa nhập Cookies. Phần mềm sẽ tự động dùng Engine AI mặc định.", "warning")
            messagebox.showwarning("Chưa nhập Cookies", "Bạn chưa nhập Cookies!\n\nHệ thống sẽ tự động sử dụng Engine AI mặc định để sinh ảnh theo đúng prompt.")
            return False

        self.log("🔍 Đang kiểm tra tính hợp lệ của Cookies...", "info")
        client = WhiskAPIClient()
        is_valid, msg = client.validate_cookies(cookies)

        if is_valid:
            self.log(f"🟩 {msg}", "success")
            messagebox.showinfo("Cookie Hợp Lệ", f"✅ {msg}")
            return True
        else:
            self.log(f"🟥 {msg}", "error")
            messagebox.showerror("Lỗi Cookies", f"❌ {msg}")
            return False

    def save_cookies(self):
        cookies = self.txt_cookies.get("1.0", "end").strip()
        self.save_state()
        if not cookies:
            self.log("🟨 Đã lưu cấu hình (Không sử dụng Cookies).", "info")
            messagebox.showinfo("Thông báo", "Đã lưu cài đặt! Phần mềm sẽ tự động sinh ảnh bằng Engine AI mặc định.")
            return

        is_valid = self.check_cookies()
        if is_valid:
            self.log("🟩 Đã lưu Cookies thành công vào phiên làm việc.", "success")

    def browse_outdir(self):
        d = filedialog.askdirectory(initialdir="./images")
        if d:
            self.entry_outdir.delete(0, "end")
            self.entry_outdir.insert(0, d)
            self.save_state()

    def add_prompt(self):
        self.prompts.append("Prompt sinh ảnh mới...")
        self.statuses.append("Đang chờ")
        self.load_table_data()
        self.save_state()

    def del_prompt(self):
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            del self.prompts[idx]
            del self.statuses[idx]
            self.load_table_data()
            self.save_state()

    def move_up(self):
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            if idx > 0:
                self.prompts[idx], self.prompts[idx - 1] = self.prompts[idx - 1], self.prompts[idx]
                self.statuses[idx], self.statuses[idx - 1] = self.statuses[idx - 1], self.statuses[idx]
                self.load_table_data()
                self.save_state()

    def move_down(self):
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            if idx < len(self.prompts) - 1:
                self.prompts[idx], self.prompts[idx + 1] = self.prompts[idx + 1], self.prompts[idx]
                self.statuses[idx], self.statuses[idx + 1] = self.statuses[idx + 1], self.statuses[idx]
                self.load_table_data()
                self.save_state()

    def clear_all(self):
        if messagebox.askyesno("Xác nhận", "Xóa toàn bộ danh sách prompt?"):
            self.prompts.clear()
            self.statuses.clear()
            self.load_table_data()
            self.save_state()

    def sync_text_to_table(self):
        text = self.txt_editor.get("1.0", "end").strip()
        if text:
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            self.prompts = lines
            self.statuses = ["Đang chờ"] * len(lines)
            self.load_table_data()
            self.notebook.select(0)
            self.save_state()
            self.log(f"🟨 Đã đồng bộ {len(lines)} prompts từ Text Editor")

    def import_file(self):
        fn = filedialog.askopenfilename(filetypes=[("Prompt Files", "*.csv *.txt *.json")])
        if fn:
            try:
                proc = BatchProcessor()
                items = proc.load_prompts_from_file(fn)
                self.prompts = [item["prompt"] for item in items]
                self.statuses = ["Đang chờ"] * len(items)
                self.load_table_data()
                self.save_state()
                self.log(f"🟩 Đã import {len(items)} prompts từ file: {fn}")
            except Exception as e:
                messagebox.showerror("Lỗi Import", str(e))

    def export_file(self):
        fn = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv"), ("Text Files", "*.txt")])
        if fn:
            with open(fn, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["STT", "Prompt"])
                for idx, p in enumerate(self.prompts):
                    writer.writerow([idx + 1, p])
            self.log(f"🟩 Đã xuất {len(self.prompts)} prompts ra file: {fn}")

    # --------------------------------------------------------------------------
    # BATCH PROCESS ENGINE INTEGRATION (WHISK BACKEND AUTOMATION)
    # --------------------------------------------------------------------------
    def start_batch(self):
        if not self.prompts:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập danh sách prompt trước!")
            return

        self.save_state()

        cookies = self.txt_cookies.get("1.0", "end").strip()
        if cookies:
            client = WhiskAPIClient()
            is_valid, msg = client.validate_cookies(cookies)
            if not is_valid:
                res = messagebox.askyesno("Lỗi Cookies", f"❌ {msg}\n\nBạn có muốn tiếp tục sinh ảnh bằng Engine AI mặc định (Flux.1 / SDXL) không?")
                if not res:
                    return

        self.is_running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")

        outdir = self.entry_outdir.get().strip() or "./images"
        threads_cnt = int(self.spin_threads.get() or 10)
        ratio = self.cmb_ratio.get()

        self.processor = BatchProcessor(
            cookies_str=cookies,
            output_dir=outdir,
            threads=threads_cnt,
            aspect_ratio=ratio
        )

        items = []
        for idx, p in enumerate(self.prompts):
            items.append({
                "id": idx + 1,
                "prompt": p,
                "subject_path": self.ref_widgets["Subject"][0].get(),
                "subject_prompt": self.ref_widgets["Subject"][1].get(),
                "scene_path": self.ref_widgets["Scene"][0].get(),
                "scene_prompt": self.ref_widgets["Scene"][1].get(),
                "style_path": self.ref_widgets["Style"][0].get(),
                "style_prompt": self.ref_widgets["Style"][1].get(),
            })

        t = threading.Thread(target=self.run_backend_worker, args=(items,))
        t.daemon = True
        t.start()

    def stop_batch(self):
        if self.processor:
            self.processor.stop()
            self.log("⚠️ Đã gửi lệnh DỪNG tiến trình Backend...", "warning")

    def retry_batch(self):
        for i in range(len(self.statuses)):
            if self.statuses[i] == "Lỗi":
                self.statuses[i] = "Đang chờ"
        self.load_table_data()
        self.start_batch()

    def show_errors(self):
        errs = [f"Prompt #{i+1}: {p}" for i, (p, s) in enumerate(zip(self.prompts, self.statuses)) if s == "Lỗi"]
        if errs:
            messagebox.showwarning("Chi tiết lỗi", "\n".join(errs))
        else:
            messagebox.showinfo("Thông báo", "Không có prompt nào bị lỗi!")

    def run_backend_worker(self, items):
        def gui_log(msg, mtype):
            self.after(0, lambda: self.log(msg, mtype))

        def gui_progress(completed, total, results):
            pct = int((completed / total) * 100)
            for r in results:
                rid = r["id"] - 1
                if 0 <= rid < len(self.statuses):
                    if r["status"] == "success":
                        self.statuses[rid] = "Thành công"
                    elif r["status"] == "error":
                        self.statuses[rid] = "Lỗi"

            self.after(0, lambda: self.update_progress_ui(pct, completed, total))
            self.after(0, self.load_table_data)

        self.processor.run_batch(items, progress_callback=gui_progress, log_callback=gui_log)

        self.is_running = False
        self.after(0, self.on_batch_finished)

    def update_progress_ui(self, pct, current, total):
        self.pbar["value"] = pct
        self.lbl_progress.config(text=f"Đang sinh ảnh & tải về {current}/{total} ({pct}%)")

    def on_batch_finished(self):
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.lbl_progress.config(text="Sẵn sàng")
        self.log("🟩 HOÀN THÀNH TIẾN TRÌNH AUTOMATION BACKEND")

if __name__ == "__main__":
    app = WhiskTkinterApp()
    app.mainloop()
