import os
import sys
from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import QTimer, QThread, Qt, QByteArray
from PyQt5.QtGui import QMouseEvent, QImage, QFont, QCursor, QPixmap
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QVBoxLayout, QWidget, QHBoxLayout, QSizePolicy, QLabel
)

from core.app import APP, register_stop, get_server, set_server, get_property
from core.crash_report import CrashReport
from core.events import register_event_handler, ExitEvent
from core.i18n import t
from core.server.server import AgendaXServer, ServerStartedEvent, Assignment, get_res_data
from core.settings import Settings
from core.utils.logger.logging import getLogger
from core.utils.path_utils import get_res_path
from platforms.windows.winui import enable_win_blur_background
from ui.construct.bases.abstract_widget import MLabel
from ui.construct.floating_ball import AgendaXFloatingBall
from ui.construct.subject_card import SubjectCard
from ui.construct.widgets.AssignmentCard import AssignmentCard, ImageLabel
from ui.utils.RemoteServer import RemoteServer
from ui.utils.qss_loader import load_qss_s

import faulthandler
faulthandler.enable()

LOG = getLogger(f'{APP.name}-ui')
UICRASH = CrashReport()


@dataclass
class Subject:
    id: str
    name: str
    display_name: str
    color: str
    assignments_card: Optional[SubjectCard] = None


