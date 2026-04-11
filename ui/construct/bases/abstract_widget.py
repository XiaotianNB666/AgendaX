from abc import ABC, abstractmethod

from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QLineEdit, QComboBox

from ui.construct.bases.core_widgets import QSSWidget, LayoutWidget
from ui.utils.qss_loader import load_qss, load_qss_s


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

    def set_color(self, color: str):
        self.setStyleSheet(
            'MLabel {'
            f'color: {color}'
            '}'
        )


class MComboBox(QComboBox, QSSWidget):
    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self.load()
        self.setStyleSheet(load_qss_s('combo_box', theme))


class MLineEdit(QLineEdit, QSSWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.load()
