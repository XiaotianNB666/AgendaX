from core.app import APP
from boot.boot_core import main as maincore
from core.utils.app_thread import Task

server: Task = Task(f'{APP.name}-server', lambda: maincore(True), task_type=Task.APP_MAIN)


def main():
    server.execute()
