from pathlib import Path

import pytest
import typer

from codex_doctor import cli
from codex_doctor.cli import (
    _check_notifications_or_exit,
    _notification_message,
    _normalize_after,
    _resolve_notify_settings,
    _should_notify,
    _should_notify_stuck,
)
from codex_doctor.current_status import CurrentStatus
from codex_doctor.notifications import NotificationResult
from codex_doctor.schemas import Confidence, Diagnosis
from codex_doctor.state_machine import CodexState


def _status(state: CodexState, project_path: Path | None = None) -> CurrentStatus:
    return CurrentStatus(
        diagnosis=Diagnosis(
            state=state.value,
            confidence=Confidence.MEDIUM,
            title="test",
            explanation="test",
        ),
        source="test",
        session_id="s1",
        project_path=project_path,
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
    message = _notification_message(
        _status(CodexState.TOOL_RUNNING, Path("/Users/bobby/Documents/codex-doctor")),
        duration_seconds=61,
    )
    assert "当前：" in message
    assert "项目：codex-doctor" in message
    assert "堵塞原因" not in message
    assert "原因：" in message
    assert "已经 61 秒" in message
    assert "卡在本地工具执行阶段" in message


def test_notification_message_supports_english():
    message = _notification_message(
        _status(CodexState.TOOL_RUNNING, Path("/Users/bobby/Documents/codex-doctor")),
        lang="en",
        duration_seconds=61,
    )

    assert message.startswith("Project: codex-doctor Current:")
    assert "Reason:" in message
    assert "Suggestion:" in message
    assert "61s" in message


def test_resolve_notify_settings_uses_defaults_without_interactive_prompt():
    lang, after = _resolve_notify_settings(lang=None, after=None, interactive=False)

    assert lang == "zh"
    assert after == 45.0


def test_resolve_notify_settings_uses_explicit_values():
    lang, after = _resolve_notify_settings(lang="en", after=30, interactive=False)

    assert lang == "en"
    assert after == 30.0


def test_normalize_after_rejects_non_positive_values():
    with pytest.raises(typer.Exit):
        _normalize_after(0)


def test_check_notifications_exits_on_failure(monkeypatch):
    monkeypatch.setattr(
        cli,
        "send_notification",
        lambda title, message: NotificationResult(ok=False, error="failed"),
    )

    with pytest.raises(typer.Exit):
        _check_notifications_or_exit()
