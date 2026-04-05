import os
import sys
from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import QTimer, QThread
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QMainWindow, QApplication, QVBoxLayout, QWidget, QHBoxLayout

from core.app import APP, register_stop, get_server, set_server, get_property
from core.crash_report import CrashReport
from core.events import register_event_handler, ExitEvent
from core.i18n import t
from core.server.server import AgendaXServer, ServerStartedEvent, Assignment
from core.settings import Settings
from core.utils.logger.logging import getLogger
from core.utils.path_utils import get_res_path
from platforms.windows.winui import enable_win_blur_background
from ui.construct.floating_ball import AgendaXFloatingBall
from ui.construct.subject_card import SubjectCard
from ui.utils.RemoteServer import RemoteServer

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
    server: AgendaXServer = None
    subjects: list

    def __init__(self) -> None:
        register_event_handler(
            ServerStartedEvent, self._set_server
        )
        super().__init__()
        self.floating_ball = AgendaXFloatingBall()
        self.floating_ball.set_click_action(self._handle_ball_clicked)
        self.floating_ball.setIcon(os.path.join(get_res_path('icon'), 'icon.png'))
        self.floating_ball.set_exit_action(self.stop)
        self.init_ui()
        if (server := get_server()) is not None:
            LOG.info(f'Connected to Server {server} successfully')
            self.server = server
        # 在窗口初始化完成后加载 subjects（无论是否有 server）
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
        self.subject_layout_widget = QWidget()
        self.subject_layout = QVBoxLayout(self.subject_layout_widget)

        h_layout = QHBoxLayout()
        h_layout.addSpacing(50)
        h_layout.addWidget(self.subject_layout_widget)
        h_layout.addSpacing(50)
        v_layout = QVBoxLayout()
        v_layout.addSpacing(10)
        v_layout.addSpacing(10)
        v_layout.addStretch()
        v_layout.addLayout(h_layout)
        v_layout.addStretch()
        container.setLayout(v_layout)


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

    # ========== 新增/修改方法 ==========
    def clear_subjects(self) -> None:
        """清空 subject_layout 中已有的控件（并释放父控件引用）"""
        while self.subject_layout.count():
            item = self.subject_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def load_subjects(self) -> None:
        """
        从 settings 获取 subjects 列表；对每个 subject，尝试从 server 获取 assignments（兼容 RemoteServer 或 本地 server.database）。
        无 assignment 时仍创建 SubjectCard 来显示 subject。
        """
        self.clear_subjects()

        settings_obj = get_property('settings', _type=Settings)
        self.subjects: list[Subject] = []

        if settings_obj:
            for _subject in settings_obj.get('subjects', []):
                _subject: dict
                self.subjects.append(Subject(
                    _subject.get('id'), _subject.get('name'), _subject.get('display_name', _subject.get('name')), _subject.get('color', '#FFFFFF'))
                )

        for subject in self.subjects:
            if not subject.assignments_card:
                subject.assignments_card = SubjectCard(subject.display_name)
                self.subject_layout.addWidget(subject.assignments_card)
            _assignments: list[Assignment] = self.server.get_assignment_by_id(subject.id)

        # # 如果没有 subjects，至少显示一个默认占位
        # if not subjects:
        #     lbl = QLabel(t('ui.main_window.no_subjects') if 'ui' in globals() else "No subjects")
        #     self.subject_layout.addWidget(lbl)
        #     return
        #
        # # ensure cache dir for resources
        # cache_dir = os.path.join(get_work_dir('.app'), 'cache')
        # os.makedirs(cache_dir, exist_ok=True)
        #
        # # 2. 针对每个 subject，尝试获取 assignments
        # for subj in subjects:
        #     # 规范化 subject id（支持 settings 中 subject 为 dict 的情况）
        #     subj_id = None
        #     if isinstance(subj, dict):
        #         subj_id = subj.get('id') or subj.get('name') or str(subj)
        #     else:
        #         subj_id = str(subj)
        #     assignments = []
        #     if self.server:
        #         try:
        #             # RemoteServer 优先使用 list_assignments
        #             if hasattr(self.server, "list_assignments"):
        #                 try:
        #                     assignments = self.server.list_assignments(subj_id)
        #                 except Exception:
        #                     LOG.debug(f"Remote list_assignments failed for {subj}", exc_info=True)
        #                     assignments = []
        #             # 本地 server 可能有 database 接口
        #             if not assignments and hasattr(self.server, "database"):
        #                 try:
        #                     assignments = self.server.database.get_by_subject(subj_id)
        #                 except Exception:
        #                     LOG.debug(f"Local database get_by_subject failed for {subj}", exc_info=True)
        #                     assignments = []
        #         except Exception:
        #             LOG.exception(f"Error while fetching assignments for subject: {subj}")
        #
        #     # 若 assignment 存在，且类型为 file:*，尝试请求资源并缓存为本地文件
        #     if assignments:
        #         for a in assignments:
        #             try:
        #                 # 确保 assignment.subject 有值（服务器可能未返回），回填为 subj_id
        #                 try:
        #                     if not getattr(a, "subject", None):
        #                         a.subject = subj_id
        #                 except Exception:
        #                     pass
        #
        #                 # 如果是文件资源，尝试从服务器请求真实 bytes 并写入缓存文件
        #                 try:
        #                     dtype = getattr(a, "data_type", "") or ""
        #                     data_ref = getattr(a, "data", "") or ""
        #                     if dtype.startswith("file:") and data_ref and hasattr(self.server, "request_resource_sync"):
        #                         try:
        #                             content = self.server.request_resource_sync(dtype, data_ref, timeout=5.0)
        #                             if content:
        #                                 # 尝试识别图片扩展名（使用 detect_image_ext 替代 imghdr）
        #                                 ext = detect_image_ext(content) or "bin"
        #                                 fname = f"{uuid.uuid4().hex}.{ext}"
        #                                 fpath = os.path.join(cache_dir, fname)
        #                                 try:
        #                                     with open(fpath, "wb") as f:
        #                                         f.write(content)
        #                                     # 将 assignment.data 指向本地缓存路径，供 SubjectCard 使用
        #                                     a.data = fpath
        #                                 except Exception:
        #                                     LOG.debug("Failed to save resource to cache", exc_info=True)
        #                         except Exception:
        #                             LOG.debug("request_resource_sync failed", exc_info=True)
        #                 except Exception:
        #                     LOG.debug("Resource handling error", exc_info=True)
        #
        #                 # 使用统一的创建逻辑，确保回退可显示
        #                 card = create_subject_card(a, subj_id)
        #             except TypeError:
        #                 try:
        #                     card = create_subject_card(getattr(a, "subject", subj_id) or subj_id, subj_id)
        #                 except Exception:
        #                     card = QLabel(str(a.subject))
        #             except Exception:
        #                 LOG.debug("Failed to create SubjectCard from assignment", exc_info=True)
        #                 card = QLabel(str(subj))
        #             self.subject_layout.addWidget(card)
        #     else:
        #         # 没有 assignment 时也显示 subject（保证界面不空）
        #         try:
        #             # 以 subject id 作为参数构造 SubjectCard（兼容 settings 中 dict）
        #             card = create_subject_card(subj, subj_id)
        #         except Exception:
        #             # 回退为简单 QLabel
        #             card = QLabel(str(subj))
        #         self.subject_layout.addWidget(card)

