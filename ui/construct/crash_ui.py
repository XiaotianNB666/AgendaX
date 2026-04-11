import sys
from typing import override

from PyQt5.QtWidgets import QApplication, QTextEdit, QHBoxLayout, QPushButton, QVBoxLayout, QGroupBox, QWidget, QLabel
from PyQt5.QtCore import QTimer

from core.app import app_quit
from core.crash_report import CrashReport
from core.i18n import t


class CrashUI(QWidget):
    def __init__(self, report: CrashReport):
        super().__init__()
        self.report = report
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(t("crash.ui.title"))
        self.resize(900, 700)
        layout = QVBoxLayout(self)
        title = QLabel(self.report.report_title)
        title.setStyleSheet("font-size:16px; font-weight:bold;")
        layout.addWidget(title)
        self.trace_edit = QTextEdit()
        self.trace_edit.setReadOnly(True)
        self.trace_edit.setLineWrapMode(QTextEdit.NoWrap)
        self.trace_edit.setText(self.report.trace_string)
        layout.addWidget(self.trace_edit)
        var_group = QGroupBox(t("crash.ui.var_monitor"))
        var_group.setCheckable(True)
        var_group.setChecked(False)
        var_layout = QVBoxLayout(var_group)
        self.var_edit = QTextEdit()
        var_group.toggled.connect(lambda b: self.var_edit.setVisible(b))
        self.var_edit.setReadOnly(True)
        self.var_edit.setVisible(False)
        self.var_edit.setLineWrapMode(QTextEdit.NoWrap)
        self.var_edit.setText(self.report.var_monitor_string)
        var_layout.addWidget(self.var_edit)
        layout.addWidget(var_group)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        copy_btn = QPushButton(t("crash.ui.copy"))
        copy_btn.clicked.connect(self.copy_to_clipboard)
        close_btn = QPushButton(t("crash.ui.close"))
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def copy_to_clipboard(self):
        app = QApplication.instance()
        if app:
            clipboard = app.clipboard()
            clipboard.setText(self.report.string)

    @override
    def close(self):
        super().close()
        app_quit()

    @override
    def closeEvent(self, a0):
        super().closeEvent(a0)
        app_quit()


def show_window(ui: CrashUI):
    app = QApplication.instance()
    created = False
    if app is None:
        app = QApplication(sys.argv)
        created = True
    ui.show()
    if created:
        app.exec_()
    else:
        QTimer.singleShot(0, lambda: None)
