from __future__ import annotations

import datetime as dt
import json
import logging

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.domain.events import NormalizedEvent
from app.domain.repositories.event_snapshots_repository import EventSnapshotsRepository
from app.infrastructure.db.models import EventSnapshot

logger = logging.getLogger(__name__)


def _log_json(event: str, **fields: object) -> None:
    logger.info("%s", json.dumps({"event": event, **fields}, default=str))


class PostgresEventSnapshotsRepository(EventSnapshotsRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def insert_if_new_hash(self, event: NormalizedEvent, observed_at: dt.datetime) -> bool:
        exists = (
            self.db.query(EventSnapshot.id)
            .filter(
                and_(
                    EventSnapshot.provider_event_id == event.provider_event_id,
                    EventSnapshot.payload_hash == event.payload_hash,
                )
            )
            .first()
        )
        if exists is not None:
            _log_json(
                "event_snapshot_skipped_existing_hash",
                provider_event_id=event.provider_event_id,
                payload_hash=event.payload_hash,
            )
            return False

        row = EventSnapshot(
            provider_event_id=event.provider_event_id,
            observed_at=observed_at,
            payload_hash=event.payload_hash,
            event_payload=event.event_payload,
        )
        self.db.add(row)
        self.db.flush()
        _log_json(
            "event_snapshot_inserted",
            provider_event_id=row.provider_event_id,
            payload_hash=row.payload_hash,
            observed_at=observed_at.isoformat(),
        )
        return True

