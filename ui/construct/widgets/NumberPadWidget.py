from PyQt5.QtWidgets import (QWidget, QGridLayout, QPushButton,
                             QLineEdit)
from typing import Optional, override, Callable

from ui.construct.bases.abstract_widget import ModernWidgetLight


class NumberPadWidget(ModernWidgetLight):
    _on_finish: Callable[[int], None] | None = None

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        buttons = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('←', 3, 0), ('0', 3, 1), ('√', 3, 2),
        ]

        for text, row, col in buttons:
            btn = QPushButton(text)
            btn.setFixedSize(60, 45)
            btn.setStyleSheet("border: none;")
            btn.clicked.connect(lambda checked, t=text: self.on_button_click(t))
            layout.addWidget(btn, row, col)

    def on_button_click(self, text: str) -> None:
        line_edit: Optional[QLineEdit] = self.parent().findChild(QLineEdit)
        if not line_edit:
            return

        if text == '←':
            current_text = line_edit.text()
            line_edit.setText(current_text[:-1])
        elif text == '√':
            current_text = line_edit.text()
            if current_text and self._on_finish:
                self._on_finish(int(current_text))
        else:
            line_edit.setText(line_edit.text() + text)

    def register_on_finish(self, handler: Callable[[int], None]) -> None:
        self._on_finish = handler

    @override
    def set(self, child: QWidget):
        pass
