"""Persist structured evidence, tool calls and guard decisions.

Revision ID: 0009_agent_trace
Revises: 0008_process_candidates
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_agent_trace"
down_revision = "0008_process_candidates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("evidence_type", sa.String(32), nullable=False),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("trust_label", sa.String(32), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"]),
    )
    for name, columns in (
        ("ix_evidence_task_id", ["task_id"]),
        ("ix_evidence_evidence_type", ["evidence_type"]),
        ("ix_evidence_source", ["source"]),
    ):
        op.create_index(name, "evidence", columns)
    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("arguments_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("trust_label", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"]),
    )
    for name, columns in (
        ("ix_tool_calls_task_id", ["task_id"]),
        ("ix_tool_calls_tool_name", ["tool_name"]),
        ("ix_tool_calls_status", ["status"]),
    ):
        op.create_index(name, "tool_calls", columns)
    op.create_table(
        "guard_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("risk_level", sa.String(2), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("public_summary", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"]),
    )
    for name, columns in (
        ("ix_guard_decisions_task_id", ["task_id"]),
        ("ix_guard_decisions_decision", ["decision"]),
        ("ix_guard_decisions_reason_code", ["reason_code"]),
    ):
        op.create_index(name, "guard_decisions", columns)


def downgrade() -> None:
    for name in (
        "ix_guard_decisions_reason_code",
        "ix_guard_decisions_decision",
        "ix_guard_decisions_task_id",
    ):
        op.drop_index(name, table_name="guard_decisions")
    op.drop_table("guard_decisions")
    for name in ("ix_tool_calls_status", "ix_tool_calls_tool_name", "ix_tool_calls_task_id"):
        op.drop_index(name, table_name="tool_calls")
    op.drop_table("tool_calls")
    for name in ("ix_evidence_source", "ix_evidence_evidence_type", "ix_evidence_task_id"):
        op.drop_index(name, table_name="evidence")
    op.drop_table("evidence")
