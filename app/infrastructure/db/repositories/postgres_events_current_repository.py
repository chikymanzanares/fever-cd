from __future__ import annotations

import datetime as dt
import json
import logging

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.domain.events import NormalizedEvent
from app.domain.repositories.events_current_repository import EventsCurrentRepository
from app.infrastructure.db.models import EventCurrent

logger = logging.getLogger(__name__)


def _log_json(event: str, **fields: object) -> None:
    logger.info("%s", json.dumps({"event": event, **fields}, default=str))


class PostgresEventsCurrentRepository(EventsCurrentRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_provider_event_id(self, provider_event_id: str) -> EventCurrent | None:
        return (
            self.db.query(EventCurrent)
            .filter(EventCurrent.provider_event_id == provider_event_id)
            .one_or_none()
        )

    def insert_new(self, event: NormalizedEvent, observed_at: dt.datetime) -> EventCurrent:
        row = EventCurrent(
            provider_event_id=event.provider_event_id,
            title=event.title,
            start_at=event.start_at,
            end_at=event.end_at,
            sell_mode=event.sell_mode,
            min_price=event.min_price,
            max_price=event.max_price,
            event_payload=event.event_payload,
            payload_hash=event.payload_hash,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
            ever_online=(event.sell_mode == "online"),
            is_present_in_latest_feed=True,
        )
        self.db.add(row)
        self.db.flush()
        _log_json(
            "events_current_inserted",
            provider_event_id=row.provider_event_id,
            payload_hash=row.payload_hash,
            observed_at=observed_at.isoformat(),
        )
        return row

    def update_changed(self, current: EventCurrent, event: NormalizedEvent, observed_at: dt.datetime) -> EventCurrent:
        previous_payload_hash = current.payload_hash
        current.title = event.title
        current.start_at = event.start_at
        current.end_at = event.end_at
        current.sell_mode = event.sell_mode
        current.min_price = event.min_price
        current.max_price = event.max_price
        current.event_payload = event.event_payload
        current.payload_hash = event.payload_hash
        current.last_seen_at = observed_at
        current.ever_online = current.ever_online or (event.sell_mode == "online")
        current.is_present_in_latest_feed = True
        self.db.flush()
        _log_json(
            "events_current_updated_changed",
            provider_event_id=current.provider_event_id,
            previous_payload_hash=previous_payload_hash,
            new_payload_hash=current.payload_hash,
            observed_at=observed_at.isoformat(),
        )
        return current

    def touch_unchanged(self, current: EventCurrent, observed_at: dt.datetime) -> EventCurrent:
        current.last_seen_at = observed_at
        current.is_present_in_latest_feed = True
        self.db.flush()
        _log_json(
            "events_current_touched_unchanged",
            provider_event_id=current.provider_event_id,
            payload_hash=current.payload_hash,
            observed_at=observed_at.isoformat(),
        )
        return current

    def mark_missing_from_latest_feed(self, seen_provider_event_ids: set[str]) -> int:
        stmt = update(EventCurrent).values(is_present_in_latest_feed=False)
        if seen_provider_event_ids:
            stmt = stmt.where(EventCurrent.provider_event_id.notin_(seen_provider_event_ids))
        result = self.db.execute(stmt)
        self.db.flush()
        marked = int(result.rowcount or 0)
        _log_json(
            "events_current_marked_missing",
            seen_count=len(seen_provider_event_ids),
            marked_missing_count=marked,
        )
        return marked

