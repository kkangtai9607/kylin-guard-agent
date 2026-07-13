from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EvidenceType(str, Enum):
    METRIC = "METRIC"
    PROCESS = "PROCESS"
    LOG = "LOG"
    PORT = "PORT"
    SERVICE = "SERVICE"
    CONFIG = "CONFIG"


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    evidence_type: EvidenceType
    source: str
    title: str
    value: float | str | bool
    anomaly_score: float = Field(ge=0, le=1)
    temporal_score: float = Field(ge=0, le=1)
    trust_label: str = "UNTRUSTED_DATA"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = []
