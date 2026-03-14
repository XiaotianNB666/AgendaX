from PyQt5.QtWidgets import QWidget

from ui.construct.bases.abstract_widget import ModernWidget


class CenterModernWidget(ModernWidget):
    def set(self, child: QWidget):
        self.set_center(child)