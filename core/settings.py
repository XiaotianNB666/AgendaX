import json
import os.path

from core.events import fire_event, SettingsLoadedEvent, register_event_handler, ReceiverGroup, ExitEvent, Receiver
from core.utils.path_utils import get_work_dir


class Settings:
    _settings: dict

    def __init__(self, data: str | None = None):
        if not data is None and isinstance(data, str):
            self.data = json.loads(data)
        else:
            app_dir = get_work_dir('.app')
            os.makedirs(app_dir, exist_ok=True)
            if os.path.isfile(settings_file := os.path.join(app_dir, '.settings')):
                with open(settings_file, 'r') as f:
                    self._settings = json.load(f)
            else:
                with open(settings_file, 'w') as f:
                    json.dump(self._create_default_settings(), f, ensure_ascii=False)
        fire_event(SettingsLoadedEvent(self._settings), ReceiverGroup.SERVER)
        register_event_handler(ExitEvent, self._save, Receiver.SETTINGS)

    def _create_default_settings(self) -> dict:
        from core.app import APP
        self._settings = {
            'version': APP.version,
            'subjects': []
        }
        return self._settings

    def _save(self, SystemExit):
        pass
