from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from typing import Any

from app.domain.events import NormalizedEvent


class EventsCurrentRepository(ABC):
    @abstractmethod
    def get_by_provider_event_id(self, provider_event_id: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def insert_new(self, event: NormalizedEvent, observed_at: dt.datetime) -> Any:
        raise NotImplementedError

    @abstractmethod
    def update_changed(self, current: Any, event: NormalizedEvent, observed_at: dt.datetime) -> Any:
        raise NotImplementedError

    @abstractmethod
    def touch_unchanged(self, current: Any, observed_at: dt.datetime) -> Any:
        raise NotImplementedError

    @abstractmethod
    def mark_missing_from_latest_feed(self, seen_provider_event_ids: set[str]) -> int:
        raise NotImplementedError

