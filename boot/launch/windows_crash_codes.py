# boot/launch/windows_crash_codes.py
from typing import Dict

WIN_CRASH_CODES: Dict[int, str] = {
    -1073741819: "Access Violation (0xC0000005)",
    -1073740791: "Stack Buffer Overrun (0xC0000409)",
    -1073741676: "Illegal Instruction (0xC000001D)",
    -1073741502: "Noncontinuable Exception (0xC0000025)",
    -1073740940: "Heap Corruption (0xC000010C)",
    -1073741571: "Invalid Handle (0xC0000008)",
    -1073741727: "Privileged Instruction (0xC0000096)",
}


def explain_returncode(code: int) -> str:
    if code >= 0:
        return f"Process exited with code {code}"

    if code in WIN_CRASH_CODES:
        return WIN_CRASH_CODES[code]

    # 尝试转为 NTSTATUS
    try:
        hex_code = f"{code & 0xFFFFFFFF:08X}"
        return f"Unknown Windows Exception (0x{hex_code})"
    except Exception:
        return f"Unknown return code: {code}"
