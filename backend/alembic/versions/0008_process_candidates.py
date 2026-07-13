"""Persist frozen managed-process candidates.

Revision ID: 0008_process_candidates
Revises: 0007_execution_evidence
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_process_candidates"
down_revision = "0007_execution_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "process_candidates",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("process_name", sa.String(128), nullable=False),
        sa.Column("start_ticks", sa.Integer(), nullable=False),
        sa.Column("service", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ELIGIBLE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"]),
    )
    op.create_index("ix_process_candidates_task_id", "process_candidates", ["task_id"])
    op.create_index("ix_process_candidates_status", "process_candidates", ["status"])


def downgrade() -> None:
    op.drop_index("ix_process_candidates_status", table_name="process_candidates")
    op.drop_index("ix_process_candidates_task_id", table_name="process_candidates")
    op.drop_table("process_candidates")
