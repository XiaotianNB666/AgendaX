from abc import ABC, abstractmethod
from typing import override

from PyQt5.QtWidgets import QWidget

from ui.construct.bases.core_widgets import QSSWidget, LayoutWidget
from ui.utils.qss_loader import load_qss


class AbstractWidgetMeta(type(ABC), type(QWidget)):
    ...


class ModernWidget(QSSWidget, LayoutWidget, ABC, metaclass=AbstractWidgetMeta):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(load_qss(self))

    def set_stylesheet(self, stylesheet: str):
        super().setStyleSheet(stylesheet)

    @override
    def setStyleSheet(self, styleSheet: str):
        original_stylesheet = '' if self.styleSheet() is None else self.styleSheet()
        self.set_stylesheet(f'{original_stylesheet}\n{styleSheet}')

    @abstractmethod
    def set(self, child: QWidget):
        pass
