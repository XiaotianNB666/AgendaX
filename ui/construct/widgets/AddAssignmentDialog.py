from ui.construct.widgets.InlineDialogWidget import InlineDialogWidget

from typing import override
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from core.i18n import t
from ui.construct.bases.abstract_widget import MLineEdit
from ui.construct.widgets.WhiteboardWidget import WhiteboardWidget
from ui.utils.qss_loader import load_qss_s
from ui.construct.widgets.TimeSelectWidget import TimeSelectWidget


class AddAssignmentWidget(WhiteboardWidget):
    def __init__(self, parent=None, theme=None, pen_color='#000000', background_color='#ffffff'):
        self.theme = theme
        super().__init__(parent, pen_color, background_color)
        self._init_text_input()
        self._init_time_select()

    def _init_text_input(self):
        self.text_input = MLineEdit(self)
        self.text_input.setPlaceholderText("请输入作业内容...")
        self.text_input.setFixedHeight(34)

        font = QFont("Microsoft YaHei", 12)
        self.text_input.setFont(font)
        self.text_input.setStyleSheet(load_qss_s('line_edit_', self.theme))
        self.text_input.setAttribute(Qt.WA_InputMethodEnabled, True)

        main_layout = self.layout()
        if main_layout is None:
            return

        # 插入到工具栏下方
        main_layout.insertWidget(1, self.text_input)

    def _init_time_select(self):
        self.time_select = TimeSelectWidget(self, self.theme)

        main_layout = self.layout()
        if main_layout is None:
            return

        main_layout.addWidget(self.time_select)

    def get_text(self) -> str:
        return self.text_input.text().strip()

    def set_text(self, text: str):
        self.text_input.setText(text)

    def get_finish_time(self) -> tuple[float, str]:
        return self.time_select.get_datetime()

    def get_finish_time_type(self) -> str:
        return self.time_select.get_time_text()

    @override
    def clear(self):
        self.text_input.clear()
        super().clear()

class AddAssignmentDialog(InlineDialogWidget):
    def __init__(
            self,
            parent=None,
            title=t('ui.assignment.title'),
            theme=None,
            subject_color: str = '#000000',
            background_color: str = '#ffffff'
    ):
        super().__init__(parent, title, draggable=True, show_title_bar=True)

        self.setMinimumSize(400, 300)
        self.resize(500, 350)

        self.theme = theme
        self.assignment_widget = AddAssignmentWidget(
            self,
            theme=self.theme,
            pen_color=subject_color,
            background_color=background_color
        )

        self.assignment_widget.text_input.setStyleSheet(
            f"QLineEdit {{ color: {subject_color}; }}"
        )

        self.set_content(self.assignment_widget)
