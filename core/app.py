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
    return '1.0.0'


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

# 原先直接在默认 STOP_TASKS 中触发 ExitEvent，可能在非 UI 线程导致 Qt 本地层异常（0xC0000005）
def _default_stop_fire_exit():
    """
    尝试将 fire_event(ExitEvent()) 安排到 UI 线程执行（若 QApplication 可用），
    否则直接调用 fire_event。任何异常都会被捕获并记录为 debug。
    """
    try:
        # 尽量通过 Qt 的单次定时器在 UI 线程触发 ExitEvent，避免跨线程直接调用导致的本地层崩溃
        from PyQt5.QtWidgets import QApplication  # type: ignore
        from PyQt5.QtCore import QTimer  # type: ignore
        app = QApplication.instance()
        if app:
            try:
                QTimer.singleShot(0, lambda: fire_event(ExitEvent()))
                return
            except Exception:
                # 如果无法通过 QTimer 安排，回退到直接触发
                pass
    except Exception:
        # Qt 不可用或导入失败，直接触发
        pass
    try:
        fire_event(ExitEvent())
    except Exception as e:
        LOG.debug(f"Failed to fire ExitEvent in default stop task: {e}", exc_info=True)


# STOP_TASKS 中有可能包含 UI 操作，禁止直接在任意线程调用它们
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
    """
    若存在 QApplication 实例，则在 UI 线程通过 QTimer.singleShot 执行 STOP_TASKS，
    否则在当前线程尝试安全调用（受保护，避免未捕获的 Qt C++ 对象错误）。
    """
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
    """
    对绑定方法做弱引用包装：
    - 使用 weakref 保存实例引用，避免延长对象生命周期
    - 调用前检查实例是否存在且（若 sip 可用）未被 C++ 层删除
    - 若对象已被回收/删除，则跳过调用
    - 对于调用过程中出现的 RuntimeError（常见于 Qt 对象已被删除），以 debug 记录并静默跳过
    """
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
                # sip 检测失败则继续尝试调用（保护在外层）
                pass
        try:
            return func(o, *args, **kwargs)
        except RuntimeError as e:
            # Qt 对象在 C++ 层已被删除，静默跳过并以 debug 记录，避免误判为严重错误
            LOG.debug(f"RuntimeError while running wrapped STOP_TASK {bound_method}: {e}", exc_info=True)
            return
        except Exception as e:
            LOG.error(f"Exception while running wrapped STOP_TASK {bound_method}: {e}", exc_info=True)

    return wrapper


def register_stop(t: Callable | Task) -> None:
    """
    注册停止回调。
    若传入的是 Task，注册其 stop 方法；若是绑定方法（Qt 对象方法），包装后注册以避免在对象已删除时调用。
    """
    global STOP_TASKS
    if isinstance(t, Task):
        STOP_TASKS.append(t.stop)
    elif callable(t):
        # 如果是绑定方法（如 MainWindow.force_stop），用包装器保护
        wrapped = _wrap_bound_method_safe(t)
        STOP_TASKS.append(wrapped)
