"""Add audit hash-chain columns."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_audit_hash"
down_revision: str | None = "0002_approvals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("audit_events") as batch:
        batch.add_column(sa.Column("previous_hash", sa.String(64), nullable=False, server_default=""))
        batch.add_column(sa.Column("current_hash", sa.String(64), nullable=True))
        batch.create_unique_constraint("uq_audit_events_current_hash", ["current_hash"])


def downgrade() -> None:
    with op.batch_alter_table("audit_events") as batch:
        batch.drop_constraint("uq_audit_events_current_hash", type_="unique")
        batch.drop_column("current_hash")
        batch.drop_column("previous_hash")
