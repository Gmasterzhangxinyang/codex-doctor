from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .events import utc_now


class Session(BaseModel):
    id: str = Field(default_factory=lambda: utc_now().strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8])
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None
    cwd: str | None = None
    codex_args: str | None = None
    codex_version: str | None = None
    model: str | None = None
    status: str | None = "running"
    total_duration_ms: int | None = None
