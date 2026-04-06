from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod


class SyncRunsRepository(ABC):
    @abstractmethod
    def create_running(self, started_at: dt.datetime) -> int:
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def mark_failed(self, sync_run_id: int, finished_at: dt.datetime, error_message: str) -> None:
        raise NotImplementedError
