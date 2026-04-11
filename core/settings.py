import json
import os.path
from typing import Any

from core.events import fire_event, SettingsLoadedEvent, register_event_handler, ReceiverGroup, ExitEvent, Receiver, \
    Event
from core.utils.path_utils import get_work_dir


class SettingsSavedEvent(Event):
    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings

    def get_value(self) -> Any:
        return self.settings


class Settings:
    _settings: dict

    def __init__(self, data: str | None = None):
        from core.app import set_property
        if not data is None and isinstance(data, str):
            self._settings = json.loads(data)
        else:
            app_dir = get_work_dir('.app')
            os.makedirs(app_dir, exist_ok=True)
            if os.path.isfile(settings_file := os.path.join(app_dir, '.settings')):
                try:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        self._settings = json.load(f)
                except:
                    self._settings = self._create_default_settings()
            else:
                with open(settings_file, 'w') as f:
                    json.dump(self._create_default_settings(), f, ensure_ascii=False)
        fire_event(SettingsLoadedEvent(self._settings), ReceiverGroup.SERVER)
        register_event_handler(ExitEvent, self._save, Receiver.SETTINGS)

        set_property('settings', self, Settings)

    def _create_default_settings(self) -> dict:
        from core.app import version
        self._settings = {
            'version': version(),
            'subjects': [
                {
                    "id": "chinese",
                    "name": "语文",
                    "display_name": "语",
                    "color": "#C00000"
                },
                {
                    "id": "math",
                    "name": "数学",
                    "display_name": "数",
                    "color": "#008BFE"
                },
                {
                    "id": "english",
                    "name": "英语",
                    "display_name": "英",
                    "color": "#EAB200"
                },
                {
                    "id": "physics",
                    "name": "物理",
                    "display_name": "物",
                    "color": "#227BDC"
                },
                {
                    "id": "chemistry",
                    "name": "化学",
                    "display_name": "化",
                    "color": "#802282"
                },
                {
                    "id": "biology",
                    "name": "生物",
                    "display_name": "生",
                    "color": "#71C107"
                }
            ],
            'theme': 'classic',
            'lang': 'zh-CN',
            'time_mapping': {
                '晚一': '19:25:00',
                '晚二': '20:20:00',
                '晚三': '21:45:00'
            }
        }
        return self._settings

    def _save(self) -> None:
        with open(os.path.join(get_work_dir('.app'), '.settings'), 'w', encoding='utf-8') as f:
            s = json.dumps(self._settings, ensure_ascii=False)
            f.write(s)
        fire_event(SettingsSavedEvent(self._settings), ReceiverGroup.SERVER)

    def get(self, path: str, default: Any = None) -> Any:
        """
        若路径中含有数字，先判断前面的是否为list，如 /a/b/0/c 则判断b是否为list，若是，则/a/b/0就是/a/b[0]；否则，解析为dict的key
        遇到错误返回 KeyError
        """
        try:
            if not path:
                raise KeyError("Empty path")

            current = self._settings
            parts = path.split("/")

            for part in parts:
                if part == "":
                    raise KeyError(f"Invalid path: {path}")

                if part.isdigit():
                    idx = int(part)

                    if not isinstance(current, list):
                        raise KeyError(
                            f"Expected list at '{part}', got {type(current).__name__}"
                        )

                    try:
                        current = current[idx]
                    except IndexError:
                        raise KeyError(f"Index {idx} out of range")

                else:
                    if not isinstance(current, dict):
                        raise KeyError(
                            f"Expected dict at '{part}', got {type(current).__name__}"
                        )

                    if part not in current:
                        raise KeyError(f"Key '{part}' not found")

                    current = current[part]

            return current
        except KeyError:
            return default
