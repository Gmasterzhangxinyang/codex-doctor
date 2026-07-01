#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

SECRET_WORDS = ("token", "key", "secret", "password", "authorization", "cookie")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        event = {
            "ts": time.time(),
            "source": "plugin-hook",
            "payload_hash": sha256(payload),
            "payload": redact(payload),
        }
        for path in output_paths():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
            except Exception:
                pass
    except Exception:
        pass
    return 0


def output_paths() -> list[Path]:
    paths = []
    plugin_data = os.environ.get("PLUGIN_DATA")
    if plugin_data:
        paths.append(Path(plugin_data) / "events.jsonl")
    paths.append(Path.home() / ".local" / "share" / "codex-doctor" / "events.jsonl")
    return paths


def sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            key: "[REDACTED]" if any(word in str(key).lower() for word in SECRET_WORDS) else redact(val)
            for key, val in obj.items()
        }
    if isinstance(obj, list):
        return [redact(item) for item in obj]
    if isinstance(obj, str):
        return obj[:500] + "...[truncated]" if len(obj) > 500 else obj
    return obj


if __name__ == "__main__":
    raise SystemExit(main())
