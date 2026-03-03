from abc import ABC, abstractmethod
from PyQt5.QtWidgets import QListWidget

from ui.utils.qss_loader import QSSLoader


class Card(ABC, QListWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(QSSLoader(self).load())
        self.init_card()

    @abstractmethod
    def init_card(self):
        ...
