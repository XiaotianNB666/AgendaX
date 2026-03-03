import win32con
import win32api
import win32gui
from typing import Callable

from core.app import LOG


class WindowsShutdownListener:
    SHUTDOWN_ACTIONS: list[Callable] = []

    """精简版Windows关机/注销监听器"""

    def __init__(self, callback=None):
        self.hwnd = None
        self.callback = callback or self.on_shutdown

    def on_shutdown(self):
        for func in self.SHUTDOWN_ACTIONS:
            func()

    def _msg_handler(self, hwnd, msg, wparam, lparam):
        """消息处理核心函数"""
        if msg == win32con.WM_QUERYENDSESSION:
            self.callback()
            return False
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def start(self):
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._msg_handler  # type: ignore
        wc.lpszClassName = "SimpleShutdownListener"  # type: ignore
        wc.hInstance = win32api.GetModuleHandle()  # type: ignore
        win32gui.RegisterClass(wc)

        self.hwnd = win32gui.CreateWindow(wc.lpszClassName, "", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None)
        if not self.hwnd:
            LOG.error('cannot init win shutdown listener!')
            return False

    def peek(self):
        win32gui.PumpWaitingMessages()

    def append(self, func: Callable):
        self.SHUTDOWN_ACTIONS.append(func)


WSL = WindowsShutdownListener()
WSL.start()


def registerShutdown(func: Callable):
    WSL.append(func)
