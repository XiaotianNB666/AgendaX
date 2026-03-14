from typing import override

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QWidget

from ui.construct.bases.card import Card


class SubjectCard(Card):

    def set(self, child: QWidget):
        pass

    @override
    def init_card(self):
        pass

    @override
    def init_size(self, obj: QSize = None):
        self.setMinimumWidth(int(obj.width() * 0.8))
