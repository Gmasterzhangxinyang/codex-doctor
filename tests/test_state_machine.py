from datetime import datetime, timedelta, timezone

from codex_doctor.schemas import Event, NetworkProbe
from codex_doctor.state_machine import CodexState, diagnose


def test_prompt_then_probe_fail_network_suspected(events_prompt_old):
    probe = NetworkProbe(target="api", ok=False, error_type="dns")
    assert diagnose(events_prompt_old, probe=probe).state == CodexState.NETWORK_SUSPECTED


def test_prompt_then_probe_ok_api_or_model_waiting(events_prompt_old):
    probe = NetworkProbe(target="api", ok=True, http_code=401)
    assert diagnose(events_prompt_old, probe=probe).state == CodexState.API_OR_MODEL_WAITING


def test_pre_tool_without_post_tool_is_tool_running():
    events = [
        Event(event_type="UserPromptSubmit", session_id="s1"),
        Event(event_type="PreToolUse", session_id="s1", tool_name="Bash"),
    ]
    diagnosis = diagnose(events)
    assert diagnosis.state == CodexState.TOOL_RUNNING
    assert diagnosis.confidence.value == "HIGH"


def test_permission_request_is_approval_waiting():
    events = [
        Event(
            event_type="PermissionRequest",
            session_id="s1",
            tool_name="Bash",
            ts=datetime.now(timezone.utc) - timedelta(seconds=8),
        )
    ]
    assert diagnose(events).state == CodexState.APPROVAL_WAITING


def test_pre_compact_is_context_compacting():
    events = [Event(event_type="PreCompact", session_id="s1")]
    assert diagnose(events).state == CodexState.CONTEXT_COMPACTING


def test_permission_denied_result_is_sandbox_blocked():
    events = [
        Event(
            event_type="PostToolUse",
            session_id="s1",
            tool_input_snippet="operation not permitted by sandbox",
        )
    ]
    assert diagnose(events).state == CodexState.SANDBOX_OR_PERMISSION_BLOCKED


def test_post_tool_clears_running_state():
    events = [
        Event(
            event_type="PreToolUse",
            session_id="s1",
            tool_name="Bash",
            ts=datetime.now(timezone.utc) - timedelta(seconds=5),
        ),
        Event(event_type="PostToolUse", session_id="s1", tool_name="Bash"),
    ]
    assert diagnose(events).state != CodexState.TOOL_RUNNING
