import time
from typing import Optional

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt, QBuffer, QIODevice
from PyQt5.QtGui import QFont

from core.app import get_property, get_server
from core.server.packets import ResourceResponsePacket
from core.server.server import Assignment
from core.settings import Settings
from ui.construct.bases.abstract_widget import MLabel
from ui.construct.bases.card import Card
from ui.construct.widgets.AddAssignmentDialog import AddAssignmentDialog
from ui.construct.widgets.AssignmentCard import AssignmentCard, ImageLabel
from ui.utils.qss_loader import load_qss_s


class SubjectCard(Card):
    def __init__(self, subject, dialog_parent=None, auto_load=True):
        self._subject_label = None
        from ui.main import Subject
        self._assignments_layout = None
        self._assignments_container = None
        self._dialog_parent = dialog_parent

        self._subject: Subject = subject
        self._assignment_cards = []

        self.settings = get_property('settings', _type=Settings)

        self._theme = self.settings.get('theme', 'classic') if self.settings else None
        self._add_assignment_dialog = AddAssignmentDialog(dialog_parent, theme=self._theme, subject_color=subject.color)
        self._add_assignment_dialog.assignment_widget.register_confirm_handler(
            lambda ignored: self._on_finish_add_assignment()
        )

        super().__init__()

        if auto_load:
            self.load()
            self.setStyleSheet(load_qss_s("subject_card", self._theme))

    def init_card(self):
        main_layout = QHBoxLayout()
        container = QWidget()
        container.setLayout(main_layout)

        self.set_center(container)

        main_layout.setContentsMargins(0, 0, 0, 0)

        self._subject_label = MLabel(self._subject.display_name)
        self._subject_label.setObjectName("subjectLabel")
        self._subject_label.setAlignment(Qt.AlignCenter)
        self._subject_label.setFixedHeight(70)
        self._subject_label.setFixedWidth(70)
        if self.settings:
            theme = self.settings.get('theme', 'classic')
        else:
            theme = None
        self._subject_label.setStyleSheet(load_qss_s("subject_label_", theme))
        self._subject_label.clicked.connect(self._handle_add_assignment)

        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self._subject_label.setFont(font)
        self._subject_label.setMinimumHeight(30)

        main_layout.addWidget(self._subject_label)

        self._assignments_container = QWidget()
        self._assignments_layout = QVBoxLayout(self._assignments_container)
        self._assignments_layout.setContentsMargins(0, 0, 0, 0)
        self._assignments_layout.setSpacing(6)
        self._assignments_layout.setAlignment(Qt.AlignTop)

        self._assignments_container.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )

        main_layout.addWidget(self._assignments_container)

        main_layout.setStretch(main_layout.indexOf(self._subject_label), 0)
        main_layout.setStretch(main_layout.indexOf(self._assignments_container), 1)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

    def _handle_add_assignment(self):
        self._add_assignment_dialog.show_dialog()

    def _on_finish_add_assignment(self):
        ass: Optional[Assignment] = None
        label = None
        if (text := self._add_assignment_dialog.assignment_widget.get_text()) == "":
            img = self._add_assignment_dialog.assignment_widget.image()

            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            img.save(buffer, "PNG")
            data = buffer.data()
            hashed = str(data.__hash__())

            if sv := get_server():
                if sv.is_local:
                    sv.save_resource(file_name=hashed, data=data)
                else:
                    sv.send_packet(None, ResourceResponsePacket.create(hashed, data))
                ass = Assignment.create(self._subject.id, 'file:img', hashed, time.time(), (t:=self._add_assignment_dialog.assignment_widget.get_finish_time())[0], t[1])
                sv.update_assignment(ass)
                buffer.close()
                label = ImageLabel(img)
            else:
                pass
        else:
            ass = Assignment.create(self._subject.id, 'text', text, time.time(), (t:=self._add_assignment_dialog.assignment_widget.get_finish_time())[0], t[1])
            label = MLabel()
            label.setText(text)
            label.setStyleSheet(load_qss_s("label_assignment", self._theme))
            label.set_color(color=self._subject.color)
            if sv := get_server():
                sv.update_assignment(ass)
            else:
                pass
        if ass and label:
            ass_card = AssignmentCard(ass, server=sv, theme=self._theme, _settings=self.settings, _dialog_parent=self._dialog_parent)
            ass_card.set(label)
            self.add_assignment(ass_card)

    def set(self, child: QWidget):
        # 保持接口兼容
        pass

    def add_assignment(self, assignment_card: AssignmentCard):
        if assignment_card not in self._assignment_cards:
            self._assignment_cards.append(assignment_card)

            self._assignments_layout.addStretch(0)
            self._assignments_layout.addWidget(assignment_card)

            self._assignments_layout.setStretchFactor(assignment_card, 0)

            self.updateGeometry()
            self.adjustSize()

    def remove_assignment(self, assignment_card: AssignmentCard):
        if assignment_card in self._assignment_cards:
            self._assignment_cards.remove(assignment_card)
            self._assignments_layout.removeWidget(assignment_card)
            assignment_card.setParent(None)

            self.updateGeometry()
            self.adjustSize()

    def clear_assignments(self):
        for card in self._assignment_cards[:]:
            self.remove_assignment(card)

    def modify_label_color(self, color: str):
        self._subject_label.setStyleSheet(
            'MLabel {' + f'color: {color};' + '}'
        )
