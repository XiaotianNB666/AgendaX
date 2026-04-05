from typing import override

from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from core.i18n import t
from ui.construct.bases.abstract_widget import MLineEdit
from ui.construct.widgets.InlineDialogWidget import InlineDialogWidget
from ui.construct.widgets.WhiteboardWidget import WhiteboardWidget
from ui.utils.qss_loader import load_qss_s


class AddAssignmentWidget(WhiteboardWidget):
    """
    作业添加控件：
    - 顶部：文本输入框（支持虚拟键盘）
    - 工具栏：笔 / 橡皮 / 撤销 / 确定 / 取消
    - 下方：手写白板区域
    """

    def __init__(self, parent=None, theme=None, pen_color='#000000'):
        self.theme = theme
        super().__init__(parent, pen_color)
        self._init_text_input()

    def _init_text_input(self):
        """
        在原有 WhiteboardWidget 工具栏中插入文本输入框
        """
        # ===== 创建文本输入框 =====
        self.text_input = MLineEdit(self)
        self.text_input.setPlaceholderText("请输入作业内容...")
        self.text_input.setFixedHeight(34)

        # 设置字体：微软雅黑
        font = QFont("Microsoft YaHei", 12)
        self.text_input.setFont(font)
        self.text_input.setStyleSheet(load_qss_s('line_edit_', self.theme))

        self.text_input.setAttribute(Qt.WA_InputMethodEnabled, True)

        main_layout = self.layout()
        if main_layout is None:
            return

        toolbar = main_layout.itemAt(0).layout()
        if toolbar is None:
            return
        main_layout.insertWidget(0, self.text_input)

    def get_text(self) -> str:
        """获取用户输入的文本"""
        return self.text_input.text().strip()

    def set_text(self, text: str):
        """设置文本内容"""
        self.text_input.setText(text)

    @override
    def clear(self):
        self.text_input.clear()
        super().clear()


class AddAssignmentDialog(InlineDialogWidget):

    def __init__(self, parent=None, title=t('ui.assignment.title'), theme=None, subject_color: str = '#000000'):
        super().__init__(parent, title, draggable=True, show_title_bar=True)

        self.setMinimumSize(400, 300)
        self.resize(500, 350)
        self.theme = theme
        self.assignment_widget = AddAssignmentWidget(self, theme=self.theme, pen_color=subject_color)
        self.assignment_widget.text_input.setStyleSheet('QLineEdit {'f'color:{subject_color};''}')

        self.set_content(self.assignment_widget)
