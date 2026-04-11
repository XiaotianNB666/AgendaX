import threading
import time
from pprint import pformat
import traceback
from typing import Any, Callable, Optional
from core.app import APP, app_force_stop
from core.utils.logger import logging

from core.i18n import t, haveKey

CRASH_LOG = logging.getLogger("crash-report")
MAJOR_EXCEPTIONS: list[tuple[Exception, time.struct_time]] = []


class SimpleVarMonitor:
    def __init__(self):
        self._vars: dict[str, dict] = {}
        self._lock = threading.Lock()

    def watch(self, name: str, initial_value: Any,
              on_change: Optional[Callable] = None):
        """
        监视一个变量

        Args:
            name: 变量名
            initial_value: 初始值
            on_change: 变化时回调 (name, old, new) -> None
        """
        with self._lock:
            self._vars[name] = {
                'current': initial_value,
                'previous': initial_value,  # 上一次的值
                'on_change': on_change
            }
        return self

    def update(self, name: str, new_value: Any):
        """
        更新变量值（必须显式调用）
        """
        with self._lock:
            if name not in self._vars:
                raise KeyError(f"Variable '{name}' not being watched")

            var_info = self._vars[name]
            old_value = var_info['current']

            # 只有值真的变化才记录
            if old_value != new_value:
                var_info['previous'] = old_value  # 保存上一次
                var_info['current'] = new_value  # 更新当前

                # 触发回调
                if var_info['on_change']:
                    var_info['on_change'](name, old_value, new_value)

    def get_state(self, name: str) -> dict:
        """获取变量的状态 {previous, current}"""
        with self._lock:
            if name not in self._vars:
                raise KeyError(f"Variable '{name}' not being watched")
            return {
                'previous': self._vars[name]['previous'],
                'current': self._vars[name]['current']
            }

    @property
    def vars(self):
        return self._vars


VAR_MONITOR = SimpleVarMonitor()


class CrashReport:
    exception: Exception
    report_string: str = ""

    report_title: str = ""

    crash_time: tuple[time.struct_time, int]

    def __init__(self, reason: str | None = None):
        self.crash_time = (time.localtime(), int(-time.timezone / 3600))
        self.reason = reason

    def set_exception(self, exception: Exception) -> None:
        self.exception = exception

    def generate(self) -> None:
        self.report_title = f"[{self.formated_time}] {t('crash.message')}"
        self.report_string = \
            f"""{self.report_title}:
\t[+]{t("crash.caused_by", reason=t("crash.unknown_reason") if self.reason is None else self.reason)}
{self.trace_string}{t("crash.traceback.var")}{self.var_monitor_string}
"""

    @property
    def string(self) -> str:
        if self.report_string == "":
            self.generate()

        return self.report_string

    @property
    def formated_time(self) -> str:
        return f"UTC{'+' if self.crash_time[1] > 0 else ''}{self.crash_time[1] if self.crash_time[1] != 0 else ''} {time.strftime('%Y-%m-%d %H:%M:%S', self.crash_time[0])}"

    @property
    def trace_string(self) -> str:
        def get_string_of(_e_struct: tuple[Exception, time.struct_time]) -> str:
            e = _e_struct[0]
            result_string = ""
            exception_lines_list = traceback.format_exception(type(e), e, e.__traceback__)
            error_name = e.__class__.__name__
            exception_lines_list.reverse()
            trace_stack_string = "".join([">" + s for s in exception_lines_list[1:-1]])
            if haveKey(f'crash.tips.{error_name}'):
                result_string += f'{t(f"crash.tips.{error_name}", e_name=error_name, msg=str(e))} ([{error_name}] {e})\n{trace_stack_string}'
            else:
                result_string += f"[{error_name}] {e}\n{trace_stack_string}"

            return result_string

        exceptions: list[tuple[Exception, time.struct_time]] = [(self.exception, self.crash_time[0])]
        me = MAJOR_EXCEPTIONS.copy()
        me.reverse()
        exceptions += me

        match (len(exceptions)):
            case 0:
                return t("crash.traceback.none")
            case 1:
                return f"{t('crash.traceback.caused_crash_exception', e=get_string_of(exceptions.pop(0)))}\n"
            case _:
                final_string = f"{t('crash.traceback.caused_crash_exception', e=get_string_of(exceptions.pop(0)))}\n"
                noticeable_exception = ""
                for i, e_struct in enumerate(exceptions):
                    noticeable_exception += \
                        f"""[{i}: {time.strftime('%Y-%m-%d %H:%M:%S', e_struct[1])}] {get_string_of(e_struct)}"""
                final_string += t('crash.traceback.noticeable_exception', exceptions_string=noticeable_exception)
                return final_string

    @property
    def var_monitor_string(self) -> str:
        if len(VAR_MONITOR.vars) == 0:
            return 'No var monitor.'
        return '-' * 10 + '\n' + '\n'.join(
            [f'{k}: {pformat(v.get('current'))} <- {pformat(v.get('previous'))}' for k, v in
             VAR_MONITOR.vars.items()]) + '\n' + '-' * 10


# noinspection PyMissingConstructor
class StaticCrashReport(CrashReport):
    def __init__(self, report_string, report_title, formated_time, trace_string, var_monitor_string):
        self.report_string = report_string
        self.report_title = report_title
        self._formated_time = formated_time
        self._trace_string = trace_string
        self._var_monitor_string = var_monitor_string

    @property
    def var_monitor_string(self) -> str:
        return self._var_monitor_string

    @property
    def trace_string(self) -> str:
        return self._trace_string

    @property
    def formated_time(self) -> str:
        return self._formated_time

    @property
    def string(self) -> str:
        return self.report_string

    def set_exception(self, exception: Exception) -> None:
        raise AssertionError("StaticCrashReport does not support set_exception")

    def generate(self) -> None:
        raise AssertionError("StaticCrashReport does not support generate")


def crash_handler(name: Optional[str] = None, handler: Optional[Callable[[CrashReport], Any]] = None):
    def decorator(original_function):
        def wrapper(*args, **kwargs):
            result = None
            try:
                result = original_function(*args, **kwargs)
            except Exception as e:
                import sys
                cr = CrashReport(reason=t("crash.uncaught_exception"))
                cr.set_exception(e)
                CRASH_LOG.critical(f'{APP.name} crashed{"" if name is None else f" at {name}"}!!!\n{cr.string}')
                if handler:
                    handler(cr)
                app_force_stop(1)
            return result

        return wrapper

    return decorator


def register_exception(e: Exception) -> None:
    global MAJOR_EXCEPTIONS
    MAJOR_EXCEPTIONS.append((e, time.localtime()))
