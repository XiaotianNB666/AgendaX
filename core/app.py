import sys

from core.utils.logger import logging

class APP:

    name: str = "AgendaX"

    @property
    def version(self = None) -> str:
        return ''
    

LOG_LEVEL: int = logging.DEBUG if '--debug' in sys.argv else logging.INFO
LOG: logging.Logger = logging.getLogger(APP.name)

logging.configure(LOG_LEVEL)

IS_BUILTIN = False
SERVER_STATUS = True # True -> running

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
