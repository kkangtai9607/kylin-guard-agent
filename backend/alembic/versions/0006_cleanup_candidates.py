"""Persist deterministic cleanup candidates.

Revision ID: 0006_cleanup_candidates
Revises: 0005_audit_head
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_cleanup_candidates"
down_revision = "0005_audit_head"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cleanup_candidates",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("path", sa.String(length=1000), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inode", sa.Integer(), nullable=False),
        sa.Column("device", sa.Integer(), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ELIGIBLE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"]),
    )
    op.create_index("ix_cleanup_candidates_task_id", "cleanup_candidates", ["task_id"])
    op.create_index("ix_cleanup_candidates_snapshot_hash", "cleanup_candidates", ["snapshot_hash"])
    op.create_index("ix_cleanup_candidates_status", "cleanup_candidates", ["status"])


def downgrade() -> None:
    op.drop_index("ix_cleanup_candidates_status", table_name="cleanup_candidates")
    op.drop_index("ix_cleanup_candidates_snapshot_hash", table_name="cleanup_candidates")
    op.drop_index("ix_cleanup_candidates_task_id", table_name="cleanup_candidates")
    op.drop_table("cleanup_candidates")
