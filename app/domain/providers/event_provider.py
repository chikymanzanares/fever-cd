from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.events import NormalizedEvent


class EventProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def fetch_raw(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw: str) -> list[NormalizedEvent]:
        raise NotImplementedError

    def fetch_and_parse(self) -> list[NormalizedEvent]:
        return self.parse(self.fetch_raw())
