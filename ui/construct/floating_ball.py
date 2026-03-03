from typing import Callable
from PyQt5.QtWidgets import QWidget, QApplication, QLabel
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtCore import QTimer

from ui.utils.qss_loader import QSSLoader


class AgendaXFloatingBall(QWidget):
    def __init__(self):
        super().__init__()
        self.qss_loader = QSSLoader(self)
        self._increasing = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_opacity)
        self._init_ui()

    def _init_ui(self):
        self._drag_position = None
        self._click_action = None
        self._opacity_high = 0.75
        self._current_opacity = self._opacity_high
        self._icon_label = None
        # 无边框、置顶、透明
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(60, 60)

        # 主标签（球形）
        self._icon_label = QLabel(self)
        self._icon_label.setFixedSize(60, 60)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setStyleSheet(self.qss_loader.load(opacity_high=self._opacity_high))

        # 阴影
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self._icon_label.setGraphicsEffect(shadow)

        # 拖动
        self._drag_position = QPoint()

    def setIcon(self, filepath: str):
        pix = QPixmap(filepath).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._icon_label.setPixmap(pix)

    def set_click_action(self, func: Callable):
        self._click_action = func

    def show(self):
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 100, 150)
        self._timer.start(20)
        super().show()

    def close(self):
        super().close()
        self._timer.stop()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self._click_action:
                self._click_action()
        elif e.button() == Qt.RightButton:
            self._icon_label.setStyleSheet(
                self.qss_loader.load(opacity_high=self._current_opacity)  # 使用当前透明度
            )
        e.accept()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_position = e.globalPos() - self.frameGeometry().topLeft()
        e.accept()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and not self._drag_position.isNull():
            self.move(e.globalPos() - self._drag_position)
        e.accept()

    def _update_opacity(self):
        if self._increasing:
            self._current_opacity += 0.01
            if self._current_opacity >= 0.8:
                self._current_opacity = 0.75
                self._increasing = False
        else:
            self._current_opacity -= 0.01
            if self._current_opacity <= 0.15:
                self._current_opacity = 0.25
                self._increasing = True
        self.setWindowOpacity(self._current_opacity)
