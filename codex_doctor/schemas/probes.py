from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .events import utc_now


class NetworkProbe(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    session_id: str | None = None
    ts: datetime = Field(default_factory=utc_now)
    target: str
    ok: bool
    http_code: int | None = None
    dns_ms: float | None = None
    connect_ms: float | None = None
    tls_ms: float | None = None
    ttfb_ms: float | None = None
    total_ms: float | None = None
    error_type: str | None = None
    error_message: str | None = None
    proxy_summary: dict[str, Any] = Field(default_factory=dict)
