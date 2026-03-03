from abc import ABC
from PyQt5.QtWidgets import QWidget


class AbstractWidgetMeta(type(ABC), type(QWidget)):
    ...
