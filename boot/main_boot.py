from core.crash_report import crash_handler
from boot.boot_core import main as maincore
from core.app import APP, set_server_status
from core.utils.app_thread import Task


# ui
@crash_handler(f"{APP.name}-ui")
def ui_main() -> int:
    from ui.main import main
    result = main()
    set_server_status(False)
    return result


server: Task = Task(f'{APP.name}-server', lambda: maincore(True), task_type=Task.APP_MAIN)
ui: Task = Task(f'{APP.name}-ui', ui_main, task_type=Task.APP_MAIN)


def main():
    server.execute()
    ui.execute()
