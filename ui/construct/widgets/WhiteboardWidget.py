from typing import Callable

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QFrame)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QPaintEvent, QMouseEvent

from ui.construct.bases.abstract_widget import MPushButton, ModernWidgetLight
from ui.construct.widgets.InlineDialogWidget import InlineDialogWidget
from ui.utils.qss_loader import load_qss_s
from core.i18n import t


class WhiteboardWidget(QWidget):
    """白板控件，支持手写输入和绘图"""

    def __init__(self, parent: InlineDialogWidget):
        super().__init__(parent)
        self._parent = parent
        self._init_ui()
        self._current_path = []
        self._paths = []
        self._pen_color = QColor(0, 0, 0)
        self._pen_width = 3
        self._drawing = False
        self._last_point = QPoint()
        self._temp_image = None
        self._original_content = None
        self.confirm_handler: Callable[[WhiteboardDialog], None] = lambda d: None

    def _init_ui(self):
        """初始化UI"""
        self.setObjectName("whiteboardWidget")

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 8, 10, 8)
        toolbar.setSpacing(10)

        # 笔按钮
        self._pen_btn = MPushButton(t('ui.whiteboard_widget.pen'))
        self._pen_btn.setCheckable(True)
        self._pen_btn.setChecked(True)
        self._pen_btn.clicked.connect(self._on_pen_clicked)
        toolbar.addWidget(self._pen_btn)

        # 橡皮擦按钮
        self._eraser_btn = MPushButton(t('ui.whiteboard_widget.eraser'))
        self._eraser_btn.setCheckable(True)
        self._eraser_btn.clicked.connect(self._on_eraser_clicked)
        toolbar.addWidget(self._eraser_btn)

        # 撤销按钮
        self._undo_btn = MPushButton(t('ui.whiteboard_widget.undo'))
        self._undo_btn.clicked.connect(self._undo_last_step)
        toolbar.addWidget(self._undo_btn)

        toolbar.addStretch()

        # 确定按钮
        self._confirm_btn = MPushButton(t('ui.whiteboard_widget.confirm'))
        self._confirm_btn.clicked.connect(self._on_confirm)
        self._confirm_btn.clicked.connect(self._on_confirm)
        toolbar.addWidget(self._confirm_btn)

        # 取消按钮
        self._cancel_btn = MPushButton(t('ui.whiteboard_widget.cancel'))
        self._cancel_btn.clicked.connect(self._on_cancel)
        toolbar.addWidget(self._cancel_btn)

        main_layout.addLayout(toolbar)

        # 分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # 绘图区
        self._drawing_area = ModernWidgetLight()
        self._drawing_area.setMinimumSize(300, 200)
        self._drawing_area.paintEvent = self._drawing_area_paint_event
        self._drawing_area.mousePressEvent = self._drawing_area_mouse_press_event
        self._drawing_area.mouseMoveEvent = self._drawing_area_mouse_move_event
        self._drawing_area.mouseReleaseEvent = self._drawing_area_mouse_release_event

        main_layout.addWidget(self._drawing_area)

    def _drawing_area_paint_event(self, event: QPaintEvent):
        """绘图区绘制事件"""
        painter = QPainter(self._drawing_area)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制背景
        painter.fillRect(event.rect(), Qt.white)

        # 绘制所有路径
        for path_data in self._paths:
            pen = QPen(path_data['color'], path_data['width'])
            painter.setPen(pen)
            points = path_data['points']
            if len(points) > 1:
                for i in range(1, len(points)):
                    painter.drawLine(points[i - 1], points[i])

        # 绘制当前路径
        if self._drawing and len(self._current_path) > 1:
            pen = QPen(self._pen_color, self._pen_width)
            painter.setPen(pen)
            for i in range(1, len(self._current_path)):
                painter.drawLine(self._current_path[i - 1], self._current_path[i])

    def _drawing_area_mouse_press_event(self, event: QMouseEvent):
        """绘图区鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self._drawing = True
            self._current_path = [event.pos()]
            self._last_point = event.pos()
            self._drawing_area.update()

    def _drawing_area_mouse_move_event(self, event: QMouseEvent):
        """绘图区鼠标移动事件"""
        if self._drawing and (event.buttons() & Qt.LeftButton):
            self._current_path.append(event.pos())

            # 限制路径长度，避免性能问题
            if len(self._current_path) > 1000:
                self._paths.append({
                    'color': self._pen_color,
                    'width': self._pen_width,
                    'points': self._current_path[:-500]
                })
                self._current_path = self._current_path[-500:]

            self._drawing_area.update()

    def _drawing_area_mouse_release_event(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self._drawing:
            self._drawing = False
            if len(self._current_path) > 1:
                self._paths.append({
                    'color': self._pen_color,
                    'width': self._pen_width,
                    'points': self._current_path.copy()
                })
            self._current_path = []
            self._drawing_area.update()

    def _on_pen_clicked(self):
        self._pen_btn.setChecked(True)
        self._eraser_btn.setChecked(False)
        self._pen_color = QColor(0, 0, 0)
        self._pen_width = 3

    def _on_eraser_clicked(self):
        self._eraser_btn.setChecked(True)
        self._pen_btn.setChecked(False)
        self._pen_color = QColor(255, 255, 255)
        self._pen_width = 15

    def _undo_last_step(self):
        if self._paths:
            self._temp_image = self._paths.pop()
            self._drawing_area.update()

    def _on_confirm(self):
        if self.confirm_handler:
            self.confirm_handler(self._parent)
        self._parent.hide_dialog()

    def _on_cancel(self):
        if self._temp_image:
            self._paths.append(self._temp_image)
            self._temp_image = None
        self._drawing_area.update()
        self._parent.hide_dialog()

    def clear(self):
        self._paths.clear()
        self._current_path.clear()
        self._drawing_area.update()

    def save_to_image(self, file_path: str):
        pixmap = self._drawing_area.grab()
        pixmap.save(file_path, "PNG")


class WhiteboardDialog(InlineDialogWidget):

    def __init__(self, parent=None, title='Whiteboard'):
        super().__init__(parent, title, draggable=True, show_title_bar=True)

        self.setMinimumSize(400, 300)
        self.resize(500, 350)

        self._whiteboard = WhiteboardWidget(self)

        self.set_content(self._whiteboard)

