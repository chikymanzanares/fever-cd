from __future__ import annotations

import datetime as dt

from app.domain.repositories.sync_runs_repository import SyncRunsRepository
from sqlalchemy.orm import Session

from app.infrastructure.db.models import SyncRun


class PostgresSyncRunsRepository(SyncRunsRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_running(self, started_at: dt.datetime) -> int:
        row = SyncRun(
            started_at=started_at,
            status="running",
        )
        self.db.add(row)
        self.db.flush()
        return int(row.id)

    def mark_success(
        self,
        sync_run_id: int,
        finished_at: dt.datetime,
        events_received: int,
        events_inserted: int,
        events_updated: int,
        events_unchanged: int,
        events_marked_missing: int,
    ) -> None:
        row = self.db.get(SyncRun, sync_run_id)
        if row is None:
            return
        row.finished_at = finished_at
        row.status = "success"
        row.events_received = events_received
        row.events_inserted = events_inserted
        row.events_updated = events_updated
        row.events_unchanged = events_unchanged
        row.events_marked_missing = events_marked_missing
        row.error_message = None
        self.db.flush()

    def mark_failed(self, sync_run_id: int, finished_at: dt.datetime, error_message: str) -> None:
        row = self.db.get(SyncRun, sync_run_id)
        if row is None:
            return
        row.finished_at = finished_at
        row.status = "failed"
        row.error_message = error_message
        self.db.flush()
