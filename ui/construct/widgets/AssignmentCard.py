from typing import Optional

from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, QDateTime, QBuffer
from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QImage, QPixmap

from core.app import get_server
from core.i18n import t
from core.server.packets import ResourceResponsePacket, AssignmentDelPacket
from core.server.server import Assignment, AgendaXServer
from core.settings import Settings
from ui.construct.bases.abstract_widget import MLabel
from ui.construct.bases.card import Card
from ui.construct.widgets.AddAssignmentDialog import AddAssignmentDialog
from ui.utils.RemoteServer import RemoteServer
from ui.utils.qss_loader import load_qss_s
from core.utils import time_utils


class CustomProgressBar(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0  # 0~100
        self._color = QColor("green")  # 默认绿色
        self.setFixedHeight(8)

    def set_progress(self, value: int, color: QColor):
        self._progress = max(0, min(100, value))
        self._color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. 绘制背景（灰色）
        bg_rect = self.rect()
        painter.fillRect(bg_rect, QColor("#e0e0e0"))

        # 2. 计算进度宽度
        progress_width = int(self.width() * self._progress / 100)
        progress_rect = bg_rect.adjusted(0, 0, progress_width - self.width(), 0)

        # 3. 设置渐变（从左到右）
        gradient = QLinearGradient(0, 0, progress_width, 0)
        gradient.setColorAt(0, self._color.lighter(120))
        gradient.setColorAt(1, self._color.darker(120))

        # 4. 设置画笔和画刷
        painter.setPen(Qt.NoPen)  # 无边框
        painter.setBrush(gradient)

        # 5. 绘制圆角矩形进度条（关键：只画进度部分，带圆角）
        painter.drawRoundedRect(progress_rect, 4, 4)


class ImageLabel(MLabel):
    def __init__(self, img: QImage):
        self.img = img
        super().__init__()
        self.setPixmap(QPixmap.fromImage(img))
        self.setScaledContents(True)


class AssignmentCard(Card):
    def __init__(
            self,
            assignment: Assignment,
            auto_load=True,
            server: Optional[AgendaXServer] = None,
            theme=None,
            _settings=None,
            _dialog_parent=None
    ):
        self._time_label = None
        self._progress_value = 0
        self._custom_progress = None
        self._assignment = assignment
        self._content_widget = None
        self._server = server
        self._settings: Settings = _settings
        self._img: Optional[ImageLabel] = None

        self._start_time = assignment.start_time
        self._deadline_timestamp = assignment.finish_time
        self._total_time_seconds = 0.0
        self._dialog_parent = _dialog_parent

        self._assignment: Assignment = assignment
        self._edit_dialog: Optional[AddAssignmentDialog] = None

        super().__init__()
        self._time_label.setStyleSheet(load_qss_s('label_', theme))
        self._timer = QTimer(self)

        if auto_load:
            self.load()

        self.init_size()
        self.start_timer()

    def parse_assignment(self):
        day = time_utils.get_day_name(
            time_utils.get_initial_time_of_this_day(self._assignment.finish_time)
        )
        text = f'{day} {self._assignment.finish_time_type}'
        self._time_label.setText(text)

        self._start_time = self._assignment.start_time
        self._deadline_timestamp = self._assignment.finish_time


    def init_card(self):
        self._time_label = MLabel()
        self.parse_assignment()
        self._time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._time_label.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Preferred
        )

        self._time_label.clicked.connect(self._edit_assignment)

        self.set_right(self._time_label)

        self._custom_progress = CustomProgressBar(self)
        self._custom_progress.setFixedHeight(5)
        self.set_bottom(self._custom_progress)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

    def init_size(self, obj=None):
        if obj is not None:
            self.resize(obj.width(), obj.height())
        else:
            self.resize(300, 80)

    def set(self, child: QWidget):
        self.set_center(child)
        if isinstance(child, ImageLabel):
            self._img = child

    def _edit_assignment(self):
        from ui.construct.widgets.AddAssignmentDialog import AddAssignmentDialog

        self._edit_dialog = AddAssignmentDialog(
            parent=self._dialog_parent,
            theme=None,
            subject_color="#FFFFFF"
        )

        self._edit_dialog.set_title(t('ui.assignment.edit_title'))

        if self._assignment.data_type == "text":
            self._edit_dialog.assignment_widget.set_text(self._assignment.data)
        elif self._assignment.data_type.startswith("file:"):
            self._edit_dialog.assignment_widget.set_image(self._img.img)

        self._edit_dialog.assignment_widget.register_confirm_handler(
            self._on_edit_confirmed
        )

        self._edit_dialog.show_dialog()

    def set_deadline(self, deadline_timestamp: float):
        self._deadline_timestamp = deadline_timestamp
        self._recalculate_total_time()

    def set_start_time(self, start_time: float):
        self._start_time = start_time
        self._recalculate_total_time()

    def _recalculate_total_time(self):
        if self._start_time is None:
            self._start_time = QDateTime.currentMSecsSinceEpoch() / 1000.0

        self._total_time_seconds = self._deadline_timestamp - self._start_time
        if self._total_time_seconds < 0:
            self._total_time_seconds = 0

    def start_timer(self):
        self._recalculate_total_time()
        self._timer.timeout.connect(self.update_progress)
        self._timer.start(1000)

    def update_progress(self):
        current_time = QDateTime.currentMSecsSinceEpoch() / 1000.0
        remaining_time = self._deadline_timestamp - current_time

        if remaining_time <= 0:
            self._progress_value = 100
            color = QColor("purple")
        else:
            if self._total_time_seconds > 0:
                progress_percent = 100 - (remaining_time / self._total_time_seconds) * 100
                self._progress_value = max(0, min(100, progress_percent))
            else:
                self._progress_value = 0

            if self._progress_value <= 40:
                color = QColor("green")
            elif self._progress_value <= 70:
                ratio = (self._progress_value - 40) / 30
                r = int(255 * ratio)
                g = 255
                color = QColor(r, g, 0)
            else:
                ratio = (self._progress_value - 70) / 30
                r = 255
                g = int(255 * (1 - ratio))
                color = QColor(r, g, 0)

        self._custom_progress.set_progress(int(self._progress_value), color)

    def stop_timer(self):
        self._timer.stop()

    def _on_edit_confirmed(self, _parent: AddAssignmentDialog):
        new_text = self._edit_dialog.assignment_widget.get_text()
        new_img = self._edit_dialog.assignment_widget.image()

        if new_text:
            self._assignment.data = new_text
            self._assignment.data_type = "text"
        else:
            buf = QBuffer()
            new_img.save(buf, "PNG")
            _data = buf.data()
            hashed = _data.__hash__()
            self._assignment.data = str(hashed)
            self._assignment.data_type = "file:img"
            buf.close()

            if sv := get_server():
                if sv.is_local:
                    sv.save_resource(str(hashed), _data)
                else:
                    server: RemoteServer = sv
                    server.send_packet(None,
                                       ResourceResponsePacket.create(str(hashed), _data)
                                       )

        new_time, time_type = self._edit_dialog.assignment_widget.get_finish_time()
        self._assignment.finish_time = float(new_time)
        self._assignment.finish_time_type = time_type

        self.parse_assignment()

        if sv := get_server():
            try:
                sv.update_assignment(self._assignment)
            except:
                import traceback
                traceback.print_exc()

        self._edit_dialog.hide_dialog()

    def del_this_assignment(self):
        if sv:=get_server():
            if sv.is_local:
                sv.del_assignment_by_id(self._assignment.id)
            else:
                server: RemoteServer = sv
                server.send_packet(None, AssignmentDelPacket.create(self._assignment.id))
