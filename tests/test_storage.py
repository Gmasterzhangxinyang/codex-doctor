from codex_doctor.schemas import Event, Session
from codex_doctor.storage import Storage


def test_create_session_and_insert_event(tmp_path):
    storage = Storage(db_file=tmp_path / "doctor.db", jsonl_file=tmp_path / "events.jsonl")
    storage.create_session(Session(id="s1", cwd="/tmp/repo"))
    storage.insert_event(Event(session_id="s1", event_type="UserPromptSubmit"))

    session = storage.get_latest_session()
    events = storage.list_recent_events("s1")

    assert session["id"] == "s1"
    assert events[0]["event_type"] == "UserPromptSubmit"


def test_end_session(tmp_path):
    storage = Storage(db_file=tmp_path / "doctor.db", jsonl_file=tmp_path / "events.jsonl")
    storage.create_session(Session(id="s1"))
    storage.end_session("s1")
    assert storage.get_latest_session()["status"] == "done"
