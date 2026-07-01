from datetime import datetime, timedelta, timezone

from codex_doctor import current_status
from codex_doctor.app_monitor import AppActivity, AppEventSummary
from codex_doctor.schemas import NetworkProbe
from codex_doctor.state_machine import CodexState


def test_diagnose_current_uses_app_activity_without_prompt_content(monkeypatch, tmp_path):
    activity = AppActivity(
        session_id="s1",
        path=tmp_path / "rollout.jsonl",
        updated_at=datetime.now(timezone.utc),
        events=[
            AppEventSummary(
                ts=datetime.now(timezone.utc),
                outer_type="response_item",
                payload_type="function_call",
                name="exec_command",
                call_id="call_1",
            )
        ],
    )

    monkeypatch.setattr(current_status, "_safe_storage", lambda: None)
    monkeypatch.setattr(current_status, "_safe_latest_app_activity", lambda: activity)

    status = current_status.diagnose_current(include_network=False)

    assert status.source == "Codex App rollout fallback"
    assert status.diagnosis.state == CodexState.TOOL_RUNNING
    assert status.app_events[-1].label == "function_call exec_command"


def test_diagnose_current_stale_activity_with_network_ok(monkeypatch, tmp_path):
    old = datetime.now(timezone.utc) - timedelta(seconds=120)
    activity = AppActivity(
        session_id="s1",
        path=tmp_path / "rollout.jsonl",
        updated_at=old,
        events=[
            AppEventSummary(ts=old, outer_type="response_item", payload_type="reasoning"),
        ],
    )
    probe = NetworkProbe(target="api", ok=True, http_code=401, total_ms=420)

    monkeypatch.setattr(current_status, "_safe_storage", lambda: None)
    monkeypatch.setattr(current_status, "_safe_latest_app_activity", lambda: activity)
    monkeypatch.setattr(current_status, "run_probe", lambda timeout=5: probe)

    status = current_status.diagnose_current(include_network=True, stale_seconds=45)

    assert status.diagnosis.state == CodexState.API_OR_MODEL_WAITING
    assert status.network_probe is probe


def test_diagnose_current_stale_activity_with_network_failure(monkeypatch, tmp_path):
    old = datetime.now(timezone.utc) - timedelta(seconds=120)
    activity = AppActivity(
        session_id="s1",
        path=tmp_path / "rollout.jsonl",
        updated_at=old,
        events=[
            AppEventSummary(ts=old, outer_type="response_item", payload_type="reasoning"),
        ],
    )
    probe = NetworkProbe(target="api", ok=False, error_type="timeout")

    monkeypatch.setattr(current_status, "_safe_storage", lambda: None)
    monkeypatch.setattr(current_status, "_safe_latest_app_activity", lambda: activity)
    monkeypatch.setattr(current_status, "run_probe", lambda timeout=5: probe)

    status = current_status.diagnose_current(include_network=True, stale_seconds=45)

    assert status.diagnosis.state == CodexState.NETWORK_SUSPECTED
    assert status.network_probe is probe
