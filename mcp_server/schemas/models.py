from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(str, Enum):
    L1 = "L1"
    L2 = "L2"


class ToolMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    title_zh: str
    description_zh: str
    risk_level: RiskLevel
    read_only: bool = True
    timeout_seconds: int = Field(ge=1, le=60)
    max_output_bytes: int = Field(ge=1024, le=1_048_576)
    allowed_modes: tuple[str, ...] = ("DEMO", "READ_ONLY", "CONTROLLED_EXECUTION")
    platform_capabilities: tuple[str, ...] = ()


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_name: str
    status: str
    data: dict[str, Any]
    warnings: list[str] = []
    truncated: bool = False
    trust_label: str = "UNTRUSTED_DATA"
    is_demo: bool = False
    error_code: str | None = None
