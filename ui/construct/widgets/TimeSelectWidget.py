# ui/construct/widgets/TimeSelectWidget.py

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSizePolicy

from core.app import get_property
from core.settings import Settings
from core.utils import time_utils, dict_utils
from core.utils.dict_utils import get_key_from_value
from ui.construct.bases.abstract_widget import MComboBox


class TimeSelectWidget(QWidget):
    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self._local_time_mapping: dict[str, int] = {}
        self.theme = theme
        self._init_ui()



    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.date_combo = MComboBox(theme=self.theme)
        self.time_combo = MComboBox(theme=self.theme)

        self._load_time_mapping()

        self._init_date_items()

        layout.addWidget(self.date_combo)
        layout.addWidget(self.time_combo)

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )

    def _init_date_items(self):
        today = time_utils.get_initial_time_of_this_day()
        for i in range(10):
            date = today + i * 24 * 3600
            text = time_utils.get_day_name(date)
            self._local_time_mapping[text] = date
            self.date_combo.addItem(text, date)

    def _load_time_mapping(self):
        settings: Settings = get_property("settings", Settings)
        self.mapping = settings.get("time_mapping", {}) if settings else {}

        for name, time_str in self.mapping.items():
            self.time_combo.addItem(name, time_str)

    def get_datetime(self):
        date = self.date_combo.currentData()
        time_str = self.time_combo.currentData()
        the_day = date
        the_second = time_utils.convert_hh_mm_ss_to_time_offset(time_str)
        return the_day + the_second, get_key_from_value(self.mapping, time_str)

    def set_datetime(self, timestamp: float):
        the_day = time_utils.get_day_name(time_utils.get_initial_time_of_this_day(timestamp))
        if the_day in self._local_time_mapping.keys():
            self.date_combo.setCurrentIndex(list(self._local_time_mapping).index(the_day))

        the_time = time_utils.get_closest_time(int(timestamp), [v for _, v in self.mapping.items()])
        the_time = dict_utils.get_key_from_value(self.mapping, the_time)
        self.time_combo.setCurrentIndex(list(self.mapping).index(the_time))

    def get_time_text(self):
        return self.time_combo.currentText()
