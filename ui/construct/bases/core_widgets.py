from ui.utils.qss_loader import load_qss
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLayout)


class QSSWidget(QWidget):
    def load(self):
        self.setStyleSheet(load_qss(self.__class__))


class LayoutWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """初始化UI布局"""
        # 主垂直布局
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # 顶部区域
        self._top_widget = QWidget()
        self._top_layout = QHBoxLayout(self._top_widget)
        self._top_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.addWidget(self._top_widget)

        # 中间水平布局（左-中-右）
        self._middle_layout = QHBoxLayout()
        self._middle_layout.setContentsMargins(0, 0, 0, 0)
        self._middle_layout.setSpacing(0)

        # 左侧区域
        self._left_widget = QWidget()
        self._left_layout = QVBoxLayout(self._left_widget)
        self._left_layout.setContentsMargins(0, 0, 0, 0)
        self._middle_layout.addWidget(self._left_widget)

        # 中心区域
        self._center_widget = QWidget()
        self._center_layout = QVBoxLayout(self._center_widget)
        self._center_layout.setContentsMargins(0, 0, 0, 0)
        self._middle_layout.addWidget(self._center_widget)

        # 右侧区域
        self._right_widget = QWidget()
        self._right_layout = QVBoxLayout(self._right_widget)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._middle_layout.addWidget(self._right_widget)

        self._main_layout.addLayout(self._middle_layout)

        # 底部区域
        self._bottom_widget = QWidget()
        self._bottom_layout = QHBoxLayout(self._bottom_widget)
        self._bottom_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.addWidget(self._bottom_widget)

        # 设置拉伸因子：顶部和底部固定高度，中间自适应
        self._main_layout.setStretch(0, 0)  # top
        self._main_layout.setStretch(1, 1)  # middle (center + left + right)
        self._main_layout.setStretch(2, 0)  # bottom

        # 中间区域的拉伸因子
        self._middle_layout.setStretch(0, 0)  # left
        self._middle_layout.setStretch(1, 1)  # center
        self._middle_layout.setStretch(2, 0)  # right

    def _clear_layout(self, layout: QLayout):
        """清空布局中的所有控件"""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def _set_widget(self, container: QWidget, layout: QLayout, child: QWidget):
        """将子控件添加到指定容器"""
        self._clear_layout(layout)
        if child:
            layout.addWidget(child)

    def set_center(self, child: QWidget):
        """设置中心区域控件"""
        self._set_widget(self._center_widget, self._center_layout, child)

    def set_left(self, child: QWidget):
        """设置左侧区域控件"""
        self._set_widget(self._left_widget, self._left_layout, child)

    def set_right(self, child: QWidget):
        """设置右侧区域控件"""
        self._set_widget(self._right_widget, self._right_layout, child)

    def set_top(self, child: QWidget):
        """设置顶部区域控件"""
        self._set_widget(self._top_widget, self._top_layout, child)

    def set_bottom(self, child: QWidget):
        """设置底部区域控件"""
        self._set_widget(self._bottom_widget, self._bottom_layout, child)

    def get_center(self) -> QWidget:
        return self._center_widget

    def get_left(self) -> QWidget:
        return self._left_widget

    def get_right(self) -> QWidget:
        return self._right_widget

    def get_top(self) -> QWidget:
        return self._top_widget

    def get_bottom(self) -> QWidget:
        return self._bottom_widget
