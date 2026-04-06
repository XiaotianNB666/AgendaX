from typing import Callable

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QPaintEvent, QMouseEvent, QImage

from ui.construct.bases.abstract_widget import MPushButton, ModernWidgetLight
from ui.construct.widgets.InlineDialogWidget import InlineDialogWidget
from core.i18n import t


from typing import Callable

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QPaintEvent, QMouseEvent, QImage

from ui.construct.bases.abstract_widget import MPushButton, ModernWidgetLight
from ui.construct.widgets.InlineDialogWidget import InlineDialogWidget
from core.i18n import t


class WhiteboardWidget(QWidget):
    def __init__(self, parent: InlineDialogWidget, pen_color='#000000'):
        super().__init__(parent)
        self._parent = parent

        self._current_path = []
        self._paths = []
        self.__pen_color = pen_color
        self._pen_color = QColor(self.__pen_color)
        self._pen_width = 3
        self._drawing = False
        self._last_point = QPoint()
        self._temp_image = None

        # ✅ 背景图
        self._background_image = QImage()

        self.confirm_handler: Callable[[InlineDialogWidget], None] = lambda d: None

        self._init_ui()

    def _init_ui(self):
        self.setObjectName("whiteboardWidget")

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ===== 工具栏 =====
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 8, 10, 8)
        toolbar.setSpacing(10)

        self._pen_btn = MPushButton(t('ui.whiteboard_widget.pen'))
        self._pen_btn.setCheckable(True)
        self._pen_btn.setChecked(True)
        self._pen_btn.clicked.connect(self._on_pen_clicked)
        toolbar.addWidget(self._pen_btn)

        self._eraser_btn = MPushButton(t('ui.whiteboard_widget.eraser'))
        self._eraser_btn.setCheckable(True)
        self._eraser_btn.clicked.connect(self._on_eraser_clicked)
        toolbar.addWidget(self._eraser_btn)

        self._undo_btn = MPushButton(t('ui.whiteboard_widget.undo'))
        self._undo_btn.clicked.connect(self._undo_last_step)
        toolbar.addWidget(self._undo_btn)

        toolbar.addStretch()

        self._confirm_btn = MPushButton(t('ui.whiteboard_widget.confirm'))
        self._confirm_btn.clicked.connect(self._on_confirm)
        toolbar.addWidget(self._confirm_btn)

        self._cancel_btn = MPushButton(t('ui.whiteboard_widget.cancel'))
        self._cancel_btn.clicked.connect(self._on_cancel)
        toolbar.addWidget(self._cancel_btn)

        main_layout.addLayout(toolbar)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # ===== 绘图区 =====
        self._drawing_area = ModernWidgetLight()
        self._drawing_area.setFixedSize(1600, 140)

        self._drawing_area.paintEvent = self._drawing_area_paint_event
        self._drawing_area.mousePressEvent = self._drawing_area_mouse_press_event
        self._drawing_area.mouseMoveEvent = self._drawing_area_mouse_move_event
        self._drawing_area.mouseReleaseEvent = self._drawing_area_mouse_release_event

        main_layout.addWidget(self._drawing_area)

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )

    # ================= 绘图 =================

    def _drawing_area_paint_event(self, event: QPaintEvent):
        painter = QPainter(self._drawing_area)
        painter.setRenderHint(QPainter.Antialiasing)

        # ✅ 背景
        if not self._background_image.isNull():
            painter.drawImage(self._drawing_area.rect(), self._background_image)
        else:
            painter.fillRect(event.rect(), Qt.white)

        # ✅ 历史路径
        for path_data in self._paths:
            pen = QPen(path_data['color'], path_data['width'])
            painter.setPen(pen)
            points = path_data['points']
            for i in range(1, len(points)):
                painter.drawLine(points[i - 1], points[i])

        # ✅ 当前路径
        if self._drawing and len(self._current_path) > 1:
            pen = QPen(self._pen_color, self._pen_width)
            painter.setPen(pen)
            for i in range(1, len(self._current_path)):
                painter.drawLine(self._current_path[i - 1], self._current_path[i])

    def _drawing_area_mouse_press_event(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drawing = True
            self._current_path = [event.pos()]
            self._last_point = event.pos()
            self._drawing_area.update()

    def _drawing_area_mouse_move_event(self, event: QMouseEvent):
        if self._drawing and (event.buttons() & Qt.LeftButton):
            self._current_path.append(event.pos())
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
            self._current_path.clear()
            self._drawing_area.update()

    # ================= 工具 =================

    def _on_pen_clicked(self):
        self._pen_btn.setChecked(True)
        self._eraser_btn.setChecked(False)
        self._pen_color = QColor(self.__pen_color)
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
        self.clear()

    def _on_cancel(self):
        if self._temp_image:
            self._paths.append(self._temp_image)
            self._temp_image = None
        self._drawing_area.update()
        self._parent.hide_dialog()
        self.clear()

    def register_confirm_handler(self, handler):
        self.confirm_handler = handler

    def clear(self):
        self._paths.clear()
        self._current_path.clear()
        self._drawing_area.update()

    # ================= 对外接口 =================

    def set_image(self, data: QImage):
        """
        从 bytes 加载图片作为背景
        """
        image = data

        if image.isNull():
            return

        self._background_image = image.scaled(
            self._drawing_area.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        self._drawing_area.update()

    def image(self) -> QImage:
        return self._drawing_area.grab().toImage()

    def save_to_image(self, file_path: str):
        self.image().save(file_path, "PNG")

class WhiteboardDialog(InlineDialogWidget):

    def __init__(self, parent=None, title='Whiteboard'):
        super().__init__(parent, title, draggable=True, show_title_bar=True)

        # self.setMinimumSize(400, 300)
        # self.resize(500, 350)

        self._whiteboard = WhiteboardWidget(self)

        self._whiteboard.setFixedSize(1600, 140)
        self.setMinimumSize(1600, 180)

        self.set_content(self._whiteboard)

