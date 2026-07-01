import json
from pathlib import Path

from codex_doctor.hook_recorder import normalize_hook_payload, record_payload
from codex_doctor.storage import Storage


def test_normalize_pre_tool_fixture():
    payload = json.loads(Path("tests/fixtures/hook_pre_tool_bash.json").read_text())
    event = normalize_hook_payload(payload)
    assert event.event_type == "PreToolUse"
    assert event.tool_name == "Bash"
    assert event.tool_input_hash
    assert "pytest" in event.tool_input_snippet


def test_record_payload_writes_storage(tmp_path):
    storage = Storage(db_file=tmp_path / "doctor.db", jsonl_file=tmp_path / "events.jsonl")
    event = record_payload(
        {"hook_event_name": "UserPromptSubmit", "session_id": "s1", "prompt": "hello"},
        storage=storage,
    )
    rows = storage.list_recent_events("s1")
    assert rows[0]["id"] == event.id
    assert (tmp_path / "events.jsonl").exists()
