from __future__ import annotations
from core.utils.logger import logging
import typing
import threading


class Task:
    MIN: int = -1
    NORMAL: int = 0
    MAJOR: int = 1
    APP_MAIN: int = 2

    def __init__(self, task_name: str, executable: typing.Callable, task_type: int = 0,
                 task_logger: logging.Logger | None = None) -> None:
        self.thread = None
        self.LOGGER = logging.getLogger(task_name) if task_logger is None else task_logger
        self.task_type = task_type
        self.executable = executable
        self.task_name = task_name

    def execute(self, is_join: bool = False, *args):
        self.thread = threading.Thread(target=__static_exec__, name=self.task_name, args=[self, *args])
        self.thread.start()
        if is_join:
            self.thread.join()

    def join(self):
        self.thread.join()

    def execute_in_this_thread(self, *args):
        self.executable(*args)

    def stop(self):  # subclass override it
        ...


def __static_exec__(task: Task, *args) -> int:
    from core.app import APP, register_force_stop
    if Task.MIN < task.task_type <= Task.MAJOR:
        task.LOGGER.info(f"executing a {'major' if task.task_type == Task.MAJOR else ''} task[{task.thread.name}]")
    elif task.task_type == Task.APP_MAIN:
        task.LOGGER.info(f"Starting {APP.name} APP.")
    register_force_stop(task)
    task.executable(*args)
    if Task.MIN < task.task_type <= Task.MAJOR:
        task.LOGGER.info(f"{'major' if task.task_type == Task.MAJOR else ''} task[{task.thread.name}] finished.")
    return 0
