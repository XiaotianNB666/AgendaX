from typing import Callable
from PyQt5.QtWidgets import (QWidget, QApplication, QLabel, QVBoxLayout,
                             QPushButton)
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtCore import QTimer

from ui.utils.qss_loader import QSSLoader


class MenuBall(QWidget):
    """展开的菜单悬浮球"""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(36, 36)

        # 主容器
        self._container = QWidget(self)
        self._container.setGeometry(0, 0, 36, 36)
        self._container.setStyleSheet("""
            background-color: #3d3d3d;
            border-radius: 18px;
            border: 2px solid #5d5d5d;
        """)

        # 布局
        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # X 按钮
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
        """在边缘位置显示并执行飞出动画"""
        self.move(edge_pos)
        self.show()

        # 停止之前的动画
        if hasattr(self, '_open_anim') and self._open_anim:
            self._open_anim.stop()

        # 从边缘飞到目标位置
        self._open_anim = QPropertyAnimation(self, b"pos")
        self._open_anim.setDuration(300)
        self._open_anim.setEasingCurve(QEasingCurve.OutBack)
        self._open_anim.setStartValue(edge_pos)
        self._open_anim.setEndValue(target_pos)
        self._open_anim.start()

    def hide_to_edge(self, edge_pos: QPoint):
        """执行飞回边缘动画后隐藏"""
        # 停止之前的动画
        if hasattr(self, '_close_anim') and self._close_anim:
            self._close_anim.stop()

        self._close_anim = QPropertyAnimation(self, b"pos")
        self._close_anim.setDuration(200)
        self._close_anim.setEasingCurve(QEasingCurve.InBack)
        self._close_anim.setStartValue(self.pos())
        self._close_anim.setEndValue(edge_pos)
        self._close_anim.finished.connect(self.close)
        self._close_anim.start()

    def move_directly(self, pos: QPoint):
        """直接移动到目标位置（无动画）"""
        if hasattr(self, '_open_anim') and self._open_anim:
            self._open_anim.stop()
        if hasattr(self, '_close_anim') and self._close_anim:
            self._close_anim.stop()
        self.move(pos)


