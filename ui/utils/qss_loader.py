from email.policy import default
from functools import cache
from os import path

from PyQt5.QtCore import QFile, QIODevice
from PyQt5.QtWidgets import QWidget

from core.utils.path_utils import get_res_path
from core.utils.string_utils import snake
from ui.main import LOG

loaded: dict[type, str] = {}

default_qss = """
* {
    background-color: #ddddd;
}
"""


class QSSLoader:
    qw: type
    qw_type: str

    def __init__(self, qw: type):
        self.qw = qw
        self.qw_type = snake(str(type(qw)))

    def load(self) -> str:
        global loaded, default_qss
        if self.qw in loaded:
            return loaded[self.qw]
        qss_path = path.join(get_res_path('stylesheets'), self.qw_type + '.qss')
        qfile = QFile(qss_path)

        if not qfile.open(QIODevice.ReadOnly | QIODevice.Text):  # type: ignore
            qss = self.load_from_parents()
            if qss != '':
                return qss
            LOG.error(f'cannot load qss[{self.qw_type}] from: {qss_path}.')
            return default_qss
        return qfile.readAll().data().decode('utf-8')

    def load_from_parents(self) -> str:
        global loaded
        final_qss: str = ''
        for T in self.qw.__bases__:
            if issubclass(T, QWidget) and T is not QWidget and not T in loaded:
                qss = QSSLoader(T).load()
                loaded[T] = qss
                final_qss += qss

        return final_qss
