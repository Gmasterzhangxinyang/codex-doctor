from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Event(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    ts: datetime = Field(default_factory=utc_now)
    source: Literal["hook", "wrapper", "probe", "process", "otel", "plugin-hook"] = "hook"
    session_id: str | None = None
    turn_id: str | None = None
    event_type: str
    cwd: str | None = None
    model: str | None = None
    permission_mode: str | None = None
    tool_name: str | None = None
    tool_input_hash: str | None = None
    tool_input_snippet: str | None = None
    success: bool | None = None
    duration_ms: int | None = None
    raw_redacted: dict[str, Any] = Field(default_factory=dict)
