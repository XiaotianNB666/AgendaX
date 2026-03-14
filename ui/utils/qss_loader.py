from argparse import ArgumentTypeError
from functools import cache
from os import path

from PyQt5.QtCore import QFile, QIODevice
from PyQt5.QtWidgets import QWidget

from core.utils.path_utils import get_res_path
from core.utils.string_utils import snake

loaded: dict[type, str] = {}

default_qss = """
* {
    background-color: #dddddd;
}
"""

QSS_IGNORE = ('q_frame', 'qss_widget')


class QSSLoader:
    qw: type
    qw_type: str

    def __init__(self, qw: QWidget | type):
        if isinstance(qw, QWidget):
            self.qw = type(qw)
        elif issubclass(qw, QWidget):
            self.qw = qw
        else:
            raise ArgumentTypeError("qw need QWidget.")

        self.qw_type = snake(self.qw.__name__)

    def load(self, **kargs):
        """**kargs: 是qss中值替换操作"""
        qss = self._load()

        for k, v in kargs.items():
            qss = qss.replace(f'/*${{{k}}}$*/', str(v))

        return qss

    def _load(self) -> str:
        from ui.main import LOG

        global loaded, default_qss
        if self.qw in loaded:
            return loaded[self.qw]

        qss_path = path.join(get_res_path('stylesheets'), self.qw_type + '.qss')
        qfile = QFile(qss_path)

        if not qfile.open(QIODevice.ReadOnly | QIODevice.Text):  # type: ignore
            qss = self.load_from_parents()
            if qss != '':
                return qss
            LOG.error(f'cannot load qss[{self.qw_type}] from: {qss_path}')
            return default_qss

        self_qss: str = qfile.readAll().data().decode('utf-8')
        return self.load_from_parents() + '\n' + self_qss

    def load_from_parents(self) -> str:
        global loaded
        final_qss: list[str] = []

        for T in self.qw.__bases__:
            if snake(T.__name__) in QSS_IGNORE:
                final_qss.append(f'/* stop load: {snake(T.__name__)} because of ignore */')
                break

            if issubclass(T, QWidget) and T is not QWidget and not T in loaded:
                qss = QSSLoader(T)._load()
                loaded[self.qw] = qss
                loaded[T] = qss
                final_qss.append(qss)

        final_qss.reverse()
        return '\n'.join(final_qss)


@cache
def load_qss(qw: QWidget | type, **kargs):
    qssl = QSSLoader(qw).load(**kargs)
    return qssl
