from typing import Callable
from PyQt5.QtWidgets import (
    QWidget, QApplication, QLabel, QPushButton, QVBoxLayout
)
from PyQt5.QtCore import (
    Qt, QPoint, QPropertyAnimation, QEasingCurve,
    QTimer
)
from PyQt5.QtGui import QColor, QPixmap
from ui.utils.qss_loader import QSSLoader


class MenuBall(QWidget):
    """展开的菜单悬浮球"""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(36, 36)

        self._container = QWidget(self)
        self._container.setGeometry(0, 0, 36, 36)
        self._container.setStyleSheet("""
            background-color: #3d3d3d;
            border-radius: 18px;
            border: 2px solid #5d5d5d;
        """)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._exit_btn = QPushButton("✕", self._container)
        self._exit_btn.setFixedSize(20, 20)
        self._exit_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #ff5f56;
            }
        """)
        layout.addWidget(self._exit_btn, alignment=Qt.AlignCenter)

    def set_exit_callback(self, callback: Callable):
        self._exit_btn.clicked.connect(callback)

    def show_at_edge(self, edge_pos: QPoint, target_pos: QPoint):
        self.move(edge_pos)
        self.show()

        if hasattr(self, "_open_anim") and self._open_anim:
            self._open_anim.stop()

        self._open_anim = QPropertyAnimation(self, b"pos")
        self._open_anim.setDuration(300)
        self._open_anim.setEasingCurve(QEasingCurve.OutBack)
        self._open_anim.setStartValue(edge_pos)
        self._open_anim.setEndValue(target_pos)
        self._open_anim.start()

    def hide_to_edge(self, edge_pos: QPoint):
        if hasattr(self, "_close_anim") and self._close_anim:
            self._close_anim.stop()

        self._close_anim = QPropertyAnimation(self, b"pos")
        self._close_anim.setDuration(200)
        self._close_anim.setEasingCurve(QEasingCurve.InBack)
        self._close_anim.setStartValue(self.pos())
        self._close_anim.setEndValue(edge_pos)
        self._close_anim.finished.connect(self.close)
        self._close_anim.start()

    def move_directly(self, pos: QPoint):
        if hasattr(self, "_open_anim") and self._open_anim:
            self._open_anim.stop()
        if hasattr(self, "_close_anim") and self._close_anim:
            self._close_anim.stop()
        self.move(pos)


class AgendaXFloatingBall(QWidget):
    def __init__(self):
        super().__init__()
        self.qss_loader = QSSLoader(self)

        self._increasing = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_opacity)

        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._on_single_click)

        self._is_dragging = False
        self._menu_ball = MenuBall(self)

        self._init_ui()

    def _init_ui(self):
        self._drag_position = None
        self._click_action = None
        self._opacity_high = 0.75
        self._current_opacity = self._opacity_high

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(60, 60)

        self._icon_label = QLabel(self)
        self._icon_label.setFixedSize(60, 60)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setStyleSheet(
            self.qss_loader.load(opacity_high=self._opacity_high)
        )

        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self._icon_label.setGraphicsEffect(shadow)

    def setIcon(self, filepath: str):
        pix = QPixmap(filepath).scaled(
            40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self._icon_label.setPixmap(pix)

    def set_click_action(self, func: Callable):
        self._click_action = func

    def set_exit_action(self, func: Callable):
        if self._menu_ball:
            self._menu_ball.set_exit_callback(func)

    def show(self):
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 80, screen.height() - 80)
        self._timer.start(20)
        super().show()

    def close(self):
        if self._menu_ball:
            self._menu_ball.close()
        super().close()
        self._timer.stop()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self._menu_ball and self._menu_ball.isVisible():
                e.ignore()
                return

            self._drag_start_pos = e.globalPos()
            self._drag_position = e.globalPos() - self.frameGeometry().topLeft()
            self._is_dragging = False

        e.accept()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_position:
            distance = (e.globalPos() - self._drag_start_pos).manhattanLength()
            if distance > 5:
                self._is_dragging = True

            if self._is_dragging:
                self.move(e.globalPos() - self._drag_position)

                if self._menu_ball and self._menu_ball.isVisible():
                    self._move_menu_ball()

        e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self._is_dragging:
                e.accept()
                self._is_dragging = False
                return

            if self._click_timer.isActive():
                self._click_timer.stop()
                self._on_double_click()
            else:
                self._click_timer.start(300)

        e.accept()

    def _on_single_click(self):
        self._click_timer.stop()
        self._toggle_menu()

    def _on_double_click(self):
        if self._click_action:
            self._click_action()

    def _toggle_menu(self):
        if self._menu_ball and self._menu_ball.isVisible():
            self._hide_menu()
        else:
            self._show_menu()

    def _get_menu_side(self):
        main_rect = self.geometry()
        screen = QApplication.primaryScreen().geometry()

        left_space = main_rect.left()
        right_space = screen.width() - main_rect.right()

        return "left" if right_space < 100 or left_space >= right_space else "right"

    def _show_menu(self):
        main_pos = self.geometry().topLeft()
        main_rect = self.geometry()
        side = self._get_menu_side()

        if side == "left":
            edge_x = main_pos.x() - 36
            target_x = main_pos.x() - 42
        else:
            edge_x = main_pos.x() + main_rect.width()
            target_x = main_pos.x() + main_rect.width() + 6

        edge_pos = QPoint(edge_x, main_pos.y() + 12)
        target_pos = QPoint(target_x, main_pos.y() + 12)

        self._menu_ball.show_at_edge(edge_pos, target_pos)

    def _hide_menu(self):
        main_pos = self.geometry().topLeft()
        main_rect = self.geometry()
        side = self._get_menu_side()

        edge_pos = (
            QPoint(main_pos.x() - 36, main_pos.y() + 12)
            if side == "left"
            else QPoint(main_pos.x() + main_rect.width(), main_pos.y() + 12)
        )

        self._menu_ball.hide_to_edge(edge_pos)

    def _move_menu_ball(self):
        if not self._menu_ball or not self._menu_ball.isVisible():
            return

        main_pos = self.geometry().topLeft()
        main_rect = self.geometry()
        side = self._get_menu_side()

        target_x = (
            main_pos.x() - 42
            if side == "left"
            else main_pos.x() + main_rect.width() + 6
        )

        self._menu_ball.move_directly(QPoint(target_x, main_pos.y() + 12))

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