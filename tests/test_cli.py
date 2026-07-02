from pathlib import Path

from typer.testing import CliRunner

from codex_doctor import cli
from codex_doctor.cli import _normalize_lang
from codex_doctor.current_status import CurrentStatus
from codex_doctor.schemas import Confidence, Diagnosis


runner = CliRunner()


def _status() -> CurrentStatus:
    return CurrentStatus(
        diagnosis=Diagnosis(
            state="API_OR_MODEL_WAITING",
            confidence=Confidence.MEDIUM,
            title="Waiting",
            explanation="Network is reachable, but no recent Codex activity was observed.",
        ),
        source="test",
        session_id="s1",
    )


def test_default_command_runs_one_shot_diagnosis(monkeypatch):
    monkeypatch.setattr(cli, "diagnose_once", lambda options: _status())

    result = runner.invoke(cli.app, ["--no-network"])

    assert result.exit_code == 0
    assert "API_OR_MODEL_WAITING" in result.output
    assert "可见线索" in result.output


def test_report_writes_one_shot_markdown(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "diagnose_once", lambda options: _status())
    output = tmp_path / "report.md"

    result = runner.invoke(cli.app, ["report", "--no-network", "-o", str(output)])

    assert result.exit_code == 0
    assert output.exists()
    assert "Codex Session Health" in output.read_text(encoding="utf-8")


def test_report_prints_reason_to_terminal(monkeypatch):
    monkeypatch.setattr(cli, "diagnose_once", lambda options: _status())

    result = runner.invoke(cli.app, ["report", "--no-network"])

    assert result.exit_code == 0
    assert "Codex Session Health" in result.output
    assert "可能解释" in result.output


def test_install_saves_language_and_installs_hooks(monkeypatch, tmp_path):
    installed: dict[str, object] = {}

    monkeypatch.setenv("CODEX_DOCTOR_DATA_DIR", str(tmp_path))

    def fake_install_hooks(scope: str, force: bool) -> Path:
        installed["scope"] = scope
        installed["force"] = force
        return tmp_path / "hooks.json"

    monkeypatch.setattr(cli, "install_hooks", fake_install_hooks)

    result = runner.invoke(cli.app, ["install", "--lang", "en", "--force"])

    assert result.exit_code == 0
    assert installed == {"scope": "user", "force": True}
    assert "Language: English" in result.output


def test_normalize_lang_accepts_chinese_alias():
    assert _normalize_lang("中文") == "zh"
