from __future__ import annotations
from core.utils.logger import logging
import typing
import threading

from core.app import APP

class Task:

    MIN: int = -1
    NORMAL: int = 0
    MAJOR: int = 1
    APP_MAIN: int = 2

    def __init__(self, task_name: str, executable: typing.Callable, task_type: int = 0, task_logger : logging.Logger | None = None) -> None:
        self.LOGGER = logging.getLogger(task_name) if task_logger is None else task_logger
        self.task_type = task_type
        self.executable = executable
        self.thread = threading.Thread(target = __static_exec__, name = task_name, args = [self])
    
    def execute(self):
        self.thread.start()

    def force_stop(self):
        self.thread._stop() #type: ignore

def __static_exec__(task: Task) -> int:
    if Task.MIN < task.task_type <= Task.MAJOR:
        task.LOGGER.info(f"executing a {'major' if task.task_type == Task.MAJOR else ''} task[{task.thread.name}]")
    elif task.task_type == Task.APP_MAIN:
        task.LOGGER.info(f"Starting {APP.name} APP.")
    task.executable()
    if Task.MIN < task.task_type <= Task.MAJOR:
        task.LOGGER.info(f"{'major' if task.task_type == Task.MAJOR else ''} task[{task.thread.name}] finished.")
    return 0