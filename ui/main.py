from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QApplication, QHBoxLayout, QPushButton
from PyQt5.QtGui import QFont, QMouseEvent

import sys

from core.app import APP
from core.crash_report import CrashReport
from core.i18n import t
from core.utils.logger.logging import getLogger
from platforms.windows.winui import enable_win_blur_background

LOG = getLogger(f'{APP.name}-ui')

UICRASH = CrashReport()

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.initUI()
    def initUI(self) -> None:
        enable_win_blur_background(self)
        container = self.centralWidget()

        if container is None:
            LOG.error('cannot get central container.')
            UICRASH.reason = t('ui.main_window.error.init')
            LOG.critical(UICRASH.string)
    
    def mouseDoubleClickEvent(self, a0: QMouseEvent | None) -> None:
        super().mouseDoubleClickEvent(a0)
        self.hide()


QAPP = QApplication(sys.argv)
MAIN_WINDOW = MainWindow()

def main() -> int:
    MAIN_WINDOW.show()
    LOG.info(t('ui.main_window.show'))
    return QAPP.exec_()
