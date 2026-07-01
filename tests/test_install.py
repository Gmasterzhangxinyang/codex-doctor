from codex_doctor.constants import MANAGED_MARKER
from codex_doctor.install import desired_hooks, merge_hooks


def test_merge_hooks_preserves_user_hook_and_adds_managed_hook():
    current = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": "echo user"}],
                }
            ]
        }
    }
    merged = merge_hooks(current, desired_hooks())
    entries = merged["hooks"]["PreToolUse"]

    assert any(entry["hooks"][0]["command"] == "echo user" for entry in entries)
    assert any(entry["hooks"][0].get(MANAGED_MARKER) for entry in entries)
