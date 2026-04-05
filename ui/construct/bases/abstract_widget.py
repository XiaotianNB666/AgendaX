from abc import ABC, abstractmethod
from typing import override

from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QLineEdit

from ui.construct.bases.core_widgets import QSSWidget, LayoutWidget
from ui.utils.qss_loader import load_qss


class AbstractWidgetMeta(type(ABC), type(QWidget)):
    ...


class ModernWidgetLight(QSSWidget, metaclass=AbstractWidgetMeta):
    def __init__(self, parent=None, auto_load=True):
        super().__init__(parent)
        if auto_load:
            self.setStyleSheet(load_qss(self))

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
    clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.load()

    def mouseReleaseEvent(self, ev):
        self.clicked.emit()


class MComboBox(QLabel, QSSWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.load()

class MLineEdit(QLineEdit, QSSWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.load()
