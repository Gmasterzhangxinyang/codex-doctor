from codex_doctor import tui


def test_watch_handles_storage_render_errors(monkeypatch):
    rendered = []

    class BrokenStorage:
        def get_latest_session(self):
            raise OSError("blocked")

    class FakeConsole:
        def print(self, *args, **kwargs):
            pass

    class FakeLive:
        def __init__(self, initial, console=None, refresh_per_second=4):
            rendered.append(initial)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def update(self, value):
            rendered.append(value)
            raise KeyboardInterrupt

    class FakePanel:
        def __init__(self, value, title=""):
            self.value = value
            self.title = title

    class FakeTable:
        @classmethod
        def grid(cls, expand=True):
            return cls()

        def __init__(self):
            self.rows = []

        def add_column(self, ratio=1):
            pass

        def add_row(self, value=""):
            self.rows.append(value)

    monkeypatch.setattr(tui, "Storage", BrokenStorage)
    monkeypatch.setattr(tui, "latest_app_activity", lambda: None)
    monkeypatch.setattr("rich.console.Console", FakeConsole)
    monkeypatch.setattr("rich.live.Live", FakeLive)
    monkeypatch.setattr("rich.panel.Panel", FakePanel)
    monkeypatch.setattr("rich.table.Table", FakeTable)
    monkeypatch.setattr(tui.time, "sleep", lambda _: None)

    tui.watch(refresh_seconds=0)

    assert rendered
