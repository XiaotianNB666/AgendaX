# boot/crash_ui.py
import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit,
    QPushButton, QHBoxLayout, QLabel, QFileDialog
)
from PyQt5.QtCore import Qt


class LauncherCrashUI(QWidget):
    def __init__(self, crash_file: Path):
        super().__init__()
        self.crash_file = crash_file
        self.setWindowTitle("AgendaX Crash Report")
        self.resize(900, 650)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("AgendaX 崩溃报告")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:16px; font-weight:bold;")
        layout.addWidget(title)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QTextEdit.NoWrap)
        self.text.setText(self.crash_file.read_text(encoding="utf-8"))

        layout.addWidget(self.text)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        copy_btn = QPushButton("复制到剪贴板")
        copy_btn.clicked.connect(self.copy_to_clipboard)

        save_btn = QPushButton("另存为...")
        save_btn.clicked.connect(self.save_as)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def copy_to_clipboard(self):
        QApplication.clipboard().setText(self.text.toPlainText())

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存崩溃报告",
            str(self.crash_file.resolve()),
            "Crash Files (*.crash);;All Files (*.*)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text.toPlainText())


def show_crash_ui(crash_file: Path):
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    ui = LauncherCrashUI(crash_file)
    ui.show()

    app.exec_()
