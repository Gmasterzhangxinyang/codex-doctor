from codex_doctor.current_status import CurrentStatus
from codex_doctor.messages import describe_status_zh
from codex_doctor.schemas import Confidence, Diagnosis


def _status(state: str, evidence=None) -> CurrentStatus:
    return CurrentStatus(
        diagnosis=Diagnosis(
            state=state,
            confidence=Confidence.MEDIUM,
            title="raw title",
            explanation="raw explanation",
            evidence=evidence or {},
        ),
        source="test",
        session_id="s1",
    )


def test_describe_tool_running_in_chinese():
    message = describe_status_zh(
        _status("TOOL_RUNNING", {"tool": "exec_command"}),
        duration_seconds=66,
    )

    assert "已经 66 秒" in message.current
    assert "exec_command" in message.reason
    assert "本地工具" in message.action or "shell" in message.action


def test_describe_api_waiting_in_chinese():
    message = describe_status_zh(_status("API_OR_MODEL_WAITING"), duration_seconds=50)

    assert "没有新的可见进展" in message.current
    assert "OpenAI" in message.reason
    assert "等" in message.action
