from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont
from ui.construct.bases.card import Card
from ui.construct.widgets.AssignmentCard import AssignmentCard


class SubjectCard(Card):
    def __init__(self, subject_name: str, auto_load=True):
        self._assignments_layout = None
        self._assignments_container = None
        self._subject_name = subject_name
        self._assignment_cards = []

        super().__init__()
        if auto_load:
            self.load()

    def init_card(self):
        """
        关键点：
        - 不再 new QVBoxLayout(self)
        - 直接使用 Card 的 layout
        """

        main_layout = self.layout()
        if main_layout is None:
            main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # ===== 学科标题 =====
        self._subject_label = QLabel(self._subject_name)
        self._subject_label.setObjectName("subjectLabel")
        self._subject_label.setAlignment(Qt.AlignLeft)

        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self._subject_label.setFont(font)
        self._subject_label.setMinimumHeight(30)

        main_layout.addWidget(self._subject_label)

        # ===== 作业容器 =====
        self._assignments_container = QWidget()
        self._assignments_layout = QVBoxLayout(self._assignments_container)
        self._assignments_layout.setContentsMargins(0, 0, 0, 0)
        self._assignments_layout.setSpacing(6)

        main_layout.addWidget(self._assignments_container)

        # 拉伸：标题固定，作业区撑开
        main_layout.setStretch(main_layout.indexOf(self._subject_label), 0)
        main_layout.setStretch(main_layout.indexOf(self._assignments_container), 1)

    def init_size(self, obj: QSize = None):
        if obj is not None:
            self.setMinimumWidth(int(obj.width() * 0.8))
        else:
            self.setMinimumWidth(300)

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