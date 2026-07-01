from __future__ import annotations

import platform
import subprocess


def notify(title: str, message: str) -> bool:
    if platform.system() != "Darwin":
        return False
    script = (
        f"display notification {_applescript_string(message)} "
        f"with title {_applescript_string(title)}"
    )
    try:
        subprocess.run(["osascript", "-e", script], check=False, timeout=5)
    except Exception:
        return False
    return True


def _applescript_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
