from abc import ABC, abstractmethod
from PyQt5.QtWidgets import QListWidget

from ui.construct.bases.abstract_widget import AbstractWidgetMeta
from ui.utils.qss_loader import QSSLoader


class Card(ABC, QListWidget, metaclass=AbstractWidgetMeta):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(QSSLoader(self).load())
        self.init_card()

    @abstractmethod
    def init_card(self):
        ...

    @abstractmethod
    def init_size(self, obj: object = None):
        ...

    def set_width(self, width):
        self.setGeometry(self.x(), self.y(), width, self.height())

    def set_height(self, height):
        self.setGeometry(self.x(), self.y(), self.width(), height)