from codex_doctor.notifications import _applescript_string


def test_applescript_string_escapes_quotes_and_backslashes():
    assert _applescript_string('a "quoted" \\ path') == '"a \\"quoted\\" \\\\ path"'
