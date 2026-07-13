"""Add serialized audit chain head."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_audit_head"
down_revision: str | None = "0004_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    table = op.create_table(
        "audit_chain_head",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("current_hash", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
    )
    op.bulk_insert(table, [{"id": 1, "current_hash": "", "version": 0}])


def downgrade() -> None:
    op.drop_table("audit_chain_head")
