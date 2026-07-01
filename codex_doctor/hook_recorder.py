from __future__ import annotations

import json
import os
import sys
from typing import Any

from .redaction import redact, snippet, stable_hash
from .schemas import Event, Session
from .storage import Storage


def normalize_hook_payload(payload: dict[str, Any]) -> Event:
    event_type = (
        payload.get("hook_event_name")
        or payload.get("event")
        or payload.get("event_type")
        or payload.get("type")
        or "UnknownHook"
    )
    tool_input = payload.get("tool_input") or payload.get("input") or payload.get("toolInput")
    redacted = redact(payload)
    return Event(
        source="hook",
        session_id=payload.get("session_id") or os.environ.get("CODEX_DOCTOR_SESSION"),
        turn_id=payload.get("turn_id") or payload.get("turnId"),
        event_type=str(event_type),
        cwd=payload.get("cwd") or payload.get("workspace") or os.getcwd(),
        model=payload.get("model"),
        permission_mode=payload.get("permission_mode") or payload.get("permissionMode"),
        tool_name=payload.get("tool_name") or payload.get("tool") or payload.get("toolName"),
        tool_input_hash=stable_hash(tool_input) if tool_input is not None else None,
        tool_input_snippet=snippet(tool_input, 500) if tool_input is not None else None,
        success=payload.get("success"),
        duration_ms=payload.get("duration_ms") or payload.get("durationMs"),
        raw_redacted=redacted if isinstance(redacted, dict) else {"payload": redacted},
    )


def record_payload(payload: dict[str, Any], storage: Storage | None = None) -> Event:
    storage = storage or Storage()
    event = normalize_hook_payload(payload)
    if event.session_id:
        storage.create_session(Session(id=event.session_id, cwd=event.cwd, model=event.model))
    storage.insert_event(event)
    return event


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if isinstance(payload, dict):
            record_payload(payload)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
