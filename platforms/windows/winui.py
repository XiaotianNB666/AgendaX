from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
import sys
import ctypes


def enable_win_blur_background(window: QWidget, blur_type: int = 1) -> QWidget | None:
    """
    仅在 Windows 上生效：
    - 设置窗口无边框全屏
    - 启用 DWM 毛玻璃模糊背景
    - 设置半透明深色背景
    """
    if sys.platform != "win32":
        return None # 非 Windows 不执行

    # 1. 无边框 + 全屏
    window.setWindowFlags(Qt.FramelessWindowHint)  # type: ignore
    window.showFullScreen()

    # 2. 启用窗口透明（为模糊做准备）
    window.setAttribute(Qt.WA_TranslucentBackground, True)  # type: ignore

    # 3. 创建并设置中心部件背景
    central_widget = QWidget(window)
    window.setCentralWidget(central_widget)
    palette = central_widget.palette()
    palette.setColor(QPalette.Window, QColor(30, 30, 30, 180))  # 深灰半透明
    central_widget.setAutoFillBackground(True)
    central_widget.setPalette(palette)

    # 4. Windows DWM 毛玻璃模糊
    hwnd = int(window.winId())
    ctypes.windll.dwmapi.DwmSetWindowAttribute(
        hwnd,
        38,
        ctypes.byref(ctypes.c_int(blur_type)),
        ctypes.sizeof(ctypes.c_int),
    )

    return central_widget
