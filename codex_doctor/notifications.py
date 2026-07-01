from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationResult:
    ok: bool
    error: str | None = None


def notify(title: str, message: str) -> bool:
    return send_notification(title, message).ok


def send_notification(title: str, message: str) -> NotificationResult:
    if platform.system() != "Darwin":
        return NotificationResult(ok=False, error="macOS notifications are only supported on Darwin.")
    script = (
        f"display notification {_applescript_string(message)} "
        f"with title {_applescript_string(title)}"
    )
    try:
        completed = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as exc:
        return NotificationResult(ok=False, error=str(exc))
    if completed.returncode != 0:
        return NotificationResult(ok=False, error=(completed.stderr or completed.stdout).strip())
    return NotificationResult(ok=True)


def _applescript_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
