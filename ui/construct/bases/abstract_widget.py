from abc import ABC, abstractmethod
from typing import override

from PyQt5.QtWidgets import QWidget, QPushButton, QLabel

from ui.construct.bases.core_widgets import QSSWidget, LayoutWidget
from ui.utils.qss_loader import load_qss


class AbstractWidgetMeta(type(ABC), type(QWidget)):
    ...


class ModernWidgetLight(QSSWidget, metaclass=AbstractWidgetMeta):
    def __init__(self, parent=None, auto_load=True):
        super().__init__(parent)
        if auto_load:
            self.setStyleSheet(load_qss(self))

    def set_stylesheet(self, stylesheet: str):
        super().setStyleSheet(stylesheet)

    @override
    def setStyleSheet(self, styleSheet: str):
        original_stylesheet = '' if self.styleSheet() is None else self.styleSheet()
        self.set_stylesheet(f'{original_stylesheet}\n{styleSheet}')

    def get_size(self):
        return self.size().width(), self.size().height()

    def set(self, child: QWidget):
        pass


class ModernWidget(ModernWidgetLight, LayoutWidget, ABC):
    def __init__(self, parent=None, auto_load=True):
        super().__init__(parent, auto_load)

    @abstractmethod
    def set(self, child: QWidget):
        pass


class MPushButton(QPushButton, QSSWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.load()

class MLabel(QLabel, QSSWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.load()
