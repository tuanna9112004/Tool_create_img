import sys
import os
import time
import json
import csv
import random
from datetime import datetime

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QLineEdit, QTextEdit, QPushButton,
    QComboBox, QSpinBox, QProgressBar, QTableWidget, QTableWidgetItem,
    QTabWidget, QFileDialog, QMessageBox, QHeaderView, QFrame, QSplitter
)

# ==============================================================================
# STYLESHEET (Dark Slate & Neon Blue/Green Styling)
# ==============================================================================
DARK_STYLE = """
QMainWindow {
    background-color: #0b0f19;
}
QWidget {
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 13px;
}
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #1e293b;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 14px;
    background-color: #111827;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #38bdf8;
}
QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: #090d16;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f8fafc;
    selection-background-color: #0284c7;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #38bdf8;
    background-color: #0f172a;
}
QPushButton {
    background-color: #1e293b;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    color: #f1f5f9;
}
QPushButton:hover {
    background-color: #334155;
    border-color: #64748b;
}
QPushButton:pressed {
    background-color: #0f172a;
}
QPushButton#btnPrimary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10b981, stop:1 #059669);
    border: none;
    color: #ffffff;
    font-size: 14px;
}
QPushButton#btnPrimary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #34d399, stop:1 #10b981);
}
QPushButton#btnStop {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ef4444, stop:1 #dc2626);
    border: none;
    color: #ffffff;
    font-size: 14px;
}
QPushButton#btnStop:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f87171, stop:1 #ef4444);
}
QPushButton#btnRetry {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0284c7, stop:1 #0369a1);
    border: none;
    color: #ffffff;
}
QPushButton#btnRetry:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #38bdf8, stop:1 #0284c7);
}
QPushButton#btnDangerIcon {
    background-color: rgba(244, 63, 94, 0.15);
    border: 1px solid rgba(244, 63, 94, 0.4);
    color: #f43f5e;
}
QPushButton#btnDangerIcon:hover {
    background-color: rgba(244, 63, 94, 0.35);
}
QTableWidget {
    background-color: #090d16;
    gridline-color: #1e293b;
    border: 1px solid #1e293b;
    border-radius: 6px;
}
QTableWidget::item {
    padding: 6px;
}
QTableWidget::item:selected {
    background-color: rgba(56, 189, 248, 0.2);
    color: #ffffff;
}
QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    font-weight: bold;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #1e293b;
}
QTabWidget::pane {
    border: 1px solid #1e293b;
    border-radius: 6px;
    background-color: #111827;
}
QTabBar::tab {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background-color: #38bdf8;
    color: #090d16;
    font-weight: bold;
}
QProgressBar {
    border: 1px solid #1e293b;
    border-radius: 6px;
    text-align: center;
    background-color: #090d16;
    color: #ffffff;
    font-weight: bold;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #10b981);
    border-radius: 5px;
}
"""

# ==============================================================================
# WORKER THREAD FOR BATCH IMAGE GENERATION
# ==============================================================================
class BatchWorker(QThread):
    progress_updated = pyqtSignal(int, int, str)  # current, total, log_message
    row_status_changed = pyqtSignal(int, str, str)  # row_idx, status, image_path
    finished_signal = pyqtSignal(bool)

    def __init__(self, prompts, cookies, output_dir, threads, aspect_ratio):
        super().__init__()
        self.prompts = prompts
        self.cookies = cookies
        self.output_dir = output_dir
        self.threads = threads
        self.aspect_ratio = aspect_ratio
        self.is_running = True

    def run(self):
        total = len(self.prompts)
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.progress_updated.emit(0, total, f"Đã khởi chạy tiến trình với {self.threads} luồng...")

        for idx, prompt in enumerate(self.prompts):
            if not self.is_running:
                self.progress_updated.emit(idx, total, "[Cảnh báo] Tiến trình bị dừng bởi người dùng!")
                break

            self.row_status_changed.emit(idx, "running", "")
            self.progress_updated.emit(idx, total, f"[Luồng {(idx % self.threads) + 1}] Đang xử lý Prompt #{idx + 1}: '{prompt[:35]}...'")

            # Simulate batch image generation processing time
            time.sleep(1.5)

            if not self.is_running:
                break

            # 90% success, 10% simulated error
            is_success = random.random() > 0.1
            if is_success:
                img_name = f"img_{idx + 1}_{int(time.time())}.png"
                saved_path = os.path.join(self.output_dir, img_name)
                # Create a placeholder dummy file
                with open(saved_path, "w") as f:
                    f.write(f"Generated Image for prompt: {prompt}")
                
                self.row_status_changed.emit(idx, "success", saved_path)
                self.progress_updated.emit(idx + 1, total, f"[Thành công] Prompt #{idx + 1} -> Đã lưu: {saved_path}")
            else:
                self.row_status_changed.emit(idx, "error", "")
                self.progress_updated.emit(idx + 1, total, f"[Lỗi] Prompt #{idx + 1}: Server Timeout / Response Error")

        self.finished_signal.emit(True)

    def stop(self):
        self.is_running = False

