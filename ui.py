import sys
import os
import subprocess
import fitz

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton,
    QVBoxLayout, QLabel, QHBoxLayout,
    QProgressBar, QLineEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFontMetrics


# ========================
# 🚀 Worker Thread
# ========================
class Worker(QThread):
    progress = Signal(int)
    status = Signal(str)

    def __init__(self, input_file, output_file):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        from main import translate_pdf

        self.status.emit("Processing...")

        def update_progress(current, total):
            percent = int(current / total * 100)
            self.progress.emit(percent)
            self.status.emit(f"Page {current}/{total}")

        def check_cancel():
            return not self._is_running

        success = translate_pdf(
            self.input_file,
            self.output_file,
            progress_callback=update_progress,
            cancel_callback=check_cancel
        )

        if success:
            self.status.emit("Done!")
        else:
            self.status.emit("Cancelled")


# ========================
# 🚀 Main App
# ========================
class App(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PDF Translator")
        self.resize(560, 280)
        self.center()
        self.setAcceptDrops(True)

        self.input_file = None
        self.output_file = None

        # ========================
        # UI
        # ========================
        self.drop_label = QLabel("Drop PDF here or drag file")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setObjectName("dropZone")

        # File input
        self.file_input = QLineEdit()
        self.file_input.setReadOnly(True)
        self.file_input.setPlaceholderText("No file selected")
        self.file_input.setMinimumHeight(30)

        # Remove link
        self.remove_label = QLabel("Remove")
        self.remove_label.setObjectName("link")
        self.remove_label.setCursor(Qt.PointingHandCursor)
        self.remove_label.mousePressEvent = lambda e: self.reset_app()
        self.remove_label.setFixedWidth(60)

        # 👉 Input + Remove ngang hàng
        file_layout = QHBoxLayout()
        file_layout.setSpacing(8)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(self.remove_label)

        self.file_container = QWidget()
        self.file_container.setLayout(file_layout)
        self.file_container.hide()

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        # Buttons (full width)
        self.btn_run = QPushButton("Run")
        self.btn_run.setObjectName("primary")
        self.btn_run.setMinimumHeight(36)
        self.btn_run.setEnabled(False)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("danger")
        self.btn_cancel.setMinimumHeight(36)
        self.btn_cancel.hide()

        self.btn_open = QPushButton("Open Output")
        self.btn_open.setObjectName("success")
        self.btn_open.setMinimumHeight(36)
        self.btn_open.hide()

        self.btn_new = QPushButton("Make New")
        self.btn_new.setObjectName("secondary")
        self.btn_new.setMinimumHeight(36)
        self.btn_new.hide()

        # ========================
        # STYLE
        # ========================
        self.setStyleSheet("""
            QWidget {
                font-size: 13px;
            }

            #dropZone {
                border: 1.5px dashed #bbb;
                padding: 20px;
                border-radius: 8px;
                color: #666;
            }

            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 6px;
            }

            QLabel#link {
                color: #dc3545;
                font-size: 12px;
            }

            QLabel#link:hover {
                text-decoration: underline;
            }

            QPushButton {
                padding: 10px;
                border-radius: 6px;
                width: 100%;
            }

            QPushButton#primary:enabled {
                background-color: #007bff;
                color: white;
                font-weight: bold;
            }

            QPushButton#primary:hover {
                background-color: #0069d9;
            }

            QPushButton#success:enabled {
                background-color: #28a745;
                color: white;
                font-weight: bold;
            }

            QPushButton#success:hover {
                background-color: #218838;
            }

            QPushButton#secondary:enabled {
                background-color: #e9ecef;
                color: #333;
            }

            QPushButton#secondary:hover {
                background-color: #d6d8db;
            }

            QPushButton#danger:enabled {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
            }

            QPushButton#danger:hover {
                background-color: #c82333;
            }

            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
        """)

        # ========================
        # Layout
        # ========================
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(self.drop_label)
        layout.addWidget(self.file_container)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.btn_run)
        layout.addWidget(self.btn_cancel)
        layout.addWidget(self.btn_open)
        layout.addWidget(self.btn_new)

        self.setLayout(layout)

        # Events
        self.btn_run.clicked.connect(self.run_process)
        self.btn_cancel.clicked.connect(self.cancel_process)
        self.btn_open.clicked.connect(self.open_output_file)
        self.btn_new.clicked.connect(self.reset_app)

    # ========================
    def center(self):
        screen = self.screen().availableGeometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

    # ========================
    def elide_text(self, text):
        metrics = QFontMetrics(self.file_input.font())
        width = self.file_input.width() - 10
        return metrics.elidedText(text, Qt.ElideMiddle, width)

    # ========================
    # Drag & Drop
    # ========================
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        file_path = event.mimeData().urls()[0].toLocalFile()

        if file_path.lower().endswith(".pdf"):
            self.set_file(file_path)
        else:
            self.drop_label.setText("Only PDF allowed")

    # ========================
    def set_file(self, file_path):
        self.input_file = file_path

        self.file_input.setText(self.elide_text(file_path))
        self.file_input.setToolTip(file_path)

        self.drop_label.hide()
        self.file_container.show()

        self.btn_run.setEnabled(True)

    def reset_app(self):
        self.input_file = None

        self.file_input.clear()
        self.file_container.hide()

        self.drop_label.show()
        self.drop_label.setText("Drop PDF here or drag file")

        self.progress_bar.hide()

        self.btn_run.setEnabled(False)
        self.btn_run.show()

        self.btn_cancel.hide()
        self.btn_open.hide()
        self.btn_new.hide()

    # ========================
    def run_process(self):
        base, ext = os.path.splitext(self.input_file)
        self.output_file = f"{base}_translated.pdf"

        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self.file_container.hide()
        self.drop_label.hide()

        self.btn_run.hide()
        self.btn_cancel.show()

        self.worker = Worker(self.input_file, self.output_file)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.update_status)
        self.worker.start()

    def cancel_process(self):
        if hasattr(self, "worker"):
            self.worker.stop()

    def update_status(self, text):
        if text == "Done!":
            self.progress_bar.setValue(100)

            self.btn_cancel.hide()
            self.btn_open.show()
            self.btn_new.show()

        elif text == "Cancelled":
            self.reset_app()

        else:
            self.setWindowTitle(text)

    # ========================
    def open_output_file(self):
        if self.output_file:
            if sys.platform == "darwin":
                subprocess.run(["open", self.output_file])
            elif sys.platform == "win32":
                os.startfile(self.output_file)


# ========================
app = QApplication(sys.argv)
window = App()
window.show()
sys.exit(app.exec())