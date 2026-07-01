import json

from codex_doctor.app_monitor import diagnose_app_activity, latest_app_activity
from codex_doctor.state_machine import CodexState


def test_latest_app_activity_reads_only_safe_event_metadata(tmp_path):
    session_dir = tmp_path / ".codex" / "sessions" / "2026" / "07" / "01"
    session_dir.mkdir(parents=True)
    session_id = "019f1c8f-50eb-7be3-87cf-59b786471584"
    rollout = session_dir / f"rollout-2026-07-01T15-23-02-{session_id}.jsonl"
    rollout.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": "2026-07-01T08:00:00.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "exec_command",
                            "arguments": {"cmd": "secret command"},
                            "call_id": "call_1",
                        },
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-07-01T08:00:01.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "output": "private output",
                            "call_id": "call_1",
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    activity = latest_app_activity(tmp_path / ".codex")

    assert activity is not None
    assert activity.session_id == session_id
    assert activity.events[-1].payload_type == "function_call_output"
    assert "private output" not in activity.events[-1].label


def test_app_activity_detects_open_function_call(tmp_path):
    session_dir = tmp_path / ".codex" / "sessions"
    session_dir.mkdir(parents=True)
    rollout = session_dir / "rollout-demo.jsonl"
    rollout.write_text(
        json.dumps(
            {
                "timestamp": "2026-07-01T08:00:00.000Z",
                "type": "response_item",
                "payload": {"type": "function_call", "name": "exec_command", "call_id": "call_1"},
            }
        ),
        encoding="utf-8",
    )

    activity = latest_app_activity(tmp_path / ".codex")
    diagnosis = diagnose_app_activity(activity)

    assert diagnosis.state == CodexState.TOOL_RUNNING
