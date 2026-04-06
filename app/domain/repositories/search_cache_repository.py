from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SearchCacheRepository(ABC):
    @abstractmethod
    def get_version(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def bump_version(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def get(self, key: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        raise NotImplementedError