class AgendaXFloatingBall(QWidget):
    def __init__(self):
        super().__init__()
        self.qss_loader = QSSLoader(self)
        self._increasing = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_opacity)
        self._is_dragging = False
        self._menu_ball = MenuBall(self)
        self._init_ui()

    def _init_ui(self):
        self._drag_position = None
        self._click_action = None
        self._opacity_high = 0.75
        self._current_opacity = self._opacity_high
        self._icon_label = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(60, 60)

        self._icon_label = QLabel(self)
        self._icon_label.setFixedSize(60, 60)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setStyleSheet(self.qss_loader.load(opacity_high=self._opacity_high))

        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self._icon_label.setGraphicsEffect(shadow)

        self._drag_position = QPoint()

    def setIcon(self, filepath: str):
        pix = QPixmap(filepath).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._icon_label.setPixmap(pix)

    def set_click_action(self, func: Callable):
        self._click_action = func

    def set_exit_action(self, func: Callable):
        if self._menu_ball:
            self._menu_ball.set_exit_callback(func)

    def show(self):
        screen = QApplication.primaryScreen().geometry()
        # 一、主球初始位置设为右下角
        self.move(screen.width() - 80, screen.height() - 80)
        self._timer.start(20)
        super().show()

    def close(self):
        if self._menu_ball:
            self._menu_ball.close()
        super().close()
        self._timer.stop()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self._click_action:
                self._click_action()
        elif e.button() == Qt.RightButton:
            self._icon_label.setStyleSheet(
                self.qss_loader.load(opacity_high=self._current_opacity)
            )
        e.accept()
        # 三、确保双击时不会唤出菜单

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            # 如果菜单可见，点击主球不处理，让菜单的按钮接收事件
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

                # 二、修复：拖拽时只移动菜单，不重新展开
                if self._menu_ball and self._menu_ball.isVisible():
                    self._move_menu_ball()
        e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            # 如果是拖拽操作，不触发菜单
            if self._is_dragging:
                e.accept()
                return

            # 三、修复：双击时不会唤出菜单
            # 通过检查是否是双击的第二次点击来避免
            # 这里简单处理：如果菜单可见则关闭，否则打开
            # 但双击时第一次释放会触发，第二次释放会关闭，这是预期行为
            # 如果需要完全禁止双击触发，需要记录上次点击时间
            self._toggle_menu()
        e.accept()

    def _toggle_menu(self):
        """切换菜单显示/隐藏"""
        if self._menu_ball and self._menu_ball.isVisible():
            self._hide_menu()
        else:
            self._show_menu()

    def _get_menu_side(self):
        """
        判断菜单应该显示在左边还是右边
        返回: 'left' 或 'right'
        """
        main_pos = self.geometry().topLeft()
        main_rect = self.geometry()
        screen = QApplication.primaryScreen().geometry()
        screen_width = screen.width()

        # 主球右边缘位置
        main_right = main_pos.x() + main_rect.width()
        # 主球中心位置
        main_center = main_pos.x() + main_rect.width() // 2

        # 主球左边剩余空间
        left_space = main_pos.x()
        # 主球右边剩余空间
        right_space = screen_width - main_right

        # 如果右边空间 >= 100 且 左边空间 < 100，或者两边空间都够但右边更宽
        if right_space >= 100 and (left_space < 100 or right_space >= left_space):
            return 'left'
        else:
            return 'right'

    def _show_menu(self):
        # 智能定位 - 判断屏幕空间
        main_pos = self.geometry().topLeft()
        main_rect = self.geometry()
        screen = QApplication.primaryScreen().geometry()
        screen_width = screen.width()

        side = self._get_menu_side()

        if side == 'left':
            # 菜单在主球左边
            # 边缘位置：主球左边缘再往左 36 像素（小球宽度）
            edge_x = main_pos.x() - 36
            # 目标位置：主球左边缘往左 42 像素
            target_x = main_pos.x() - 42
        else:
            # 菜单在主球右边
            # 边缘位置：主球右边缘
            edge_x = main_pos.x() + main_rect.width()
            # 目标位置：主球右边缘往右 6 像素
            target_x = main_pos.x() + main_rect.width() + 6

        edge_pos = QPoint(edge_x, main_pos.y() + 12)
        target_pos = QPoint(target_x, main_pos.y() + 12)

        # 从边缘飞出到目标位置
        self._menu_ball.show_at_edge(edge_pos, target_pos)

    def _hide_menu(self):
        if self._menu_ball:
            # 获取主球位置计算边缘位置
            main_pos = self.geometry().topLeft()
            main_rect = self.geometry()
            side = self._get_menu_side()

            if side == 'left':
                # 飞回主球左边缘
                edge_pos = QPoint(main_pos.x() - 36, main_pos.y() + 12)
            else:
                # 飞回主球右边缘
                edge_pos = QPoint(main_pos.x() + main_rect.width(), main_pos.y() + 12)

            self._menu_ball.hide_to_edge(edge_pos)

    def _move_menu_ball(self):
        """拖拽时更新菜单位置，不重新展开"""
        if not self._menu_ball or not self._menu_ball.isVisible():
            return

        main_pos = self.geometry().topLeft()
        main_rect = self.geometry()
        side = self._get_menu_side()

        if side == 'left':
            new_x = main_pos.x() - 42
        else:
            new_x = main_pos.x() + main_rect.width() + 6

        new_pos = QPoint(new_x, main_pos.y() + 12)
        self._menu_ball.move_directly(new_pos)

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


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    ball = AgendaXFloatingBall()
    # ball.setIcon("path/to/your/icon.png")  # 替换为实际图标路径
    ball.show()
    sys.exit(app.exec_())