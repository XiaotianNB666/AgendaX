import sys
import os
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QMainWindow, QApplication, QVBoxLayout, QWidget, QHBoxLayout
from core.app import APP, register_force_stop
from core.crash_report import CrashReport
from core.i18n import t
from core.utils.logger.logging import getLogger
from core.utils.path_utils import get_res_path
from platforms.windows.winui import enable_win_blur_background
from ui.construct.floating_ball import AgendaXFloatingBall
from ui.construct.subject_card import SubjectCard

LOG = getLogger(f'{APP.name}-ui')

UICRASH = CrashReport()


class MainWindow(QMainWindow):
    subject_layout_widget: QWidget
    subject_layout: QVBoxLayout
    floating_ball: AgendaXFloatingBall

    def __init__(self) -> None:
        super().__init__()
        self.floating_ball = AgendaXFloatingBall()
        self.floating_ball.set_click_action(self._handle_ball_clicked)
        self.floating_ball.setIcon(os.path.join(get_res_path('icon'), 'icon.png'))
        self.floating_ball.set_exit_action(self.stop)
        self.init_ui()

    def init_ui(self) -> None:
        container = enable_win_blur_background(self)

        container.setMinimumSize(self.size())

        if container is None:
            LOG.error('cannot get central container.')
            UICRASH.reason = t('ui.main_window.error.init')
            LOG.critical(UICRASH.string)

        self.subject_layout_widget = QWidget()
        self.subject_layout = QVBoxLayout(self.subject_layout_widget)
        # 水平布局
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(self.subject_layout_widget)
        h_layout.addStretch()

        v_layout = QVBoxLayout()
        v_layout.addSpacing(10)
        v_layout.addSpacing(10)
        v_layout.addSpacing(10)
        v_layout.addStretch()
        v_layout.addLayout(h_layout)
        v_layout.addStretch()

        container.setLayout(v_layout)
        for _ in range(8):
            self.subject_layout.addWidget((sc := SubjectCard()))
            sc.init_size(container)

    def mouseDoubleClickEvent(self, a0: QMouseEvent | None) -> None:
        super().mouseDoubleClickEvent(a0)
        self.hide()
        self.floating_ball.show()

    def force_stop(self):
        self.close()
        QApplication.quit()

    def stop(self):
        self.close()
        QApplication.quit()

    def _handle_ball_clicked(self):
        self.show()
        self.floating_ball.close()


QAPP = QApplication(sys.argv)
MAIN_WINDOW = MainWindow()


def main() -> int:
    register_force_stop(MAIN_WINDOW.force_stop)
    MAIN_WINDOW.show()
    LOG.info(t('ui.main_window.show'))
    return QAPP.exec_()
