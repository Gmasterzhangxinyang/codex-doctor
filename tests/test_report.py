from codex_doctor.report import generate_report
from codex_doctor.schemas import Event, Session
from codex_doctor.storage import Storage


def test_report_without_session(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_DOCTOR_DATA_DIR", str(tmp_path))
    text = generate_report(last=True)
    assert "No session" in text


def test_report_with_session(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_DOCTOR_DATA_DIR", str(tmp_path))
    storage = Storage()
    storage.create_session(Session(id="s1", cwd="/tmp/repo"))
    storage.insert_event(Event(session_id="s1", event_type="PreToolUse", tool_name="Bash"))
    text = generate_report(session_id="s1")
    assert "TOOL_RUNNING" in text
    assert "Bash" in text
