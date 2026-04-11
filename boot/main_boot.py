from boot.boot_core import main as maincore
from core.app import APP, get_server
from core.crash_report import crash_handler, CrashReport
from core.utils.app_thread import Task
from ui.construct.crash_ui import CrashUI, show_window


def on_crash(report: CrashReport):
    crash_ui = CrashUI(report)
    show_window(crash_ui)


def on_crash(report: CrashReport):
    crash_ui = CrashUI(report)
    show_window(crash_ui)

# ui
@crash_handler(f"{APP.name}-ui", on_crash)
def ui_main() -> int:
    from ui.main import main
    result = main()
    sv = get_server()
    if sv:
        sv.shutdown()
    return result


server: Task = Task(f'{APP.name}-server', lambda: maincore(True), task_type=Task.APP_MAIN)
ui: Task = Task(f'{APP.name}-ui', ui_main, task_type=Task.APP_MAIN)


def main():
    ui.execute()
    server.execute_in_this_thread()
