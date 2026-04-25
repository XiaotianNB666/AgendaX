# boot/launcher.py
import subprocess
import sys
import os

from core.utils.logger import logging
from boot.launch.crash_writer import write_crash_file
from boot.launch.crash_ui import show_crash_ui
from boot.launch.windows_crash_codes import explain_returncode

LAUNCHER_LOG = logging.getLogger("launcher")


def launch_agendax(exe_path: str, args: list[str]):
    exe_path = os.path.abspath(exe_path)

    if not os.path.exists(exe_path):
        raise FileNotFoundError(exe_path)

    LAUNCHER_LOG.info(f"Launching: {exe_path} {' '.join(args)}")

    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE

    proc = subprocess.Popen(
        [exe_path] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        startupinfo=si
    )

    stdout, stderr = proc.communicate()
    rc = proc.returncode

    if rc != 0:
        reason = explain_returncode(rc)
        LAUNCHER_LOG.critical(
            f"AgendaX crashed with return code {rc} ({reason})"
        )

        crash_file = write_crash_file(stdout, stderr, args, rc)
        LAUNCHER_LOG.critical(f"Crash file: {crash_file}")

        show_crash_ui(crash_file)

    else:
        LAUNCHER_LOG.info("AgendaX exited normally.")

def main():
    exe_path = os.path.join('.', 'AgendaX.exe')
    launch_agendax(str(exe_path), ['--no-main-window'] + sys.argv[1:])
