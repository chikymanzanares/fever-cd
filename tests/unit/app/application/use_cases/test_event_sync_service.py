from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from app.application.use_cases.event_sync_service import EventSyncService
from app.domain.events import NormalizedEvent


@dataclass
class FakeCurrent:
    provider_event_id: str
    payload_hash: str


class FakeEventsCurrentRepository:
    def __init__(self, existing: dict[str, FakeCurrent] | None = None) -> None:
        self.store = existing or {}
        self.inserted = 0
        self.updated = 0
        self.unchanged_touched = 0
        self.missing_marked_with: set[str] | None = None

    def get_by_provider_event_id(self, provider_event_id: str):
        return self.store.get(provider_event_id)

    def insert_new(self, event: NormalizedEvent, observed_at: dt.datetime):
        self.inserted += 1
        current = FakeCurrent(provider_event_id=event.provider_event_id, payload_hash=event.payload_hash)
        self.store[event.provider_event_id] = current
        return current

    def update_changed(self, current: FakeCurrent, event: NormalizedEvent, observed_at: dt.datetime):
        self.updated += 1
        current.payload_hash = event.payload_hash
        return current

    def touch_unchanged(self, current: FakeCurrent, observed_at: dt.datetime):
        self.unchanged_touched += 1
        return current

    def mark_missing_from_latest_feed(self, seen_provider_event_ids: set[str]) -> int:
        self.missing_marked_with = seen_provider_event_ids
        missing = [pid for pid in self.store if pid not in seen_provider_event_ids]
        return len(missing)


class FakeEventSnapshotsRepository:
    def __init__(self) -> None:
        self.insert_calls = 0

    def insert_if_new_hash(self, event: NormalizedEvent, observed_at: dt.datetime) -> bool:
        self.insert_calls += 1
        return True


def _event(provider_event_id: str, payload_hash: str) -> NormalizedEvent:
    now = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    return NormalizedEvent(
        provider_event_id=provider_event_id,
        title=f"event-{provider_event_id}",
        start_at=now,
        end_at=now + dt.timedelta(hours=2),
        sell_mode="online",
        min_price=Decimal("10.00"),
        max_price=Decimal("20.00"),
        event_payload={"id": provider_event_id},
        payload_hash=payload_hash,
    )


def test_event_sync_service_handles_new_changed_unchanged_and_missing():
    # Existing state:
    # - "changed" exists with old hash
    # - "same" exists with same hash
    # - "missing" exists but won't be in incoming feed
    current_repo = FakeEventsCurrentRepository(
        existing={
            "changed": FakeCurrent(provider_event_id="changed", payload_hash="old"),
            "same": FakeCurrent(provider_event_id="same", payload_hash="same-hash"),
            "missing": FakeCurrent(provider_event_id="missing", payload_hash="missing-hash"),
        }
    )
    snapshots_repo = FakeEventSnapshotsRepository()
    service = EventSyncService(current_repo, snapshots_repo)

    incoming = [
        _event("new", "new-hash"),  # case 1
        _event("changed", "newer-hash"),  # case 2
        _event("same", "same-hash"),  # case 3
    ]

    stats = service.sync(incoming, observed_at=dt.datetime(2026, 1, 2, tzinfo=dt.timezone.utc))

    assert stats.events_received == 3
    assert stats.events_inserted == 1
    assert stats.events_updated == 1
    assert stats.events_unchanged == 1
    assert stats.events_marked_missing == 1  # "missing"

    # Snapshot insertion only for case 1 + 2
    assert snapshots_repo.insert_calls == 2

    # All incoming ids were tracked as seen
    assert current_repo.missing_marked_with == {"new", "changed", "same"}

