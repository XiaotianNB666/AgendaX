import sys
from typing import NoReturn

from core.utils.app_thread import Task
from core.utils.logger import logging


class APP:
    name: str = "AgendaX"

    @property
    def version(self=None) -> str:
        return ''


LOG_LEVEL: int = logging.DEBUG if '--debug' in sys.argv else logging.INFO
LOG: logging.Logger = logging.getLogger(APP.name)

logging.configure(LOG_LEVEL)

IS_BUILTIN = False
SERVER_STATUS = True  # True -> running
STOP_TASKS: list[Task] = []


def set_server_status(status: bool) -> None:
    global SERVER_STATUS
    SERVER_STATUS = status


def get_server_status() -> bool:
    return SERVER_STATUS


def set_builtin(b: bool) -> None:
    global IS_BUILTIN
    IS_BUILTIN = b


def get_builtin() -> bool:
    return IS_BUILTIN


def app_force_stop(status) -> NoReturn:
    for STOP_TASK in STOP_TASKS:
        STOP_TASK.force_stop()
    exit(status)


def register_stop(t: Task) -> None:
    global STOP_TASKS
    if isinstance(t, Task):
        STOP_TASKS.append(t)
