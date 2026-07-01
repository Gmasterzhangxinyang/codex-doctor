from codex_doctor.notifications import _applescript_string
from codex_doctor import notifications


def test_applescript_string_escapes_quotes_and_backslashes():
    assert _applescript_string('a "quoted" \\ path') == '"a \\"quoted\\" \\\\ path"'


def test_send_notification_reports_osascript_failure(monkeypatch):
    class Completed:
        returncode = 1
        stdout = ""
        stderr = "syntax error"

    monkeypatch.setattr(notifications.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(notifications.subprocess, "run", lambda *args, **kwargs: Completed())

    result = notifications.send_notification("title", "message")

    assert not result.ok
    assert result.error == "syntax error"
