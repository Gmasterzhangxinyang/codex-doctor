from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import Confidence, Diagnosis
from .state_machine import CodexState

TAIL_BYTES = 256 * 1024
UUID_AT_END_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$"
)


@dataclass(frozen=True)
class AppEventSummary:
    ts: datetime
    outer_type: str
    payload_type: str | None = None
    name: str | None = None
    status: str | None = None
    call_id: str | None = None

    @property
    def label(self) -> str:
        parts = [self.payload_type or self.outer_type]
        if self.name:
            parts.append(self.name)
        if self.status:
            parts.append(self.status)
        return " ".join(parts)


@dataclass(frozen=True)
class AppActivity:
    session_id: str
    path: Path
    updated_at: datetime
    events: list[AppEventSummary]
    project_path: Path | None = None


def latest_app_activity(codex_home: Path | None = None) -> AppActivity | None:
    home = codex_home or Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    sessions_dir = home / "sessions"
    if not sessions_dir.exists():
        return None

    files = [path for path in sessions_dir.rglob("*.jsonl") if path.is_file()]
    if not files:
        return None

    latest = max(files, key=lambda path: path.stat().st_mtime)
    events = read_app_events(latest)
    if not events:
        return None

    return AppActivity(
        session_id=_session_id_from_path(latest),
        path=latest,
        updated_at=events[-1].ts,
        events=events,
        project_path=read_app_project_path(latest),
    )


def diagnose_app_activity(activity: AppActivity, now: datetime | None = None) -> Diagnosis:
    now = now or datetime.now(timezone.utc)
    latest = activity.events[-1]
    age = max(0.0, (now - latest.ts).total_seconds())
    open_call = _open_function_call(activity.events)

    if open_call:
        return Diagnosis(
            session_id=activity.session_id,
            state=CodexState.TOOL_RUNNING.value,
            confidence=Confidence.MEDIUM,
            title="Codex App appears to be running a tool.",
            explanation=(
                "Codex App's local rollout log has a function_call without a later "
                "function_call_output. This is best-effort App monitoring."
            ),
            evidence={"source": "codex-app-rollout", "age_seconds": age, "tool": open_call.name},
        )

    if latest.payload_type in {"reasoning", "web_search_call", "web_search_end"} and age < 120:
        return Diagnosis(
            session_id=activity.session_id,
            state=CodexState.MODEL_STREAMING.value,
            confidence=Confidence.MEDIUM,
            title="Codex App activity is visible.",
            explanation=(
                "Codex App is writing reasoning/search events to its local rollout log. "
                "Hooks did not fire for this App session, so this is a fallback signal."
            ),
            evidence={"source": "codex-app-rollout", "last_event": latest.label, "age_seconds": age},
        )

    if age < 120:
        return Diagnosis(
            session_id=activity.session_id,
            state=CodexState.MODEL_STREAMING.value,
            confidence=Confidence.LOW,
            title="Codex App recently wrote local session events.",
            explanation=(
                "Codex App's rollout log changed recently, but Codex Doctor did not receive hooks "
                "for this session."
            ),
            evidence={"source": "codex-app-rollout", "last_event": latest.label, "age_seconds": age},
        )

    return Diagnosis(
        session_id=activity.session_id,
        state=CodexState.DONE.value,
        confidence=Confidence.LOW,
        title="No recent Codex App rollout activity.",
        explanation=(
            "Codex Doctor can see the latest Codex App rollout file, but it has not changed "
            f"for {age:.0f}s."
        ),
        evidence={"source": "codex-app-rollout", "last_event": latest.label, "age_seconds": age},
    )


def read_app_events(path: Path) -> list[AppEventSummary]:
    events: list[AppEventSummary] = []
    for line in _tail_lines(path):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        event = _summarize_row(row)
        if event:
            events.append(event)
    events.sort(key=lambda event: event.ts)
    return events[-40:]


def read_app_project_path(path: Path) -> Path | None:
    for line in reversed(_tail_lines(path)):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = row.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        raw_path = (
            _safe_str(payload.get("cwd"))
            or _workspace_root(payload.get("workspace_roots"))
            or _safe_str(row.get("cwd"))
        )
        if raw_path:
            return Path(raw_path).expanduser()
    return None


def _summarize_row(row: dict[str, Any]) -> AppEventSummary | None:
    ts_raw = row.get("timestamp")
    if not isinstance(ts_raw, str):
        return None
    ts = _parse_ts(ts_raw)
    raw_payload = row.get("payload")
    payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}
    return AppEventSummary(
        ts=ts,
        outer_type=str(row.get("type") or "unknown"),
        payload_type=_safe_str(payload.get("type")),
        name=_safe_str(payload.get("name")),
        status=_safe_str(payload.get("status")),
        call_id=_safe_str(payload.get("call_id")),
    )


def _open_function_call(events: list[AppEventSummary]) -> AppEventSummary | None:
    open_calls: dict[str, AppEventSummary] = {}
    fallback: AppEventSummary | None = None
    for event in events:
        if event.payload_type == "function_call":
            fallback = event
            if event.call_id:
                open_calls[event.call_id] = event
        elif event.payload_type == "function_call_output" and event.call_id:
            open_calls.pop(event.call_id, None)
            fallback = None
    if open_calls:
        return list(open_calls.values())[-1]
    return fallback


def _tail_lines(path: Path) -> list[str]:
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > TAIL_BYTES:
            handle.seek(size - TAIL_BYTES)
            handle.readline()
        data = handle.read()
    return data.decode("utf-8", errors="ignore").splitlines()


def _parse_ts(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    ts = datetime.fromisoformat(value)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _safe_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _workspace_root(value: Any) -> str | None:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                return item
            if isinstance(item, dict):
                path = _safe_str(item.get("path")) or _safe_str(item.get("root"))
                if path:
                    return path
    return None


def _session_id_from_path(path: Path) -> str:
    stem = path.stem
    match = UUID_AT_END_RE.search(stem)
    if match:
        return match.group(1)
    return stem.removeprefix("rollout-")
