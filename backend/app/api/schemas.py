from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.agent.state_machine import TaskState


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: str = Field(min_length=1, max_length=4000)
    requested_mode: Literal["DEMO", "READ_ONLY", "CONTROLLED_EXECUTION"] | None = None


class TaskTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_state: TaskState
    reason_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9_]+$")


class TaskView(BaseModel):
    id: str
    goal: str
    mode: str
    state: str
    version: int
    created_at: datetime


class ApprovalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_name: Literal[
        "safe_log_cleanup",
        "service_restart",
        "config_safe_update",
        "terminate_process",
        "rollback_change",
    ]
    arguments: dict[str, Any]
    expires_in: int = Field(default=300, ge=30, le=900)


class ApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=500)


class KnowledgeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=100_000)
    review_status: Literal["PENDING", "APPROVED", "REJECTED"] = "PENDING"


class ConfigBaselineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path_ref: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=200_000)


class ConfigDriftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path_ref: str = Field(min_length=1, max_length=500)
    current_content: str = Field(max_length=200_000)


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_interval_seconds: int = Field(ge=30, le=86_400)
    retention_days: int = Field(ge=1, le=365)


class IncidentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ACKNOWLEDGED", "RESOLVED", "CLOSED"]


class KnowledgeReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_status: Literal["APPROVED", "REJECTED"]


class ExecutionPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_name: Literal[
        "safe_log_cleanup",
        "service_restart",
        "config_safe_update",
        "terminate_process",
        "rollback_change",
    ]
    arguments: dict[str, Any]


class ExecutionRunRequest(ExecutionPreviewRequest):
    task_id: str = Field(min_length=1, max_length=64)
    approval_token: str = Field(min_length=64, max_length=4096)
    fault: Literal["verification"] | None = None


class ToolTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    arguments: dict[str, Any] = Field(default_factory=dict)


class ProcessCandidateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(min_length=1, max_length=64)
    pid: int = Field(ge=2, le=4_194_304)
