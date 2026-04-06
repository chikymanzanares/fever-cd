from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "000000000002"
down_revision = "000000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sync_runs", sa.Column("events_marked_missing", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("sync_runs", "events_marked_missing")
