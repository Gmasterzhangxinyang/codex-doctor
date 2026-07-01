from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .events import utc_now


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Diagnosis(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    session_id: str | None = None
    ts: datetime = Field(default_factory=utc_now)
    state: str
    confidence: Confidence
    title: str
    explanation: str
    evidence: dict[str, Any] = Field(default_factory=dict)
