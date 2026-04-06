from PyQt5.QtWidgets import (QFrame, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QApplication, QLabel, QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, QPoint, QTimer, QParallelAnimationGroup
from PyQt5.QtGui import QMouseEvent
from typing_extensions import override

from typing import Optional, List

from ui.construct.bases.abstract_widget import MPushButton, MLabel
from ui.utils.qss_loader import load_qss_s


class InlineDialogWidget(QFrame):
    """内嵌式对话框控件"""

    _instances: List['InlineDialogWidget'] = []

    def __init__(self, parent: Optional[QWidget] = None, title: str = "Dialog",
                 draggable: bool = True, show_title_bar: bool = True) -> None:
        super().__init__(parent)
        self._title: str = title
        self._draggable: bool = draggable
        self._show_title_bar: bool = show_title_bar
        self._is_shown: bool = False
        self._is_dragging: bool = False
        self._drag_start_pos: QPoint = QPoint()
        self._dialog_start_pos: QPoint = QPoint()
        self._animation_timer: Optional[QTimer] = None
        self._opacity_effect: Optional[QGraphicsOpacityEffect] = None
        self._animation_group: Optional[QParallelAnimationGroup] = None
        self._z_level: int = 0
        self._base_z_value: int = 1000

        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setFocusPolicy(Qt.StrongFocus)

        InlineDialogWidget._instances.append(self)
        self.setStyleSheet(load_qss_s("modern_widget_light"))

        self._init_ui()

    @classmethod
    def get_instances(cls) -> List['InlineDialogWidget']:
        return cls._instances

    @classmethod
    def close_all_dialogs(cls) -> None:
        for instance in cls._instances[:]:
            instance.hide_dialog()

    @classmethod
    def show_dialog_by_title(cls, title: str) -> bool:
        for instance in cls._instances:
            if instance.get_title() == title:
                instance.show_dialog()
                return True
        return False

    @classmethod
    def bring_to_front(cls, instance: 'InlineDialogWidget') -> bool:
        if instance in cls._instances:
            max_level: int = max((inst.get_z_level() for inst in cls._instances), default=0)
            instance.set_z_level(max_level + 1)
            instance.reorder_by_level()
            return True
        return False

    @classmethod
    def send_to_back(cls, instance: 'InlineDialogWidget') -> bool:
        if instance in cls._instances:
            min_level: int = min((inst.get_z_level() for inst in cls._instances), default=0)
            instance.set_z_level(min_level - 1)
            instance.reorder_by_level()
            return True
        return False

    @classmethod
    def arrange_by_level(cls) -> None:
        cls._instances.sort(key=lambda x: x._z_level)
        for instance in cls._instances:
            instance.raise_()

    def _init_ui(self) -> None:
        self.setObjectName("inlineDialog")
        self.setStyleSheet(self._get_base_style())

        self._main_layout: QVBoxLayout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self._title_bar: QWidget = QWidget()
        self._title_bar.setObjectName("titleBar")
        self._title_bar.setCursor(Qt.SizeAllCursor if self._draggable else Qt.ArrowCursor)
        self._title_layout: QHBoxLayout = QHBoxLayout(self._title_bar)
        self._title_layout.setContentsMargins(10, 8, 10, 8)

        self._title_label: QLabel = MLabel(self._title)
        self._title_label.setObjectName("titleLabel")
        self._title_layout.addWidget(self._title_label)

        self._close_btn: QPushButton = QPushButton("×")
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.clicked.connect(self.hide_dialog)
        self._title_layout.addStretch()
        self._title_layout.addWidget(self._close_btn)

        if self._show_title_bar:
            self._main_layout.addWidget(self._title_bar)
        else:
            self._title_bar.hide()
            self.setStyleSheet(self._get_base_style() + self._get_no_titlebar_style())

        self._content_widget: QWidget = QWidget()
        self._content_layout: QVBoxLayout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(15, 15, 15, 15)
        self._main_layout.addWidget(self._content_widget)

        self.raise_()
        self.setVisible(False)

    def _get_base_style(self) -> str:
        return load_qss_s("inline_dialog_base_style")

    def _get_no_titlebar_style(self) -> str:
        return load_qss_s("inline_dialog_no_title_bar")

    def set_draggable(self, draggable: bool) -> None:
        self._draggable = draggable
        if self._show_title_bar:
            self._title_bar.setCursor(Qt.SizeAllCursor if draggable else Qt.ArrowCursor)

    def is_draggable(self) -> bool:
        return self._draggable

    def set_title(self, title: str) -> None:
        self._title = title
        self._title_label.setText(title)

    def get_title(self) -> str:
        return self._title

    def set_content(self, widget: QWidget) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._content_layout.addWidget(widget)

        QTimer.singleShot(0, self.resize_to_content)

    def get_content_widget(self) -> QWidget:
        return self._content_widget

    def set_style_sheet(self, qss: str) -> None:
        self.setStyleSheet(self._get_base_style() + qss)

    def show_title_bar(self, show: bool = True) -> None:
        self._show_title_bar = show
        if show:
            self._title_bar.show()
            self.setStyleSheet(self._get_base_style())
        else:
            self._title_bar.hide()
            self.setStyleSheet(self._get_base_style() + self._get_no_titlebar_style())

    def is_title_bar_visible(self) -> bool:
        return self._show_title_bar

    def set_z_level(self, level: int) -> None:
        self._z_level = level
        self._update_z_order()

    def get_z_level(self) -> int:
        return self._z_level

    def raise_to_top(self) -> None:
        max_level: int = max((inst.get_z_level() for inst in InlineDialogWidget._instances), default=0)
        self.set_z_level(max_level + 1)

    def lower_to_bottom(self) -> None:
        min_level: int = min((inst.get_z_level() for inst in InlineDialogWidget._instances), default=0)
        self.set_z_level(min_level - 1)

    def _update_z_order(self) -> None:
        base_style: str = self._get_base_style()
        no_title_style: str = "" if self._show_title_bar else self._get_no_titlebar_style()
        self.setStyleSheet(base_style + no_title_style)
        self.reorder_by_level()

    def reorder_by_level(self) -> None:
        if not self.parent():
            return
        sorted_instances: List[InlineDialogWidget] = sorted(
            InlineDialogWidget._instances,
            key=lambda x: x._z_level,
            reverse=False
        )
        for instance in sorted_instances:
            instance.raise_()

    def show_dialog(self, with_animation: bool = True) -> None:
        if not self.parent():
            return

        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setFocusPolicy(Qt.StrongFocus)
        self.show()
        self._is_shown = True

        self.resize_to_content()

        parent_rect = self.parent().rect()
        dialog_width = self.width()
        dialog_height = self.height()

        x = (parent_rect.width() - dialog_width) // 2
        y = (parent_rect.height() - dialog_height) // 2
        self.move(x, y)

        if with_animation:
            self._animate_expand()
        else:
            self.setFixedHeight(self.height())

        self.raise_to_top()

    def _animate_expand(self) -> None:
        self._target_height: int = self.sizeHint().height()
        self._current_height: int = 0
        self._step: int = max(1, self._target_height // 10)
        if self._animation_timer:
            self._animation_timer.stop()
            self._animation_timer.deleteLater()
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._expand_step)
        self._animation_timer.start(10)

    def _expand_step(self) -> None:
        self._current_height += self._step
        if self._current_height >= self._target_height:
            self._current_height = self._target_height
            if self._animation_timer:
                self._animation_timer.stop()
                self._animation_timer.deleteLater()
                self._animation_timer = None
            self.setFixedHeight(self._target_height)
        else:
            self.setFixedHeight(self._current_height)

    def hide_dialog(self, with_animation: bool = True) -> None:
        self._is_shown = False
        if with_animation:
            self._animate_collapse()
        else:
            self.setVisible(False)

    def _animate_collapse(self) -> None:
        self._current_height: int = self.height()
        self._step: int = max(1, self._current_height // 10)
        if self._animation_timer:
            self._animation_timer.stop()
            self._animation_timer.deleteLater()
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._collapse_step)
        self._animation_timer.start(10)

    def _collapse_step(self) -> None:
        self._current_height -= self._step
        if self._current_height <= 0:
            self._current_height = 0
            if self._animation_timer:
                self._animation_timer.stop()
                self._animation_timer.deleteLater()
                self._animation_timer = None
            self.setVisible(False)
        else:
            self.setFixedHeight(self._current_height)

    def toggle_dialog(self) -> None:
        if self._is_shown:
            self.hide_dialog()
        else:
            self.show_dialog()

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._is_shown and event.button() == Qt.LeftButton:
            self.raise_to_top()
            can_drag: bool = False
            if self._show_title_bar:
                if self._title_bar.underMouse() and self._draggable:
                    can_drag = True
            else:
                if self._draggable:
                    if not self._close_btn.underMouse():
                        can_drag = True
            if can_drag:
                self._is_dragging = True
                self._drag_start_pos = event.globalPos()
                self._dialog_start_pos = self.pos()
                event.accept()
                return
        super().mousePressEvent(event)

    @override
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging:
            delta: QPoint = event.globalPos() - self._drag_start_pos
            new_pos: QPoint = self._dialog_start_pos + delta
            if self.parent():
                parent_rect = self.parent().rect()
                dialog_rect = self.rect()
                min_x: int = min(0, parent_rect.width() - dialog_rect.width())
                min_y: int = min(0, parent_rect.height() - dialog_rect.height())
                max_x: int = max(0, parent_rect.width() - dialog_rect.width())
                max_y: int = max(0, parent_rect.height() - dialog_rect.height())
                new_x: int = max(min_x, min(new_pos.x(), max_x))
                new_y: int = max(min_y, min(new_pos.y(), max_y))
                self.move(new_x, new_y)
            event.accept()
            return
        super().mouseMoveEvent(event)

    @override
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging:
            self._is_dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    @override
    def closeEvent(self, event) -> None:
        if self in InlineDialogWidget._instances:
            InlineDialogWidget._instances.remove(self)
        super().closeEvent(event)

    def resize_to_content(self, margins: tuple[int, int, int, int] = (0, 0, 0, 0)) -> None:
        if not self._content_widget or not self._content_widget.layout():
            return

        content_hint = self._content_widget.sizeHint()
        if not content_hint.isValid():
            return

        l, t, r, b = margins
        w = content_hint.width() + l + r
        h = content_hint.height() + t + b

        # 如果有标题栏，加上标题栏高度
        if self._show_title_bar:
            h += self._title_bar.sizeHint().height()

        self.resize(w, h)
