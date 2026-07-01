from codex_doctor.redaction import redact, snippet, stable_hash


def test_redact_api_key():
    data = redact({"api_key": "sk-test-secret", "nested": {"token": "abc", "safe": "ok"}})
    assert data["api_key"] == "[REDACTED]"
    assert data["nested"]["token"] == "[REDACTED]"
    assert data["nested"]["safe"] == "ok"


def test_truncate_long_prompt():
    text = snippet("x" * 600, max_chars=20)
    assert text == "x" * 20 + "...[truncated]"


def test_hash_tool_input_is_stable():
    assert stable_hash({"command": "pytest"}) == stable_hash({"command": "pytest"})
    assert stable_hash({"command": "pytest"}) != stable_hash({"command": "ruff"})
