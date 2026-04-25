# boot/launch/crash_writer.py
import time
import hashlib
from pathlib import Path

from boot.launch.windows_crash_codes import explain_returncode

CRASH_DIR = Path("./crashes")
CRASH_DIR.mkdir(exist_ok=True)


def write_crash_file(stdout: str, stderr: str, args: list[str], returncode: int) -> Path:
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    digest = hashlib.md5(stderr.encode("utf-8")).hexdigest()[:6]

    crash_path = CRASH_DIR / f"crash_{timestamp}_{digest}.crash"

    reason = explain_returncode(returncode)

    content = f"""
[meta]
timestamp = "{time.strftime('%Y-%m-%d %H:%M:%S')}"
return_code = {returncode}
reason = "{reason}"
args = {args}

[stdout]
{stdout}

[stderr]
{stderr}
""".strip()

    crash_path.write_text(content, encoding="utf-8")
    return crash_path
