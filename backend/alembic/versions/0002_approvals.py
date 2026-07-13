"""Add approval persistence."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_approvals"
down_revision: str | None = "0001_phase1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("agent_tasks.id"), nullable=False),
        sa.Column("requester_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approver_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("arguments_json", sa.Text(), nullable=False),
        sa.Column("arguments_hash", sa.String(64), nullable=False),
        sa.Column("risk_level", sa.String(2), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("token_hash", sa.String(64), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("task_id", "requester_id", "approver_id", "status"):
        op.create_index(f"ix_approvals_{column}", "approvals", [column])


def downgrade() -> None:
    op.drop_table("approvals")
