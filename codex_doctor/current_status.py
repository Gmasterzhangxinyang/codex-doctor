from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .app_monitor import AppActivity, AppEventSummary, diagnose_app_activity, latest_app_activity
from .network_probe import run_probe
from .report import _event_from_row, _probe_from_row
from .schemas import Confidence, Diagnosis, NetworkProbe
from .state_machine import CodexState, diagnose
from .storage import Storage


@dataclass(frozen=True)
class CurrentStatus:
    diagnosis: Diagnosis
    source: str
    session_id: str
    app_activity: AppActivity | None = None
    app_events: list[AppEventSummary] | None = None
    project_path: Path | None = None
    network_probe: NetworkProbe | None = None
    storage_error: str | None = None


def diagnose_current(
    *,
    include_network: bool = True,
    stale_seconds: int = 45,
    network_timeout: int = 5,
    probe_when_active: bool = False,
) -> CurrentStatus:
    storage = _safe_storage()
    app_activity = _safe_latest_app_activity()
    doctor_status = _doctor_status(storage)

    if app_activity:
        status = _status_from_app_activity(app_activity, stale_seconds=stale_seconds)
    elif doctor_status:
        status = doctor_status
    else:
        status = CurrentStatus(
            diagnosis=Diagnosis(
                state=CodexState.IDLE.value,
                confidence=Confidence.LOW,
                title="No current Codex activity found.",
                explanation=(
                    "Codex Doctor did not find a recent Codex App rollout or hook/wrapper session."
                ),
            ),
            source="none",
            session_id="latest",
        )

    if include_network and (probe_when_active or _needs_network_probe(status, stale_seconds)):
        probe = run_probe(timeout=network_timeout)
        if storage:
            try:
                storage.insert_probe(probe)
            except Exception:
                pass
        status = _with_network_interpretation(status, probe, stale_seconds=stale_seconds)

    return status


def _safe_storage() -> Storage | None:
    try:
        return Storage()
    except Exception:
        return None


def _safe_latest_app_activity() -> AppActivity | None:
    try:
        return latest_app_activity()
    except Exception:
        return None


def _doctor_status(storage: Storage | None) -> CurrentStatus | None:
    if storage is None:
        return None
    try:
        selected = storage.get_latest_session()
        if not selected:
            return None
        session_id = selected["id"]
        rows = list(reversed(storage.list_recent_events(session_id=session_id, limit=100)))
        events = [_event_from_row(row) for row in rows]
        probe_row = storage.latest_probe(session_id=session_id)
        probe = _probe_from_row(probe_row) if probe_row else None
        process = storage.latest_process_sample(session_id=session_id)
        diagnosis = diagnose(events, probe=probe, process_sample=dict(process) if process else None)
        return CurrentStatus(
            diagnosis=diagnosis,
            source="Codex Doctor hooks/wrapper",
            session_id=session_id,
            network_probe=probe,
        )
    except Exception as exc:
        return CurrentStatus(
            diagnosis=Diagnosis(
                state=CodexState.IDLE.value,
                confidence=Confidence.LOW,
                title="Codex Doctor storage is temporarily unavailable.",
                explanation="The local Codex Doctor database could not be opened.",
                evidence={"error": str(exc)},
            ),
            source="Codex Doctor hooks/wrapper",
            session_id="latest",
            storage_error=str(exc),
        )


def _status_from_app_activity(
    activity: AppActivity,
    *,
    stale_seconds: int,
) -> CurrentStatus:
    diagnosis = diagnose_app_activity(activity)
    age = _age_seconds(activity.updated_at)
    if age >= stale_seconds:
        diagnosis = Diagnosis(
            session_id=activity.session_id,
            state=CodexState.CODEX_THINKING_NO_TOOL.value,
            confidence=Confidence.LOW,
            title="Codex App has not written a recent event.",
            explanation=(
                f"The latest Codex App rollout event is {age:.0f}s old. "
                "A network probe can help separate local network issues from API/model waiting."
            ),
            evidence={
                "source": "codex-app-rollout",
                "age_seconds": age,
                "last_event": activity.events[-1].label,
            },
        )
    return CurrentStatus(
        diagnosis=diagnosis,
        source="Codex App rollout fallback",
        session_id=activity.session_id,
        app_activity=activity,
        app_events=activity.events,
        project_path=activity.project_path,
    )


def _with_network_interpretation(
    status: CurrentStatus,
    probe: NetworkProbe,
    *,
    stale_seconds: int,
) -> CurrentStatus:
    diagnosis = status.diagnosis
    age = _status_age(status)
    if age is not None and age >= stale_seconds:
        if not probe.ok:
            diagnosis = Diagnosis(
                session_id=status.session_id,
                state=CodexState.NETWORK_SUSPECTED.value,
                confidence=Confidence.MEDIUM,
                title="Codex may be blocked by network or proxy.",
                explanation=(
                    f"No recent Codex activity for {age:.0f}s, and the OpenAI probe failed."
                ),
                evidence={"probe_error": probe.error_type, "age_seconds": age},
            )
        elif diagnosis.state in {
            CodexState.CODEX_THINKING_NO_TOOL.value,
            CodexState.DONE.value,
            CodexState.IDLE.value,
        }:
            diagnosis = Diagnosis(
                session_id=status.session_id,
                state=CodexState.API_OR_MODEL_WAITING.value,
                confidence=Confidence.MEDIUM,
                title="Network is reachable; Codex is likely waiting on API/model or reconnect.",
                explanation=(
                    f"No recent Codex activity for {age:.0f}s, but api.openai.com is reachable."
                ),
                evidence={"http_code": probe.http_code, "age_seconds": age},
            )
    return CurrentStatus(
        diagnosis=diagnosis,
        source=status.source,
        session_id=status.session_id,
        app_activity=status.app_activity,
        app_events=status.app_events,
        project_path=status.project_path,
        network_probe=probe,
        storage_error=status.storage_error,
    )


def _needs_network_probe(status: CurrentStatus, stale_seconds: int) -> bool:
    age = _status_age(status)
    if age is not None and age >= stale_seconds:
        return True
    return status.diagnosis.state in {
        CodexState.CODEX_THINKING_NO_TOOL.value,
        CodexState.NETWORK_SUSPECTED.value,
        CodexState.API_OR_MODEL_WAITING.value,
        CodexState.IDLE.value,
    }


def _status_age(status: CurrentStatus) -> float | None:
    if status.app_activity:
        return _age_seconds(status.app_activity.updated_at)
    age = status.diagnosis.evidence.get("elapsed_seconds") or status.diagnosis.evidence.get(
        "age_seconds"
    )
    return float(age) if isinstance(age, int | float) else None


def _age_seconds(ts: datetime) -> float:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - ts).total_seconds())
