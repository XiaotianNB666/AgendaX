import os
import sys
from functools import cache


@cache
def get_base_dir() ->  str:
    if getattr(sys, 'frozen', False):
        # pyinstaller 打包兼容
        return sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)  # type: ignore
    else:
        # dev env
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))