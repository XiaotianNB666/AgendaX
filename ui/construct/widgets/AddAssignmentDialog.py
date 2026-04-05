from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from core.i18n import t
from ui.construct.widgets.InlineDialogWidget import InlineDialogWidget
from ui.construct.widgets.WhiteboardWidget import WhiteboardWidget


class AddAssignmentWidget(WhiteboardWidget):
    """
    作业添加控件：
    - 顶部：文本输入框（支持虚拟键盘）
    - 工具栏：笔 / 橡皮 / 撤销 / 确定 / 取消
    - 下方：手写白板区域
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_text_input()

    def _init_text_input(self):
        """
        在原有 WhiteboardWidget 工具栏中插入文本输入框
        """
        # ===== 创建文本输入框 =====
        self._text_input = QLineEdit(self)
        self._text_input.setPlaceholderText("请输入作业内容...")
        self._text_input.setFixedHeight(34)

        # 设置字体：微软雅黑
        font = QFont("Microsoft YaHei", 12)
        self._text_input.setFont(font)

        # 确保启用输入法（Windows 虚拟键盘必须）
        self._text_input.setAttribute(Qt.WA_InputMethodEnabled, True)

        # ===== 找到工具栏 layout =====
        # WhiteboardWidget 的主布局是 QVBoxLayout
        main_layout = self.layout()
        if main_layout is None:
            return

        # 第一个元素是 toolbar (QHBoxLayout)
        toolbar = main_layout.itemAt(0).layout()
        if toolbar is None:
            return

        # 在工具栏上方插入文本输入框
        main_layout.insertWidget(0, self._text_input)


    def get_text(self) -> str:
        """获取用户输入的文本"""
        return self._text_input.text().strip()

    def set_text(self, text: str):
        """设置文本内容"""
        self._text_input.setText(text)

    def clear_all(self):
        """清空文本和白板"""
        self._text_input.clear()
        self.clear()


class AddAssignmentDialog(InlineDialogWidget):

    def __init__(self, parent=None, title=t('ui.assignment.title')):
        super().__init__(parent, title, draggable=True, show_title_bar=True)

        self.setMinimumSize(400, 300)
        self.resize(500, 350)

        self.assignment_widget = AddAssignmentWidget(self)

        self.set_content(self.assignment_widget)
