from argparse import ArgumentTypeError
from functools import cache
from os import path
from typing import Optional

from PyQt5.QtCore import QFile, QIODevice
from PyQt5.QtWidgets import QWidget

from core.events import SettingsLoadedEvent, register_event_handler
from core.settings import Settings
from core.utils.path_utils import get_res_path
from core.utils.string_utils import snake

loaded: dict[type, str] = {}

default_qss = """
* {
    background-color: #f0f0f0;
}
"""

QSS_IGNORE = ('q_frame', 'qss_widget')
SETTINGS: Optional[Settings] = None


class QSSLoader:
    qw: type[QWidget]
    qw_type: str

    def __init__(self, qw: QWidget | type[QWidget]):
        if isinstance(qw, QWidget):
            self.qw = type(qw)
        elif issubclass(qw, QWidget):
            self.qw = qw
        else:
            raise ArgumentTypeError("qw need QWidget.")

        self.qw_type = snake(self.qw.__name__)

    def load(self, is_load_self_only: bool = False, **kargs):
        qss = self._load(is_load_self_only)

        for k, v in kargs.items():
            qss = qss.replace(f'/*${{{k}}}$*/', str(v))

        return qss

    def _load(self, is_load_self_only: bool = False, theme: Optional[str] = '') -> str:
        from ui.main import LOG

        global loaded, default_qss
        if self.qw in loaded:
            return loaded[self.qw]

        if theme:
            theme = f'theme/{theme}'

        qss_path = path.join(get_res_path('stylesheets'), theme, self.qw_type + '.qss')  # 找到qss文件
        qfile = QFile(qss_path)

        if not qfile.open(QIODevice.ReadOnly | QIODevice.Text):  # type: ignore
            if not is_load_self_only:
                qss = self.load_from_parents()
                if qss != '':
                    return qss
            LOG.error(f'cannot load qss[{self.qw_type}] from: {qss_path}')
            return default_qss

        self_qss: str = qfile.readAll().data().decode('utf-8')

        if is_load_self_only:
            return self_qss

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
def load_qss(qw: QWidget | type, is_load_self_only: bool = False, **kargs):
    qss = QSSLoader(qw).load(is_load_self_only, **kargs)
    return qss


@cache
def load_qss_s(name: str, theme: Optional[str] = None, **kargs):
    from ui.main import LOG

    if theme is None:
        if SETTINGS:
            theme = SETTINGS.get('theme')
        else:
            theme = ''

    if theme:
        theme = ['themes', theme]

    qss_path = path.join(get_res_path('stylesheets'), *theme, name + '.qss')
    qfile = QFile(qss_path)

    if not qfile.open(QIODevice.ReadOnly | QIODevice.Text):  # type: ignore
        LOG.error(f'cannot load qss[{name}] from: {qss_path}')
        return default_qss

    qss: str = qfile.readAll().data().decode('utf-8')

    for k, v in kargs.items():
        qss = qss.replace(f'/*${{{k}}}$*/', str(v))

    return qss


def _set_settings(settings: SettingsLoadedEvent):
    global SETTINGS
    SETTINGS = settings.get_value()


register_event_handler(SettingsLoadedEvent, _set_settings)
