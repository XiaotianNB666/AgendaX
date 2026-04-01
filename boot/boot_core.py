import atexit
import threading

from core.app import LOG, APP, get_server, set_server, set_builtin, get_builtin, init_app
from core.bases.resource_release import RESOURCE_RELEASE
from core.crash_report import crash_handler, VAR_MONITOR
from core.server.server import AgendaXServer
from platforms.windows.winutils import registerShutdown

assert __name__ != "__main__", "This cannot be executed directly."


def init():
    init_app()
    atexit.register(clean)
    registerShutdown(clean)
    VAR_MONITOR.watch('boot_main@RESOURCE_RELEASE', RESOURCE_RELEASE)


def clean():
    LOG.info("Stopping...")
    for releasable in RESOURCE_RELEASE:
        releasable.release_resource()


# server
@crash_handler(f"{APP.name}-server")
def main(is_builtin: bool) -> int:
    set_builtin(is_builtin)
    VAR_MONITOR.watch('boot_main.main@is_builtin', is_builtin)
    init()

    server = AgendaXServer()
    set_server(server)
    server.start()

    return 0
