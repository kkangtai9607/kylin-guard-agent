"""Add snapshots, incidents, baselines and settings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_operations"
down_revision: str | None = "0003_audit_hash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "system_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_system_snapshots_is_demo", "system_snapshots", ["is_demo"])
    op.create_index("ix_system_snapshots_captured_at", "system_snapshots", ["captured_at"])
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("snapshot_id", sa.String(36), sa.ForeignKey("system_snapshots.id")),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("snapshot_id", "severity", "status", "created_at"):
        op.create_index(f"ix_incidents_{column}", "incidents", [column])
    op.create_table(
        "config_baselines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("path_ref", sa.String(500), nullable=False, unique=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("redacted_content", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "settings",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in ("settings", "config_baselines", "incidents", "system_snapshots"):
        op.drop_table(table)
