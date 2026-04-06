from __future__ import annotations

import json
import os
from typing import Any

import redis

from app.domain.repositories.search_cache_repository import SearchCacheRepository

SEARCH_CACHE_VERSION_KEY = "search:version"


class RedisSearchCacheRepository(SearchCacheRepository):
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client

    def get_version(self) -> int:
        raw = self.redis.get(SEARCH_CACHE_VERSION_KEY)
        if raw is None:
            self.redis.set(SEARCH_CACHE_VERSION_KEY, "1")
            return 1
        return int(raw)

    def bump_version(self) -> int:
        return int(self.redis.incr(SEARCH_CACHE_VERSION_KEY))

    def get(self, key: str) -> dict[str, Any] | None:
        raw = self.redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self.redis.set(key, json.dumps(value), ex=ttl_seconds)


def get_search_cache() -> SearchCacheRepository:
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    client = redis.from_url(redis_url, decode_responses=True)
    return RedisSearchCacheRepository(client)
