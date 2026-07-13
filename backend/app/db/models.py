from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    roles: Mapped[list[Role]] = relationship(secondary="user_roles", back_populates="users")


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(32), unique=True)
    users: Mapped[list[User]] = relationship(secondary="user_roles", back_populates="roles")


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id"),)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )


class UserSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    user: Mapped[User] = relationship()


class AgentTask(Base):
    __tablename__ = "agent_tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    goal: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(32), default="READ_ONLY")
    state: Mapped[str] = mapped_column(String(32), default="RECEIVED", index=True)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    steps: Mapped[list[TaskStep]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class TaskStep(Base):
    __tablename__ = "task_steps"
    __table_args__ = (UniqueConstraint("task_id", "sequence"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int]
    from_state: Mapped[str] = mapped_column(String(32))
    to_state: Mapped[str] = mapped_column(String(32))
    reason_code: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    task: Mapped[AgentTask] = relationship(back_populates="steps")


class EvidenceRecordModel(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(32), index=True)
    source: Mapped[str] = mapped_column(String(128), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    trust_label: Mapped[str] = mapped_column(String(32), default="UNTRUSTED_DATA")
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ToolCallRecord(Base):
    __tablename__ = "tool_calls"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id"), index=True)
    sequence: Mapped[int]
    tool_name: Mapped[str] = mapped_column(String(128), index=True)
    arguments_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), index=True)
    result_json: Mapped[str] = mapped_column(Text)
    trust_label: Mapped[str] = mapped_column(String(32), default="UNTRUSTED_DATA")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class GuardDecisionRecord(Base):
    __tablename__ = "guard_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id"), index=True)
    stage: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(32), index=True)
    risk_level: Mapped[str] = mapped_column(String(2))
    reason_code: Mapped[str] = mapped_column(String(64), index=True)
    public_summary: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str | None] = mapped_column(ForeignKey("agent_tasks.id"), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    previous_hash: Mapped[str] = mapped_column(String(64), default="")
    current_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class AuditChainHead(Base):
    __tablename__ = "audit_chain_head"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    current_hash: Mapped[str] = mapped_column(String(64), default="")
    version: Mapped[int] = mapped_column(default=0)


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id"), index=True)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    approver_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    tool_name: Mapped[str] = mapped_column(String(128))
    arguments_json: Mapped[str] = mapped_column(Text)
    arguments_hash: Mapped[str] = mapped_column(String(64))
    risk_level: Mapped[str] = mapped_column(String(2), default="L3")
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CleanupCandidateRecord(Base):
    __tablename__ = "cleanup_candidates"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id"), index=True)
    path: Mapped[str] = mapped_column(String(1000))
    size_bytes: Mapped[int]
    modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    inode: Mapped[int]
    device: Mapped[int]
    snapshot_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="ELIGIBLE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProcessCandidateRecord(Base):
    __tablename__ = "process_candidates"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id"), index=True)
    pid: Mapped[int]
    process_name: Mapped[str] = mapped_column(String(128))
    start_ticks: Mapped[int]
    service: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="ELIGIBLE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ExecutionRecord(Base):
    __tablename__ = "executions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("agent_tasks.id"), index=True)
    approval_id: Mapped[str] = mapped_column(ForeignKey("approvals.id"), unique=True)
    tool_name: Mapped[str] = mapped_column(String(128), index=True)
    arguments_hash: Mapped[str] = mapped_column(String(64))
    target_ref: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BackupRecord(Base):
    __tablename__ = "backups"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id: Mapped[str] = mapped_column(ForeignKey("executions.id"), index=True)
    backup_ref: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(32), default="VERIFIED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class VerificationResultRecord(Base):
    __tablename__ = "verification_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id: Mapped[str] = mapped_column(ForeignKey("executions.id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RollbackRecord(Base):
    __tablename__ = "rollback_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id: Mapped[str] = mapped_column(ForeignKey("executions.id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SystemSnapshot(Base):
    __tablename__ = "system_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(64), default="system_snapshot")
    payload_json: Mapped[str] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("system_snapshots.id"), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="INFO", index=True)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", index=True)
    summary: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class ConfigBaseline(Base):
    __tablename__ = "config_baselines"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    path_ref: Mapped[str] = mapped_column(String(500), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    redacted_content: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