def detect_image_ext(content: bytes) -> str | None:
    """
    返回常见图片扩展名（不含点），若无法识别返回 None。
    支持: jpg, png, gif, bmp, webp
    """
    if not content or len(content) < 4:
        return None
    # JPEG: FF D8 FF
    if content[:3] == b'\xff\xd8\xff':
        return 'jpg'
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if content.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    # GIF: GIF87a / GIF89a
    if content.startswith(b'GIF87a') or content.startswith(b'GIF89a'):
        return 'gif'
    # BMP: 'BM'
    if content.startswith(b'BM'):
        return 'bmp'
    # WEBP: 'RIFF'....'WEBP'
    if content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return 'webp'
    return None


def main() -> int:
    """
    在 main() 内创建 QApplication 和 MainWindow，确保在 UI 主线程创建 Qt 对象。
    """
    app = QApplication(sys.argv)
    main_window = MainWindow()
    register_stop(run_on_ui_thread(main_window.force_stop))
    main_window.show()
    LOG.info(t('ui.main_window.show'))
    return app.exec_()


def run_on_ui_thread(func):
    """
    装饰器：确保被装饰的函数在 UI 线程执行。
    如果当前线程是 UI 线程，直接调用；否则通过 QTimer.singleShot 切换到 UI 线程。
    """

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
