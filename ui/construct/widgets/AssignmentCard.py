from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QPainter, QColor, QLinearGradient
from ui.construct.bases.card import Card


class CustomProgressBar(QWidget):
    """自定义绘制进度条（无 QProgressBar）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0  # 0~100
        self._color = QColor("green")  # 默认绿色
        self.setFixedHeight(8)  # 固定高度

    def set_progress(self, value: int, color: QColor):
        """设置进度值和颜色"""
        self._progress = max(0, min(100, value))
        self._color = color
        self.update()  # 触发重绘

    def paintEvent(self, event):
        """自定义绘制进度条"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制背景
        bg_rect = self.rect()
        painter.fillRect(bg_rect, QColor("#e0e0e0"))

        # 绘制进度块
        progress_width = int(self.width() * self._progress / 100)
        progress_rect = bg_rect.adjusted(0, 0, progress_width - self.width(), 0)

        # 使用渐变填充
        gradient = QLinearGradient(0, 0, progress_width, 0)
        gradient.setColorAt(0, self._color.lighter(120))
        gradient.setColorAt(1, self._color.darker(120))
        painter.fillRect(progress_rect, gradient)

        # 绘制圆角
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(progress_rect, 4, 4)


class AssignmentCard(Card):
    def __init__(self, parent=None, auto_load=True, deadline_timestamp: float = 0.0):
        """
        :param deadline_timestamp: 截止时间的 Unix 时间戳（float）
        """
        super().__init__(parent, auto_load)
        self._progress_value = 0  # 当前进度值（0~100）
        self._custom_progress = None
        self._title_label = None
        self._content_widget = None  # 用于 set(child) 的内容容器
        self._deadline_timestamp = deadline_timestamp  # 截止时间戳
        self._total_time_seconds = 0.0  # 作业总时间（秒）
        self._timer = QTimer(self)  # 定时器，用于实时更新进度条

        if auto_load:
            self.load()  # 加载 QSS 样式

        self.init_card()
        self.init_size()
        self.start_timer()  # 启动定时器，每秒更新一次进度条

    def init_card(self):
        """初始化卡片结构：标题、进度条、内容区域"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部标题区域
        self._top_widget = QWidget()
        top_layout = QHBoxLayout(self._top_widget)
        top_layout.setContentsMargins(8, 4, 8, 4)
        self._title_label = QLabel("数学作业")
        self._title_label.setObjectName("titleLabel")
        top_layout.addWidget(self._title_label)
        top_layout.addStretch()
        main_layout.addWidget(self._top_widget)

        # 进度条区域
        self._custom_progress = CustomProgressBar()
        main_layout.addWidget(self._custom_progress)

        # 内容区域（用于 set(child)）
        self._content_widget = QWidget()
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._content_widget)

        # 设置拉伸因子
        main_layout.setStretch(0, 0)  # 标题
        main_layout.setStretch(1, 0)  # 进度条
        main_layout.setStretch(2, 1)  # 内容区域

    def init_size(self, obj=None):
        """卡片尺寸（可选参数用于初始化动态调整）"""
        if obj is not None:
            self.resize(obj.width(), obj.height())
        else:
            self.resize(300, 80)  # 默认尺寸

    def set(self, child: QWidget):
        """设置内容区域的子控件"""
        self._content_widget.layout().addWidget(child)

    def set_deadline(self, deadline_timestamp: float):
        """设置截止时间（Unix 时间戳）"""
        self._deadline_timestamp = deadline_timestamp
        # 重新计算总时间（从创建时间到截止时间）
        current_time = QDateTime.currentMSecsSinceEpoch() / 1000.0
        self._total_time_seconds = self._deadline_timestamp - current_time
        if self._total_time_seconds < 0:
            self._total_time_seconds = 0  # 防止负数

    def start_timer(self):
        """启动定时器，每秒更新一次进度条"""
        self._timer.timeout.connect(self.update_progress)
        self._timer.start(1000)


def update_progress(self):
    """根据当前时间和截止时间更新进度条"""
    current_time = QDateTime.currentMSecsSinceEpoch() / 1000.0
    remaining_time = self._deadline_timestamp - current_time

    if remaining_time <= 0:
        # 超过截止时间：进度条变紫色，进度值为100
        self._progress_value = 100
        color = QColor("purple")
    else:
        # 计算百分比：p = 100 - (剩余时间 / 总时间) * 100
        if self._total_time_seconds > 0:
            progress_percent = 100 - (remaining_time / self._total_time_seconds) * 100
            self._progress_value = max(0, min(100, progress_percent))  # 限制在0~100
        else:
            self._progress_value = 0

        if self._progress_value <= 40:
            color = QColor("green")
        elif 40 < self._progress_value <= 100:
            # 从绿->黄->红（线性插值）
            if self._progress_value <= 70:
                # 绿->黄：40~70
                ratio = (self._progress_value - 40) / 30
                r = int(0 + (255 - 0) * ratio)
                g = int(255 - (255 - 255) * ratio)
                b = int(0 + (0 - 0) * ratio)
                color = QColor(r, g, b)
            else:
                # 黄->红：70~100
                ratio = (self._progress_value - 70) / 30
                r = int(255 + (255 - 255) * ratio)
                g = int(255 - (255 - 0) * ratio)
                b = int(0 + (0 - 0) * ratio)
                color = QColor(r, g, b)
        else:
            color = QColor("green")

    # 更新自定义进度条
    self._custom_progress.set_progress(int(self._progress_value), color)


def stop_timer(self):
    self._timer.stop()
