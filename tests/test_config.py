from pathlib import Path

from codex_doctor import config


def test_ensure_user_data_dir_falls_back_when_default_is_not_writable(monkeypatch, tmp_path):
    blocked = tmp_path / "blocked"
    fallback = tmp_path / "fallback"

    monkeypatch.setenv("CODEX_DOCTOR_DATA_DIR", str(blocked))
    monkeypatch.setattr(config, "fallback_data_dir", lambda: fallback)

    original_mkdir = Path.mkdir

    def fake_mkdir(self, *args, **kwargs):
        if self == blocked:
            raise PermissionError("blocked")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    assert config.ensure_user_data_dir() == fallback
    assert fallback.exists()
