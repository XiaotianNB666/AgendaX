from PyQt5.QtWidgets import QWidget

class QSSLoader:
    qw: QWidget
    qw_type: str

    def __init__(self, qw: QWidget):
        self.qw = qw
        self.qw_type = str(type(qw))

    def load(self):
