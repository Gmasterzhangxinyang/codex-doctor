from pathlib import Path

from codex_doctor import codex_locator


def test_find_codex_executable_uses_override(monkeypatch, tmp_path):
    executable = tmp_path / "codex"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)

    monkeypatch.setenv("CODEX_DOCTOR_CODEX_PATH", str(executable))
    monkeypatch.setattr(codex_locator.shutil, "which", lambda _: None)
    monkeypatch.setattr(codex_locator, "MACOS_APP_CODEX_PATHS", [])

    assert codex_locator.find_codex_executable() == str(executable)


def test_find_codex_executable_falls_back_to_macos_app(monkeypatch, tmp_path):
    executable = tmp_path / "Codex.app" / "Contents" / "Resources" / "codex"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)

    monkeypatch.delenv("CODEX_DOCTOR_CODEX_PATH", raising=False)
    monkeypatch.setattr(codex_locator.shutil, "which", lambda _: None)
    monkeypatch.setattr(codex_locator, "MACOS_APP_CODEX_PATHS", [Path(executable)])

    assert codex_locator.find_codex_executable() == str(executable)
