from __future__ import annotations

import os
import shutil
from pathlib import Path

MACOS_APP_CODEX_PATHS = [
    Path("/Applications/Codex.app/Contents/Resources/codex"),
    Path.home() / "Applications" / "Codex.app" / "Contents" / "Resources" / "codex",
]


def find_codex_executable() -> str | None:
    override = os.environ.get("CODEX_DOCTOR_CODEX_PATH")
    if override:
        path = Path(override).expanduser()
        if _is_executable(path):
            return str(path)

    path_from_shell = shutil.which("codex")
    if path_from_shell:
        return path_from_shell

    for path in MACOS_APP_CODEX_PATHS:
        if _is_executable(path):
            return str(path)
    return None


def _is_executable(path: Path) -> bool:
    return path.exists() and path.is_file() and os.access(path, os.X_OK)
