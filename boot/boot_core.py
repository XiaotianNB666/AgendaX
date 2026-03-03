import atexit

from core.app import LOG, APP, get_server_status, set_builtin, get_builtin
from core.bases.resource_release import RESOURCE_RELEASE
from core.crash_report import crash_handler, VAR_MONITOR
from core.data_swap import set_current_server, CURRENT_SERVER
from core.server.servers import BuiltinServer, get_builtin_server_address
from core.server.server import server_repl
from platforms.windows.winutils import WSL, registerShutdown

assert __name__ != "__main__", "This cannot be executed directly."


def init():
    atexit.register(clean)
    registerShutdown(clean)
    VAR_MONITOR.watch('boot_main@RESOURCE_RELEASE', RESOURCE_RELEASE)

    if get_builtin():
        set_current_server(BuiltinServer(get_builtin_server_address()))

    VAR_MONITOR.watch("server", CURRENT_SERVER)


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
    server_repl()
    while get_server_status() and get_builtin():
        WSL.peek()
    return 0
