from abc import ABC, abstractmethod
from PyQt5.QtWidgets import QListWidget

class Card(ABC, QListWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet()

    @abstractmethod
    def init_card(self):
        ...
