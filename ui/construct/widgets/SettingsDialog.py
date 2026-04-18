from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout
)

from core.app import get_property
from core.i18n import t, get_locale, set_locale
from core.settings import Settings

from ui.construct.bases.abstract_widget import (
    MComboBox,
    MLabel,
    MPushButton,
    MLineEdit
)
from ui.construct.widgets.InlineDialogWidget import InlineDialogWidget
from ui.utils.qss_loader import load_qss, load_qss_s


class SettingsDialog(InlineDialogWidget):

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            parent=parent,
            title=t("settings.title"),
            draggable=True,
            show_title_bar=True
        )

        self._settings: Settings = get_property('settings')
        self.init_ui()
        self._load_settings()

    def init_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)

        form = QFormLayout()

        self.theme_combo = MComboBox()
        self.theme_combo.addItems(["classic"])
        form.addRow(t("settings.theme"), self.theme_combo)

        self.lang_combo = MComboBox()
        self.lang_combo.addItems(["zh-CN", "en"])
        form.addRow(t("settings.language"), self.lang_combo)

        self.display_name_input = MLineEdit()

        self.display_name_input.setStyleSheet(load_qss_s('modern_widget_light'))

        self.display_name_input.setPlaceholderText(
            t("settings.display_name_hint")
        )
        form.addRow(
            t("settings.display_name"),
            self.display_name_input
        )

        layout.addLayout(form)

        hint = MLabel(t("settings.restart_hint"))
        hint.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(hint)

        btn_layout = QHBoxLayout()
        self.save_btn = MPushButton(t("settings.save"))
        self.cancel_btn = MPushButton(t("settings.cancel"))

        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.hide_dialog)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

        self.set_content(container)

    def _load_settings(self) -> None:
        try:
            self.theme_combo.setCurrentText(
                self._settings.get("theme", "classic")
            )
            self.lang_combo.setCurrentText(
                self._settings.get("lang", "zh-CN")
            )
            self.display_name_input.setText(
                self._settings.get("display_name", "")
            )
        except Exception:
            pass

    def _save(self) -> None:
        self._settings._settings["theme"] = self.theme_combo.currentText()
        self._settings._settings["lang"] = self.lang_combo.currentText()
        self._settings._settings["display_name"] = (
            self.display_name_input.text().strip()
        )

        self._settings.save_async()

        if self.lang_combo.currentText() != get_locale():
            set_locale(self.lang_combo.currentText())

        self.hide_dialog()
