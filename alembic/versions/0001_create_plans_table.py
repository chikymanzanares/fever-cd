from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "000000000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events_current",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sell_mode", sa.String(length=50), nullable=False),
        sa.Column("min_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("event_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ever_online", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_present_in_latest_feed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_events_current_start_at", "events_current", ["start_at"])
    op.create_index("idx_events_current_end_at", "events_current", ["end_at"])
    op.create_index("idx_events_current_sell_mode", "events_current", ["sell_mode"])
    op.create_index("idx_events_current_ever_online", "events_current", ["ever_online"])
    op.create_index("idx_events_current_last_seen_at", "events_current", ["last_seen_at"])
    op.create_index("idx_events_current_time_range", "events_current", ["start_at", "end_at"])

    op.create_table(
        "event_snapshots",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("event_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_event_snapshots_provider_event_id", "event_snapshots", ["provider_event_id"])
    op.create_index("idx_event_snapshots_observed_at", "event_snapshots", ["observed_at"])
    op.create_index(
        "uq_event_snapshots_provider_event_hash",
        "event_snapshots",
        ["provider_event_id", "payload_hash"],
        unique=True,
    )

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("events_received", sa.Integer(), nullable=True),
        sa.Column("events_inserted", sa.Integer(), nullable=True),
        sa.Column("events_updated", sa.Integer(), nullable=True),
        sa.Column("events_unchanged", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("sync_runs")

    op.drop_index("uq_event_snapshots_provider_event_hash", table_name="event_snapshots")
    op.drop_index("idx_event_snapshots_observed_at", table_name="event_snapshots")
    op.drop_index("idx_event_snapshots_provider_event_id", table_name="event_snapshots")
    op.drop_table("event_snapshots")

    op.drop_index("idx_events_current_time_range", table_name="events_current")
    op.drop_index("idx_events_current_last_seen_at", table_name="events_current")
    op.drop_index("idx_events_current_ever_online", table_name="events_current")
    op.drop_index("idx_events_current_sell_mode", table_name="events_current")
    op.drop_index("idx_events_current_end_at", table_name="events_current")
    op.drop_index("idx_events_current_start_at", table_name="events_current")
    op.drop_table("events_current")

