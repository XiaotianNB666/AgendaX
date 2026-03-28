from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QPainter, QColor, QLinearGradient

from core.server.server import Assignment
from ui.construct.bases.card import Card


class CustomProgressBar(QWidget):
    """自定义绘制进度条（无 QProgressBar）"""

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


class AssignmentCard(Card):
    def __init__(
            self,
            assignment: Assignment,
            auto_load=True
    ):
        self._progress_value = 0
        self._custom_progress = None
        self._assignment = assignment
        self._content_widget = None

        self._start_time = assignment.start_time
        self._deadline_timestamp = assignment.finish_time
        self._total_time_seconds = 0.0

        super().__init__()
        self._timer = QTimer(self)

        if auto_load:
            self.load()

        self.init_size()
        self.start_timer()

    def init_card(self):
        main_layout = self.layout()
        if main_layout is None:
            main_layout = QVBoxLayout(self)

        self._content_widget = QWidget()
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        self._custom_progress = CustomProgressBar(self)
        main_layout.addWidget(self._content_widget)
        main_layout.addWidget(self._custom_progress)

    def init_size(self, obj=None):
        if obj is not None:
            self.resize(obj.width(), obj.height())
        else:
            self.resize(300, 80)

    def set(self, child: QWidget):
        self._content_widget.layout().addWidget(child)

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