# ==============================================================================
# MAIN WINDOW CLASS
# ==============================================================================
class WhiskApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Whisk Image Generator Pro by creatornow.com.vn - Desktop Edition")
        self.resize(1380, 880)

        self.prompts = [
            "A breathtaking panoramic illustration of earthy futuristic landscape with glowing waterfalls",
            "A dramatic editorial illustration of three cybernetic warriors in neon armor",
            "A majestic and slightly menacing oil painting of a mythical dragon over ancient ruins",
            "A sweeping illustrated map of the Austro-Hungarian empire in steampunk style",
            "Realistic photography of a sleek high-tech AI camera lens with soft studio lighting"
        ]
        self.statuses = ["Đang chờ"] * len(self.prompts)
        self.worker = None

        self.init_ui()
        self.load_default_table()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Main Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # ----------------------------------------------------------------------
        # LEFT PANEL: References & Settings
        # ----------------------------------------------------------------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Group 1: Reference Images
        ref_group = QGroupBox("🖼️ Ảnh Tham Chiếu (Reference Images)")
        ref_layout = QVBoxLayout(ref_group)
        ref_layout.setSpacing(10)

        # Subject, Scene, Style Rows
        self.ref_inputs = {}
        for key, title, hint in [
            ("Subject", "Subject (Đối tượng chính):", "VD: 'young woman, brown eyes, long black hair'"),
            ("Scene", "Scene (Cảnh / Bối cảnh):", "VD: 'modern office, glass windows, natural lighting'"),
            ("Style", "Style (Phong cách):", "VD: 'realistic photography, soft lighting, portrait'")
        ]:
            item_box = QVBoxLayout()
            lbl = QLabel(title)
            lbl.setStyleSheet("font-weight: 600; color: #f1f5f9;")
            item_box.addWidget(lbl)

            input_row = QHBoxLayout()
            path_edit = QLineEdit()
            path_edit.setPlaceholderText("Chọn ảnh tham chiếu...")
            path_edit.setReadOnly(True)
            btn_choose = QPushButton("📁 Chọn")
            btn_check = QPushButton("🔍 Kiểm tra")
            btn_clear = QPushButton("✖")
            btn_clear.setObjectName("btnDangerIcon")

            btn_choose.clicked.connect(lambda _, k=key: self.browse_ref_file(k))
            btn_check.clicked.connect(lambda _, k=key: self.check_ref_file(k))
            btn_clear.clicked.connect(lambda _, k=key: self.clear_ref_file(k))

            input_row.addWidget(path_edit, 3)
            input_row.addWidget(btn_choose, 1)
            input_row.addWidget(btn_check, 1)
            input_row.addWidget(btn_clear)
            item_box.addLayout(input_row)

            prompt_edit = QLineEdit()
            prompt_edit.setPlaceholderText(hint)
            item_box.addWidget(prompt_edit)

            ref_layout.addLayout(item_box)
            self.ref_inputs[key] = (path_edit, prompt_edit)

        left_layout.addWidget(ref_group)

        # Group 2: Settings
        settings_group = QGroupBox("⚙️ Cài đặt (Settings)")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(10)

        # Cookies
        lbl_cookie = QLabel("🔑 Cookies:")
        self.txt_cookies = QTextEdit()
        self.txt_cookies.setPlaceholderText("Dán cookies phiên đăng nhập vào đây (_ga=..., Host-next-auth.csrf-token=...)")
        self.txt_cookies.setMaximumHeight(65)
        btn_save_cookies = QPushButton("💾 Lưu Cookies")
        btn_save_cookies.clicked.connect(self.save_cookies)

        settings_layout.addWidget(lbl_cookie)
        settings_layout.addWidget(self.txt_cookies)
        settings_layout.addWidget(btn_save_cookies, alignment=Qt.AlignmentFlag.AlignRight)

        # Grid Settings: Threads, Aspect Ratio, Directory, Start Index
        grid_sett = QGridLayout()
        grid_sett.addWidget(QLabel("Số luồng (Threads):"), 0, 0)
        self.spn_threads = QSpinBox()
        self.spn_threads.setRange(1, 50)
        self.spn_threads.setValue(10)
        grid_sett.addWidget(self.spn_threads, 0, 1)

        grid_sett.addWidget(QLabel("Tỷ lệ khung hình:"), 0, 2)
        self.cmb_ratio = QComboBox()
        self.cmb_ratio.addItems(["Landscape (16:9)", "Portrait (9:16)", "Square (1:1)", "Standard (4:3)"])
        grid_sett.addWidget(self.cmb_ratio, 0, 3)

        grid_sett.addWidget(QLabel("Thư mục xuất ảnh:"), 1, 0)
        self.txt_output_dir = QLineEdit("./images")
        btn_browse_dir = QPushButton("...")
        btn_browse_dir.clicked.connect(self.browse_output_dir)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.txt_output_dir)
        dir_layout.addWidget(btn_browse_dir)
        grid_sett.addLayout(dir_layout, 1, 1, 1, 3)

        grid_sett.addWidget(QLabel("Số bắt đầu:"), 2, 0)
        self.spn_start = QSpinBox()
        self.spn_start.setValue(1)
        grid_sett.addWidget(self.spn_start, 2, 1)

        settings_layout.addLayout(grid_sett)
        left_layout.addWidget(settings_group)

        # Action Buttons
        ctrl_layout = QGridLayout()
        self.btn_start = QPushButton("▶ Bắt đầu")
        self.btn_start.setObjectName("btnPrimary")
        self.btn_start.setMinimumHeight(42)
        self.btn_start.clicked.connect(self.start_batch)

        self.btn_stop = QPushButton("⏹ Dừng")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setMinimumHeight(42)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_batch)

        self.btn_retry = QPushButton("🔄 Retry prompt hiện tại")
        self.btn_retry.setObjectName("btnRetry")
        self.btn_retry.setMinimumHeight(38)
        self.btn_retry.clicked.connect(self.retry_batch)

        btn_err_details = QPushButton("⚠️ Chi tiết lỗi")
        btn_err_details.setMinimumHeight(38)
        btn_err_details.clicked.connect(self.show_errors)

        ctrl_layout.addWidget(self.btn_start, 0, 0)
        ctrl_layout.addWidget(self.btn_stop, 0, 1)
        ctrl_layout.addWidget(self.btn_retry, 1, 0)
        ctrl_layout.addWidget(btn_err_details, 1, 1)

        left_layout.addLayout(ctrl_layout)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # ----------------------------------------------------------------------
        # RIGHT PANEL: Prompts Management, Progress & Logs
        # ----------------------------------------------------------------------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Tabs Editor
        self.tabs = QTabWidget()
        
        # Tab 1: Table Editor
        tab_table = QWidget()
        layout_table_tab = QVBoxLayout(tab_table)

        # Toolbar
        toolbar = QHBoxLayout()
        btn_add = QPushButton("➕ Thêm dòng")
        btn_del = QPushButton("➖ Xóa dòng")
        btn_up = QPushButton("⬆ Lên")
        btn_down = QPushButton("⬇ Xuống")
        btn_add.clicked.connect(self.add_row)
        btn_del.clicked.connect(self.del_row)
        btn_up.clicked.connect(self.move_up)
        btn_down.clicked.connect(self.move_down)

        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_del)
        toolbar.addWidget(btn_up)
        toolbar.addWidget(btn_down)
        toolbar.addStretch()

        btn_import = QPushButton("📥 Import từ file")
        btn_export = QPushButton("📤 Export ra file")
        btn_sync = QPushButton("🔄 Sync Text ↔ Table")
        btn_clear_all = QPushButton("🗑 Xóa tất cả")
        btn_clear_all.setObjectName("btnDangerIcon")

        btn_import.clicked.connect(self.import_file)
        btn_export.clicked.connect(self.export_file)
        btn_sync.clicked.connect(self.sync_text_table)
        btn_clear_all.clicked.connect(self.clear_all)

        toolbar.addWidget(btn_import)
        toolbar.addWidget(btn_export)
        toolbar.addWidget(btn_sync)
        toolbar.addWidget(btn_clear_all)

        layout_table_tab.addLayout(toolbar)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["STT", "Prompt", "Tiến độ", "Rerun"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 80)
        layout_table_tab.addWidget(self.table)

        self.tabs.addTab(tab_table, "📋 Table Editor")

        # Tab 2: Text Editor
        tab_text = QWidget()
        layout_text_tab = QVBoxLayout(tab_text)
        self.txt_editor = QTextEdit()
        self.txt_editor.setPlaceholderText("Nhập danh sách prompt (mỗi prompt 1 dòng)...")
        btn_apply_text = QPushButton("🔄 Cập nhật vào Bảng Prompt")
        btn_apply_text.clicked.connect(self.sync_text_to_table_action)

        layout_text_tab.addWidget(btn_apply_text, alignment=Qt.AlignmentFlag.AlignLeft)
        layout_text_tab.addWidget(self.txt_editor)
        self.tabs.addTab(tab_text, "📝 Text Editor")

        right_layout.addWidget(self.tabs, 3)

        # Progress Section
        progress_group = QGroupBox("📊 Tiến độ sinh ảnh")
        prog_layout = QVBoxLayout(progress_group)

        self.lbl_progress = QLabel("Trạng thái: Sẵn sàng")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        metrics_layout = QHBoxLayout()
        self.lbl_total = QLabel("Tổng số: 0")
        self.lbl_success = QLabel("Thành công: 0")
        self.lbl_error = QLabel("Lỗi: 0")
        self.lbl_pending = QLabel("Đang chờ: 0")

        self.lbl_success.setStyleSheet("color: #10b981; font-weight: bold;")
        self.lbl_error.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.lbl_pending.setStyleSheet("color: #f59e0b; font-weight: bold;")

        metrics_layout.addWidget(self.lbl_total)
        metrics_layout.addWidget(self.lbl_success)
        metrics_layout.addWidget(self.lbl_error)
        metrics_layout.addWidget(self.lbl_pending)

        prog_layout.addWidget(self.lbl_progress)
        prog_layout.addWidget(self.progress_bar)
        prog_layout.addLayout(metrics_layout)

        right_layout.addWidget(progress_group)

        # Log Section
        log_group = QGroupBox("📜 Log Console")
        log_layout = QVBoxLayout(log_group)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("background-color: #06080d; font-family: 'Consolas', monospace; font-size: 11px;")
        
        btn_clear_log = QPushButton("🧹 Xóa Log")
        btn_clear_log.clicked.connect(lambda: self.txt_log.clear())

        log_layout.addWidget(self.txt_log)
        log_layout.addWidget(btn_clear_log, alignment=Qt.AlignmentFlag.AlignRight)

        right_layout.addWidget(log_group, 2)

        splitter.addWidget(right_widget)
        splitter.setSizes([460, 920])

    # --------------------------------------------------------------------------
    # TABLE & LOGIC HELPER METHODS
    # --------------------------------------------------------------------------
    def log(self, message, msg_type="info"):
        nowStr = datetime.now().strftime("[%H:%M:%S]")
        color = "#94a3b8"
        if msg_type == "success": color = "#10b981"
        elif msg_type == "error": color = "#ef4444"
        elif msg_type == "warning": color = "#f59e0b"

        self.txt_log.append(f'<span style="color:#64748b;">{nowStr}</span> <span style="color:{color};">{message}</span>')

    def load_default_table(self):
        self.table.setRowCount(len(self.prompts))
        for i, prompt in enumerate(self.prompts):
            # STT
            stt_item = QTableWidgetItem(str(i + 1))
            stt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, stt_item)

            # Prompt
            prompt_item = QTableWidgetItem(prompt)
            self.table.setItem(i, 1, prompt_item)

            # Status
            status_item = QTableWidgetItem(self.statuses[i])
            self.table.setItem(i, 2, status_item)

            # Rerun Button
            btn_rerun = QPushButton("🔄")
            btn_rerun.setFixedWidth(40)
            btn_rerun.clicked.connect(lambda _, row=i: self.rerun_row(row))
            self.table.setCellWidget(i, 3, btn_rerun)

        self.update_metrics()
        self.log(f"Đã nạp {len(self.prompts)} prompts vào phần mềm Desktop", "info")

    def update_metrics(self):
        total = len(self.prompts)
        success = self.statuses.count("Thành công")
        error = self.statuses.count("Lỗi")
        pending = self.statuses.count("Đang chờ")

        self.lbl_total.setText(f"Tổng số: {total}")
        self.lbl_success.setText(f"Thành công: {success}")
        self.lbl_error.setText(f"Lỗi: {error}")
        self.lbl_pending.setText(f"Đang chờ: {pending}")

    def browse_ref_file(self, key):
        filename, _ = QFileDialog.getOpenFileName(self, f"Chọn ảnh tham chiếu [{key}]", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if filename:
            self.ref_inputs[key][0].setText(filename)
            self.log(f"Đã chọn ảnh tham chiếu [{key}]: {filename}", "info")

    def check_ref_file(self, key):
        path = self.ref_inputs[key][0].text()
        prompt = self.ref_inputs[key][1].text()
        if not path and not prompt:
            QMessageBox.warning(self, "Cảnh báo", f"Tham chiếu [{key}] chưa có ảnh hoặc prompt mô tả!")
        else:
            QMessageBox.information(self, "Thông báo", f"Tham chiếu [{key}] HỢP LỆ!\nFile: {path}\nPrompt: {prompt}")

    def clear_ref_file(self, key):
        self.ref_inputs[key][0].clear()
        self.ref_inputs[key][1].clear()
        self.log(f"Đã xóa tham chiếu [{key}]", "info")

    def save_cookies(self):
        cookies = self.txt_cookies.toPlainText().strip()
        self.log("Đã lưu cookies vào ứng dụng Desktop", "success")
        QMessageBox.information(self, "Thành công", "Đã lưu Cookies!")

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Chọn thư mục xuất ảnh", "./images")
        if directory:
            self.txt_output_dir.setText(directory)

    def add_row(self):
        row = self.table.rowCount()
        self.prompts.append("Prompt sinh ảnh mới...")
        self.statuses.append("Đang chờ")
        self.load_default_table()

    def del_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0 and current_row < len(self.prompts):
            del self.prompts[current_row]
            del self.statuses[current_row]
            self.load_default_table()

    def move_up(self):
        row = self.table.currentRow()
        if row > 0:
            self.prompts[row], self.prompts[row - 1] = self.prompts[row - 1], self.prompts[row]
            self.statuses[row], self.statuses[row - 1] = self.statuses[row - 1], self.statuses[row]
            self.load_default_table()
            self.table.selectRow(row - 1)

    def move_down(self):
        row = self.table.currentRow()
        if row >= 0 and row < len(self.prompts) - 1:
            self.prompts[row], self.prompts[row + 1] = self.prompts[row + 1], self.prompts[row]
            self.statuses[row], self.statuses[row + 1] = self.statuses[row + 1], self.statuses[row]
            self.load_default_table()
            self.table.selectRow(row + 1)

    def clear_all(self):
        if QMessageBox.question(self, "Xác nhận", "Xóa toàn bộ danh sách prompt?") == QMessageBox.StandardButton.Yes:
            self.prompts.clear()
            self.statuses.clear()
            self.load_default_table()

    def sync_text_table(self):
        self.txt_editor.setPlainText("\n".join(self.prompts))

    def sync_text_to_table_action(self):
        lines = [line.strip() for line in self.txt_editor.toPlainText().split("\n") if line.strip()]
        self.prompts = lines
        self.statuses = ["Đang chờ"] * len(lines)
        self.load_default_table()
        self.tabs.setCurrentIndex(0)

    def import_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Import Prompts", "", "Text/CSV Files (*.txt *.csv)")
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            self.prompts = lines
            self.statuses = ["Đang chờ"] * len(lines)
            self.load_default_table()
            self.log(f"Import thành công {len(lines)} prompts từ {filename}", "success")

    def export_file(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export Prompts", "whisk_prompts.txt", "Text Files (*.txt)")
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(self.prompts))
            self.log(f"Đã export danh sách prompt ra {filename}", "success")

    def rerun_row(self, row):
        self.statuses[row] = "Đang chờ"
        self.load_default_table()

    # --------------------------------------------------------------------------
    # BATCH PROCESS EXECUTION
    # --------------------------------------------------------------------------
    def start_batch(self):
        if not self.prompts:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng thêm prompt trước khi bắt đầu!")
            return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self.worker = BatchWorker(
            prompts=self.prompts,
            cookies=self.txt_cookies.toPlainText(),
            output_dir=self.txt_output_dir.text(),
            threads=self.spn_threads.value(),
            aspect_ratio=self.cmb_ratio.currentText()
        )
        self.worker.progress_updated.connect(self.on_worker_progress)
        self.worker.row_status_changed.connect(self.on_row_status_changed)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.start()

    def stop_batch(self):
        if self.worker:
            self.worker.stop()
            self.btn_stop.setEnabled(False)

    def retry_batch(self):
        for i in range(len(self.statuses)):
            if self.statuses[i] == "Lỗi":
                self.statuses[i] = "Đang chờ"
        self.load_default_table()
        self.start_batch()

    def show_errors(self):
        errors = [f"Prompt #{i+1}: {self.prompts[i]}" for i in range(len(self.statuses)) if self.statuses[i] == "Lỗi"]
        if not errors:
            QMessageBox.information(self, "Thông báo", "Không có prompt nào bị lỗi!")
        else:
            QMessageBox.warning(self, "Danh sách lỗi", "\n".join(errors))

    def on_worker_progress(self, current, total, log_msg):
        pct = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.lbl_progress.setText(f"Trạng thái: Đang chạy {current}/{total}...")
        self.log(log_msg, "info" if "Thành công" not in log_msg else "success")

    def on_row_status_changed(self, row_idx, status_code, saved_path):
        if status_code == "running":
            self.statuses[row_idx] = "Đang chạy..."
        elif status_code == "success":
            self.statuses[row_idx] = "Thành công"
        elif status_code == "error":
            self.statuses[row_idx] = "Lỗi"
        self.load_default_table()

    def on_worker_finished(self, success):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_progress.setText("Trạng thái: Đã hoàn tất toàn bộ tiến trình!")
        self.log("=== TIẾN TRÌNH THỦ CÔNG HOÀN THÀNH ===", "success")

# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = WhiskApp()
    window.setStyleSheet(DARK_STYLE)
    window.show()
    sys.exit(app.exec())
