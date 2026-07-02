from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

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


def fallback_data_dir() -> Path:
    return Path(tempfile.gettempdir()) / APP_NAME


def ensure_user_data_dir() -> Path:
    path = user_data_dir()
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return path
    except OSError:
        fallback = fallback_data_dir()
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def db_path() -> Path:
    return user_data_dir() / "codex-doctor.db"


def jsonl_path() -> Path:
    return user_data_dir() / "events.jsonl"


def settings_path() -> Path:
    return user_data_dir() / "settings.json"


def load_settings() -> dict[str, Any]:
    path = settings_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(settings: dict[str, Any]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    current = load_settings()
    current.update(settings)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def hooks_path(scope: str = "user", project_dir: Path | None = None) -> Path:
    if scope == "project":
        return (project_dir or Path.cwd()) / ".codex" / "hooks.json"
    return codex_home() / "hooks.json"
