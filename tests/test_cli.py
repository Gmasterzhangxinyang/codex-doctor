from codex_doctor.cli import _notification_message, _should_notify, _should_notify_stuck
from codex_doctor.current_status import CurrentStatus
from codex_doctor.schemas import Confidence, Diagnosis
from codex_doctor.state_machine import CodexState


def _status(state: CodexState) -> CurrentStatus:
    return CurrentStatus(
        diagnosis=Diagnosis(
            state=state.value,
            confidence=Confidence.MEDIUM,
            title="test",
            explanation="test",
        ),
        source="test",
        session_id="s1",
    )


def test_should_notify_is_quiet_for_normal_activity_by_default():
    assert not _should_notify(_status(CodexState.TOOL_RUNNING))


def test_should_notify_all_includes_normal_activity_but_not_idle():
    assert _should_notify(_status(CodexState.TOOL_RUNNING), notify_all=True)
    assert not _should_notify(_status(CodexState.IDLE), notify_all=True)


def test_should_notify_stuck_includes_long_running_active_states():
    assert _should_notify_stuck(_status(CodexState.MODEL_STREAMING))
    assert _should_notify_stuck(_status(CodexState.TOOL_RUNNING))
    assert not _should_notify_stuck(_status(CodexState.DONE))


def test_notification_message_can_include_duration():
    message = _notification_message(_status(CodexState.TOOL_RUNNING), duration_seconds=61)
    assert message.startswith("TOOL_RUNNING for 61s:")
