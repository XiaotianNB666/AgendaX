from abc import ABC, abstractmethod, ABCMeta
from PyQt5.QtWidgets import QListWidget, QWidget, QFrame

from ui.construct.bases.abstract_widget import ModernWidget


class Card(QFrame, ModernWidget):
    def set(self, child: QWidget):
        pass

    def __init__(self):
        super().__init__()
        self.init_card()

    def init_card(self):
        ...
