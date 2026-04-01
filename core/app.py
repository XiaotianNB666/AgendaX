import sys
from typing import NoReturn, Callable, Optional

from core.server.server import AgendaXServer
from core.utils.app_thread import Task
from core.utils.logger import logging


def version() -> str:
    return ''


class APP:
    name: str = "AgendaX"


LOG_LEVEL: int = logging.DEBUG if '--debug' in sys.argv else logging.INFO
LOG: logging.Logger = logging.getLogger(APP.name)

def init_app() -> None:
    logging.configure(LOG_LEVEL)


IS_BUILTIN = False
SERVER: Optional[AgendaXServer] = None  # True -> running
STOP_TASKS: list[Callable] = []


def set_server(server: AgendaXServer) -> None:
    global SERVER
    SERVER = server


def get_server() -> Optional[AgendaXServer]:
    return SERVER


def set_builtin(b: bool) -> None:
    global IS_BUILTIN
    IS_BUILTIN = b


def get_builtin() -> bool:
    return IS_BUILTIN


def app_force_stop(status) -> NoReturn:
    for STOP_TASK in STOP_TASKS:
        STOP_TASK()
    exit(status)


def register_force_stop(t: Callable | Task) -> None:
    global STOP_TASKS
    if isinstance(t, Task):
        STOP_TASKS.append(t.stop)
    elif isinstance(t, Callable):
        STOP_TASKS.append(t)
