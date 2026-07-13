"""Persist execution, backup, verification and rollback evidence.

Revision ID: 0007_execution_evidence
Revises: 0006_cleanup_candidates
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_execution_evidence"
down_revision = "0006_cleanup_candidates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("approval_id", sa.String(36), nullable=False, unique=True),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("arguments_hash", sa.String(64), nullable=False),
        sa.Column("target_ref", sa.String(1000)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"]),
        sa.ForeignKeyConstraint(["approval_id"], ["approvals.id"]),
    )
    op.create_index("ix_executions_task_id", "executions", ["task_id"])
    op.create_index("ix_executions_tool_name", "executions", ["tool_name"])
    op.create_index("ix_executions_status", "executions", ["status"])
    op.create_table(
        "backups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("execution_id", sa.String(36), nullable=False),
        sa.Column("backup_ref", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"]),
    )
    op.create_index("ix_backups_execution_id", "backups", ["execution_id"])
    op.create_table(
        "verification_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("execution_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"]),
    )
    op.create_index(
        "ix_verification_results_execution_id", "verification_results", ["execution_id"]
    )
    op.create_table(
        "rollback_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("execution_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"]),
    )
    op.create_index("ix_rollback_records_execution_id", "rollback_records", ["execution_id"])


def downgrade() -> None:
    op.drop_index("ix_rollback_records_execution_id", table_name="rollback_records")
    op.drop_table("rollback_records")
    op.drop_index("ix_verification_results_execution_id", table_name="verification_results")
    op.drop_table("verification_results")
    op.drop_index("ix_backups_execution_id", table_name="backups")
    op.drop_table("backups")
    op.drop_index("ix_executions_status", table_name="executions")
    op.drop_index("ix_executions_tool_name", table_name="executions")
    op.drop_index("ix_executions_task_id", table_name="executions")
    op.drop_table("executions")
