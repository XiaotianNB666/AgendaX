from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont

from core.app import get_property
from core.settings import Settings
from ui.construct.bases.card import Card
from ui.construct.widgets.AssignmentCard import AssignmentCard
from ui.utils.qss_loader import load_qss_s


class SubjectCard(Card):
    def __init__(self, subject_name: str, auto_load=True):
        self._assignments_layout = None
        self._assignments_container = None
        self._subject_name = subject_name
        self._assignment_cards = []

        self.settings = get_property('settings', _type = Settings)
        super().__init__()
        if auto_load:
            self.load()
            self.setStyleSheet(load_qss_s("subject_card", self.settings.get('theme', 'classic') if self.settings else None))


    def init_card(self):

        main_layout = QHBoxLayout()
        container = QWidget()
        container.setLayout(main_layout)

        self.set_center(container)

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        self._subject_label = QLabel(self._subject_name)
        self._subject_label.setObjectName("subjectLabel")
        self._subject_label.setAlignment(Qt.AlignCenter)
        self._subject_label.setFixedHeight(50)
        self._subject_label.setFixedWidth(50)
        if self.settings:
            theme = self.settings.get('theme', 'classic')
        else:
            theme = None
        self._subject_label.setStyleSheet(load_qss_s("subject_label_", theme))

        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self._subject_label.setFont(font)
        self._subject_label.setMinimumHeight(30)

        main_layout.addWidget(self._subject_label)

        self._assignments_container = QWidget()
        self._assignments_layout = QHBoxLayout(self._assignments_container)
        self._assignments_layout.setContentsMargins(0, 0, 0, 0)
        self._assignments_layout.setSpacing(6)

        main_layout.addWidget(self._assignments_container)

        main_layout.setStretch(main_layout.indexOf(self._subject_label), 0)
        main_layout.setStretch(main_layout.indexOf(self._assignments_container), 1)

    def init_size(self, obj: QSize = None):
        ...

    def set(self, child: QWidget):
        # 保持接口兼容
        pass

    def add_assignment(self, assignment_card: AssignmentCard):
        if assignment_card not in self._assignment_cards:
            self._assignment_cards.append(assignment_card)
            self._assignments_layout.addWidget(assignment_card)

    def remove_assignment(self, assignment_card: AssignmentCard):
        if assignment_card in self._assignment_cards:
            self._assignment_cards.remove(assignment_card)
            self._assignments_layout.removeWidget(assignment_card)
            assignment_card.setParent(None)

    def clear_assignments(self):
        for card in self._assignment_cards[:]:
            self.remove_assignment(card)
