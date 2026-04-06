from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod

from app.domain.events import NormalizedEvent


class EventSnapshotsRepository(ABC):
    @abstractmethod
    def insert_if_new_hash(self, event: NormalizedEvent, observed_at: dt.datetime) -> bool:
        """
        Returns True when a new snapshot row is inserted.
        """
        raise NotImplementedError

