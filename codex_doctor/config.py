from __future__ import annotations

import os
from pathlib import Path

from .constants import APP_NAME


def user_data_dir() -> Path:
    override = os.environ.get("CODEX_DOCTOR_DATA_DIR")
    if override:
        return Path(override).expanduser()
    try:
        from platformdirs import user_data_path

        return user_data_path(APP_NAME)
    except Exception:
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            return base / APP_NAME
        if os.uname().sysname == "Darwin":
            return Path.home() / "Library" / "Application Support" / APP_NAME
        return Path.home() / ".local" / "share" / APP_NAME


def db_path() -> Path:
    return user_data_dir() / "codex-doctor.db"


def jsonl_path() -> Path:
    return user_data_dir() / "events.jsonl"


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def hooks_path(scope: str = "user", project_dir: Path | None = None) -> Path:
    if scope == "project":
        return (project_dir or Path.cwd()) / ".codex" / "hooks.json"
    return codex_home() / "hooks.json"
