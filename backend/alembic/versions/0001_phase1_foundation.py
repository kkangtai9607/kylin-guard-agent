"""Phase 1 foundation tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_phase1"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("roles", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(32), nullable=False, unique=True))
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("username", sa.String(64), nullable=False), sa.Column("password_hash", sa.String(512), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("username"))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table("user_roles", sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True), sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True), sa.UniqueConstraint("user_id", "role_id"))
    op.create_table("sessions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"], unique=True)
    op.create_table("agent_tasks", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("goal", sa.Text(), nullable=False), sa.Column("mode", sa.String(32), nullable=False), sa.Column("state", sa.String(32), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_agent_tasks_user_id", "agent_tasks", ["user_id"])
    op.create_index("ix_agent_tasks_state", "agent_tasks", ["state"])
    op.create_table("task_steps", sa.Column("id", sa.String(36), primary_key=True), sa.Column("task_id", sa.String(36), sa.ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False), sa.Column("sequence", sa.Integer(), nullable=False), sa.Column("from_state", sa.String(32), nullable=False), sa.Column("to_state", sa.String(32), nullable=False), sa.Column("reason_code", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("task_id", "sequence"))
    op.create_index("ix_task_steps_task_id", "task_steps", ["task_id"])
    op.create_table("audit_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("task_id", sa.String(36), sa.ForeignKey("agent_tasks.id")), sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id")), sa.Column("event_type", sa.String(64), nullable=False), sa.Column("payload_json", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_audit_events_task_id", "audit_events", ["task_id"])
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    for table in ("audit_events", "task_steps", "agent_tasks", "sessions", "user_roles", "users", "roles"):
        op.drop_table(table)
