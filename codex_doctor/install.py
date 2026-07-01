from __future__ import annotations

import json
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import hooks_path, user_data_dir
from .constants import HOOK_COMMAND, MANAGED_MARKER

HOOK_EVENTS = [
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "Stop",
]


def managed_hook(status: str) -> dict[str, Any]:
    return {
        MANAGED_MARKER: True,
        "type": "command",
        "command": HOOK_COMMAND,
        "timeout": 5,
        "statusMessage": f"Codex Doctor: {status}",
    }


def desired_hooks() -> dict[str, Any]:
    status = {
        "SessionStart": "session started",
        "UserPromptSubmit": "prompt submitted",
        "PreToolUse": "tool starting",
        "PermissionRequest": "approval requested",
        "PostToolUse": "tool finished",
        "PreCompact": "compacting",
        "PostCompact": "compact finished",
        "Stop": "session stopped",
    }
    hooks: dict[str, Any] = {"hooks": {}}
    for name in HOOK_EVENTS:
        entry: dict[str, Any] = {"hooks": [managed_hook(status[name])]}
        if name in {"PreToolUse", "PermissionRequest", "PostToolUse"}:
            entry["matcher"] = "*"
        hooks["hooks"][name] = [entry]
    return hooks


def install_hooks(scope: str = "user", force: bool = False, project_dir: Path | None = None) -> Path:
    path = hooks_path(scope, project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = _read_json(path)
    if path.exists() and not force:
        backup = path.with_suffix(
            path.suffix + "." + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + ".bak"
        )
        shutil.copy2(path, backup)
    merged = merge_hooks(current, desired_hooks())
    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    user_data_dir().mkdir(parents=True, exist_ok=True)
    return path


def uninstall_hooks(
    scope: str = "user", project_dir: Path | None = None, purge_data: bool = False
) -> Path:
    path = hooks_path(scope, project_dir)
    current = _read_json(path)
    current["hooks"] = {
        event_name: [
            entry
            for entry in entries
            if not any(hook.get(MANAGED_MARKER) for hook in entry.get("hooks", []))
        ]
        for event_name, entries in current.get("hooks", {}).items()
    }
    current["hooks"] = {name: entries for name, entries in current["hooks"].items() if entries}
    if current["hooks"]:
        path.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    elif path.exists():
        path.unlink()
    if purge_data and user_data_dir().exists():
        shutil.rmtree(user_data_dir())
    return path


def merge_hooks(current: dict[str, Any], desired: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(current) if current else {"hooks": {}}
    merged.setdefault("hooks", {})
    for event_name, desired_entries in desired["hooks"].items():
        existing = merged["hooks"].setdefault(event_name, [])
        existing = [
            entry
            for entry in existing
            if not any(hook.get(MANAGED_MARKER) for hook in entry.get("hooks", []))
        ]
        existing.extend(desired_entries)
        merged["hooks"][event_name] = existing
    return merged


def hooks_installed(scope: str = "user", project_dir: Path | None = None) -> bool:
    data = _read_json(hooks_path(scope, project_dir))
    for entries in data.get("hooks", {}).values():
        for entry in entries:
            if any(hook.get(MANAGED_MARKER) for hook in entry.get("hooks", [])):
                return True
    return False


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"hooks": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"hooks": {}}