class MainWindow(QMainWindow):
    subject_layout_widget: QWidget
    subject_layout: QVBoxLayout
    floating_ball: AgendaXFloatingBall
    settings: Settings = None
    server: AgendaXServer | RemoteServer = None
    subjects: list[Subject]

    def __init__(self) -> None:
        register_event_handler(ServerStartedEvent, self._set_server)
        super().__init__()

        self.floating_ball = AgendaXFloatingBall()
        self.floating_ball.set_click_action(self._handle_ball_clicked)
        self.floating_ball.setIcon(os.path.join(get_res_path('icon'), 'icon.png'))
        self.floating_ball.set_exit_action(self.stop)

        self.init_ui()

        if (server := get_server()) is not None:
            LOG.info(f'Connected to Server {server} successfully')
            self.server = server

        try:
            self.load_subjects()
        except Exception:
            LOG.exception("Failed to load subjects on init")

    def _set_server(self, event: ServerStartedEvent) -> None:
        self.server = event.get_value()
        LOG.info(f'Connected to Server {event.get_value()} successfully')
        try:
            self.load_subjects()
        except Exception:
            LOG.exception("Failed to load subjects after server set")

    def init_ui(self) -> None:
        container = enable_win_blur_background(self)
        container.setMinimumSize(self.size())

        if container is None:
            LOG.error('cannot get central container.')
            UICRASH.reason = t('ui.main_window.error.init')
            LOG.critical(UICRASH.string)
            return

        self.subject_layout_widget = QWidget()
        self.subject_layout = QVBoxLayout(self.subject_layout_widget)
        self.subject_layout.setContentsMargins(0, 0, 0, 0)
        self.subject_layout.setSpacing(6)
        self.subject_layout.setAlignment(Qt.AlignTop)

        self.subject_layout.setStretch(0, 0)
        self.subject_layout.addStretch(1)

        self.subject_layout_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        h_layout = QHBoxLayout()
        h_layout.addSpacing(50)
        h_layout.addWidget(self.subject_layout_widget)
        h_layout.addSpacing(50)

        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addStretch(1)
        v_layout.addLayout(h_layout)
        v_layout.addStretch(1)

        # 在左下角添加设置入口
        self._add_settings_entry(v_layout)

        container.setLayout(v_layout)

    def _add_settings_entry(self, main_layout: QVBoxLayout) -> None:
        """
        在左下角添加设置入口
        """

        # 创建设置标签
        settings_label = QLabel()
        settings_label.setText(t("settings.text_icon"))
        settings_label.setObjectName("settingsEntry")
        settings_label.setCursor(QCursor(Qt.PointingHandCursor))

        # 设置样式
        settings_label.setStyleSheet("""
            QLabel#settingsEntry {
                color: #666666;
                font-size: 12px;
                padding: 5px 10px;
                border-radius: 4px;
                background-color: rgba(0, 0, 0, 0.05);
            }
            QLabel#settingsEntry:hover {
                color: #333333;
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)

        # 设置字体
        font = QFont()
        font.setPointSize(9)
        settings_label.setFont(font)

        # 连接点击事件
        settings_label.mousePressEvent = self._on_settings_clicked

        # 创建底部布局容器
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        # 将设置标签放在左下角
        bottom_layout.addWidget(settings_label, 0, Qt.AlignLeft)
        bottom_layout.addStretch(1)

        # 将底部容器添加到主布局
        main_layout.addWidget(bottom_container, 0, Qt.AlignBottom)

        # 保存引用以便后续使用
        self.settings_label = settings_label

    def _on_settings_clicked(self, event) -> None:
        """
        设置标签点击事件
        """
        from ui.construct.widgets.SettingsDialog import SettingsDialog

        if event.button() == Qt.LeftButton:
            if not hasattr(self, '_settings_dialog'):
                self._settings_dialog = SettingsDialog(self)
            self._settings_dialog.show_dialog()
            event.accept()
        else:
            # 对于其他鼠标事件，调用父类处理
            super(type(self), self).mousePressEvent(event)

    def mouseDoubleClickEvent(self, a0: QMouseEvent | None) -> None:
        widget_under_mouse = QApplication.widgetAt(a0.globalPos())
        if widget_under_mouse is not None and widget_under_mouse != self and widget_under_mouse != self.centralWidget():
            return
        super().mouseDoubleClickEvent(a0)
        self.hide()
        self.floating_ball.show()

    def force_stop(self):
        self.close()

    def stop(self):
        self.close()

    def _handle_ball_clicked(self):
        self.show()
        self.floating_ball.close()

    def _connect_remote_server(self):
        self.server.shutdown(quit_app=False)
        rs = RemoteServer()
        try:
            rs.start()
            self.server = rs
            LOG.info(f'Connected to RemoteServer {self.server} successfully')
        except Exception as e:
            LOG.error(f"Failed to start RemoteServer: {e}", exc_info=True)
        else:
            register_event_handler(ExitEvent, lambda ev: rs.disconnect_remote())
            register_stop(rs.shutdown)
            set_server(rs)
            try:
                self.load_subjects()
            except Exception:
                LOG.exception("Failed to load subjects after connecting remote")

    # ========== subject 管理 ==========
    def clear_subjects(self) -> None:
        while self.subject_layout.count():
            item = self.subject_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def load_subjects(self) -> None:
        self.clear_subjects()

        settings_obj = get_property('settings', _type=Settings)
        self.settings = settings_obj
        self.subjects = []

        if not settings_obj:
            return

        for _subject in settings_obj.get('subjects', []):
            subject = Subject(
                _subject.get('id'),
                _subject.get('name'),
                _subject.get('display_name', _subject.get('name')),
                _subject.get('color', '#FFFFFF')
            )

            subject.assignments_card = SubjectCard(
                subject,
                self.centralWidget()
            )
            subject.assignments_card.modify_label_color(subject.color)

            self.subject_layout.addWidget(subject.assignments_card)

            self.subjects.append(subject)

            assignments: list[Assignment] = self.server.get_assignment_by_id(subject.id)
            for ass in assignments:
                if 'file' in ass.data_type:
                    if self.server.is_local:
                        _data = get_res_data(ass.data)
                        self._handle_res(subject, ass, _data)
                    else:
                        sv: RemoteServer = self.server
                        sv.request_resource(ass.data_type, ass.data, lambda data:
                        run_on_ui_thread(lambda:
                                         self._handle_res(subject, ass, data)
                                         )
                                            )
                elif ass.data_type == 'text':
                    text: str = ass.data
                    label = MLabel()
                    label.setText(text)
                    label.setStyleSheet(load_qss_s("label_assignment", self.settings.get('theme', 'classic')))
                    label.set_color(color=subject.color)

                    ass_card = AssignmentCard(ass, server=self.server, theme=self.settings.get('theme', 'classic'),
                                              _settings=self.settings,
                                              _dialog_parent=self.centralWidget())
                    ass_card.set(label)

                    subject.assignments_card.add_assignment(ass_card)

        self.subject_layout.addStretch(1)

    def _add_ass(self, subject: Subject, ass: Assignment, widget) -> None:
        subject.assignments_card.add_assignment(
            _ass_c := AssignmentCard(
                ass,
                server=self.server,
                theme=self.settings.get('theme', 'classic') if self.settings else None,
                _settings=self.settings,
                _dialog_parent=self.centralWidget()
            )
        )
        _ass_c.set(widget)

    def _handle_res(self, subject: Subject, ass: Assignment, data) -> None:
        img = QImage()
        img.loadFromData(QByteArray(data))
        label = ImageLabel(img)
        self._add_ass(subject, ass, label)


def detect_image_ext(content: bytes) -> str | None:
    if not content or len(content) < 4:
        return None
    if content[:3] == b'\xff\xd8\xff':
        return 'jpg'
    if content.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if content.startswith(b'GIF87a') or content.startswith(b'GIF89a'):
        return 'gif'
    if content.startswith(b'BM'):
        return 'bmp'
    if content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return 'webp'
    return None


def main() -> int:
    app = QApplication(sys.argv)
    main_window = MainWindow()

    register_stop(run_on_ui_thread(main_window.force_stop))
    if '--no-main-window' in sys.argv:
        main_window.hide()
        main_window.floating_ball.show()
    else:
        main_window.show()
    LOG.info(t('ui.main_window.show'))
    return app.exec_()


def run_on_ui_thread(func):
    def wrapper(*args, **kwargs):
        app = QApplication.instance()
        if app is None:
            LOG.error("No QApplication instance found when trying to run on UI thread.")
            return
        if app.thread() == QThread.currentThread():
            return func(*args, **kwargs)
        else:
            result_container = []

            def call_func():
                result_container.append(func(*args, **kwargs))

            QTimer.singleShot(0, call_func)
            while not result_container:
                app.processEvents()
            return result_container[0]

    return wrapper
