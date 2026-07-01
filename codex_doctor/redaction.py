from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .constants import DEFAULT_SNIPPET_CHARS

SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|token|secret|password|passwd|authorization|cookie|session)", re.I
)
SECRET_VALUE_RE = re.compile(r"(sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._-]{12,})", re.I)


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def snippet(value: Any, max_chars: int = DEFAULT_SNIPPET_CHARS) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, default=str)
    text = SECRET_VALUE_RE.sub("[REDACTED]", text)
    if len(text) > max_chars:
        return text[:max_chars] + "...[truncated]"
    return text


def redact(obj: Any, max_chars: int = DEFAULT_SNIPPET_CHARS) -> Any:
    if isinstance(obj, dict):
        redacted = {}
        for key, value in obj.items():
            if SECRET_KEY_RE.search(str(key)):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact(value, max_chars=max_chars)
        return redacted
    if isinstance(obj, list):
        return [redact(item, max_chars=max_chars) for item in obj]
    if isinstance(obj, str):
        return snippet(obj, max_chars=max_chars)
    return obj
