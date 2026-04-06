from __future__ import annotations

import datetime as dt
import json
import logging
from dataclasses import dataclass

from app.domain.events import NormalizedEvent
from app.domain.repositories.event_snapshots_repository import EventSnapshotsRepository
from app.domain.repositories.events_current_repository import EventsCurrentRepository

logger = logging.getLogger(__name__)


def _log_json(event: str, **fields: object) -> None:
    logger.info("%s", json.dumps({"event": event, **fields}, default=str))


@dataclass
class SyncStats:
    events_received: int = 0
    events_inserted: int = 0
    events_updated: int = 0
    events_unchanged: int = 0
    events_marked_missing: int = 0


class EventSyncService:
    def __init__(
        self,
        events_current_repo: EventsCurrentRepository,
        event_snapshots_repo: EventSnapshotsRepository,
    ) -> None:
        self.events_current_repo = events_current_repo
        self.event_snapshots_repo = event_snapshots_repo

    def sync(self, events: list[NormalizedEvent], observed_at: dt.datetime | None = None) -> SyncStats:
        """
        Implements the 4 sync cases:
        1) new event -> insert current + snapshot
        2) existing changed -> update current + snapshot
        3) existing unchanged -> touch last_seen/present only
        4) disappeared from feed -> mark is_present_in_latest_feed=false
        """
        if observed_at is None:
            observed_at = dt.datetime.now(dt.timezone.utc)

        stats = SyncStats(events_received=len(events))
        seen_provider_ids: set[str] = set()
        _log_json("sync_started", events_received=stats.events_received, observed_at=observed_at.isoformat())

        for event in events:
            seen_provider_ids.add(event.provider_event_id)

            current = self.events_current_repo.get_by_provider_event_id(event.provider_event_id)
            if current is None:
                self.events_current_repo.insert_new(event, observed_at)
                snapshot_inserted = self.event_snapshots_repo.insert_if_new_hash(event, observed_at)
                stats.events_inserted += 1
                _log_json(
                    "sync_case_new_event",
                    provider_event_id=event.provider_event_id,
                    payload_hash=event.payload_hash,
                    snapshot_inserted=snapshot_inserted,
                )
                continue

            if current.payload_hash != event.payload_hash:
                previous_payload_hash = current.payload_hash
                self.events_current_repo.update_changed(current, event, observed_at)
                snapshot_inserted = self.event_snapshots_repo.insert_if_new_hash(event, observed_at)
                stats.events_updated += 1
                _log_json(
                    "sync_case_event_changed",
                    provider_event_id=event.provider_event_id,
                    previous_payload_hash=previous_payload_hash,
                    new_payload_hash=event.payload_hash,
                    snapshot_inserted=snapshot_inserted,
                )
                continue

            self.events_current_repo.touch_unchanged(current, observed_at)
            stats.events_unchanged += 1
            _log_json(
                "sync_case_event_unchanged",
                provider_event_id=event.provider_event_id,
                payload_hash=event.payload_hash,
            )

        stats.events_marked_missing = self.events_current_repo.mark_missing_from_latest_feed(seen_provider_ids)
        _log_json(
            "sync_finished",
            events_received=stats.events_received,
            events_inserted=stats.events_inserted,
            events_updated=stats.events_updated,
            events_unchanged=stats.events_unchanged,
            events_marked_missing=stats.events_marked_missing,
        )
        return stats

