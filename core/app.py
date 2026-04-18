import sys
import weakref
from typing import NoReturn, Callable, Optional, Any, TypeVar

from core.events import fire_event, ExitEvent
from core.server.server import AgendaXServer
from core.utils.app_thread import Task
from core.utils.logger import logging

try:
    import sip  # type: ignore

    _HAVE_SIP = True
except Exception:
    sip = None
    _HAVE_SIP = False


def version() -> str:
    return '1.0.2'


class APP:
    name: str = "AgendaX"


LOG_LEVEL: int = logging.DEBUG if '--debug' in sys.argv else logging.INFO
if '--debug' in sys.argv:
    import os

    os.environ["QT_LOGGING_RULES"] = "*.debug=true"
LOG: logging.Logger = logging.getLogger(APP.name)


def init_app() -> None:
    logging.configure(LOG_LEVEL)


IS_BUILTIN = False
SERVER: Optional[AgendaXServer] = None
APP_PROPERTIES: dict[str, Any] = {}


def _default_stop_fire_exit():
    """
    尝试将 fire_event(ExitEvent()) 安排到 UI 线程执行（若 QApplication 可用），
    否则直接调用 fire_event。任何异常都会被捕获并记录为 debug。
    """
    try:
        from PyQt5.QtWidgets import QApplication  # type: ignore
        from PyQt5.QtCore import QTimer  # type: ignore
        app = QApplication.instance()
        if app:
            try:
                QTimer.singleShot(0, lambda: fire_event(ExitEvent()))
                return
            except Exception:
                pass
    except Exception:
        pass
    try:
        fire_event(ExitEvent())
    except Exception as e:
        LOG.debug(f"Failed to fire ExitEvent in default stop task: {e}", exc_info=True)


STOP_TASKS: list[Callable] = [_default_stop_fire_exit]


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


_T = TypeVar('_T')


def get_property(key: str, default: _T = None, _type: type[_T] = Any) -> _T:
    return APP_PROPERTIES.get(key, default)


def set_property(key: str, value: _T, _type: type[_T] = Any) -> None:
    APP_PROPERTIES[key] = value


def _safe_call_stop_task(stop_task: Callable) -> None:
    try:
        stop_task()
    except RuntimeError as e:
        LOG.debug(f"RuntimeError when running STOP_TASK {stop_task}: {e}", exc_info=True)
    except Exception as e:
        LOG.error(f"Exception when running STOP_TASK {stop_task}: {e}", exc_info=True)


def app_quit():
    try:
        from PyQt5.QtWidgets import QApplication  # type: ignore
        from PyQt5.QtCore import QTimer  # type: ignore
        app = QApplication.instance()
        if app:
            for STOP_TASK in STOP_TASKS:
                try:
                    QTimer.singleShot(0, STOP_TASK)
                except Exception as e:
                    LOG.error(f"Failed to schedule STOP_TASK via QTimer.singleShot: {STOP_TASK}, error: {e}",
                              exc_info=True)
            return
    except Exception as e:
        LOG.debug(f"Unable to schedule STOP_TASK via Qt (import/instance failed): {e}", exc_info=True)

    for STOP_TASK in STOP_TASKS:
        _safe_call_stop_task(STOP_TASK)


def app_force_stop(status) -> NoReturn:
    # 强制退出之前尝试触发安全的停止流程
    try:
        app_quit()
    except Exception as e:
        LOG.error(f"Exception in app_quit during force stop: {e}", exc_info=True)
    finally:
        sys.exit(status)


def _wrap_bound_method_safe(bound_method: Callable) -> Callable:
    try:
        obj = getattr(bound_method, "__self__", None)
        func = getattr(bound_method, "__func__", None)
    except Exception:
        # 不是标准绑定方法，返回原始可调用
        return bound_method

    if obj is None or func is None:
        return bound_method

    obj_ref = weakref.ref(obj)

    def wrapper(*args, **kwargs):
        o = obj_ref()
        if o is None:
            LOG.debug(f"Skip STOP_TASK: target object already garbage-collected: {bound_method}")
            return
        if _HAVE_SIP:
            try:
                if sip.isdeleted(o):  # type: ignore
                    LOG.debug(f"Skip STOP_TASK: sip reports object deleted: {bound_method}")
                    return
            except Exception:
                pass
        try:
            return func(o, *args, **kwargs)
        except RuntimeError as e:
            LOG.debug(f"RuntimeError while running wrapped STOP_TASK {bound_method}: {e}", exc_info=True)
            return
        except Exception as e:
            LOG.error(f"Exception while running wrapped STOP_TASK {bound_method}: {e}", exc_info=True)

    return wrapper


def register_stop(t: Callable | Task) -> None:
    global STOP_TASKS
    if isinstance(t, Task):
        STOP_TASKS.append(t.stop)
    elif callable(t):
        wrapped = _wrap_bound_method_safe(t)
        STOP_TASKS.append(wrapped)
