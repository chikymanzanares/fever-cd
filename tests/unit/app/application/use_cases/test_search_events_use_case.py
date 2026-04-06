from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from app.application.use_cases.search_events_use_case import SearchEventsUseCase


class FakeQuery:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows
        self.filters: list[object] = []

    def filter(self, *args, **kwargs):
        self.filters.append((args, kwargs))
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self) -> list[object]:
        return self.rows


class FakeSession:
    def __init__(self, rows: list[object]) -> None:
        self.query_obj = FakeQuery(rows)

    def query(self, _model):
        return self.query_obj


class FakeCache:
    def __init__(self, cached: dict | None = None) -> None:
        self.cached = cached
        self.store: dict[str, dict] = {}
        self.get_calls = 0
        self.set_calls = 0

    def get_version(self) -> int:
        return 1

    def bump_version(self) -> int:
        return 2

    def get(self, key: str):
        self.get_calls += 1
        return self.cached

    def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        self.set_calls += 1
        self.store[key] = value


def _row(provider_event_id: str = "1591:1642") -> object:
    return type(
        "Row",
        (),
        {
            "provider_event_id": provider_event_id,
            "title": "Los Morancos",
            "start_at": dt.datetime(2021, 7, 31, 18, 0, tzinfo=dt.timezone.utc),
            "end_at": dt.datetime(2021, 7, 31, 19, 0, tzinfo=dt.timezone.utc),
            "min_price": Decimal("65.00"),
            "max_price": Decimal("75.00"),
        },
    )()


def test_search_use_case_raises_for_invalid_range():
    use_case = SearchEventsUseCase(db=FakeSession([]), cache=None)
    with pytest.raises(ValueError, match="starts_at must be less than or equal to ends_at"):
        use_case.execute(
            starts_at=dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc),
            ends_at=dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc),
            mode="local",
        )


def test_search_use_case_returns_hit_when_cache_has_payload():
    expected = {"data": {"events": [{"id": "x"}]}, "error": None}
    cache = FakeCache(cached=expected)
    use_case = SearchEventsUseCase(db=FakeSession([_row()]), cache=cache)

    result = use_case.execute(
        starts_at=dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc),
        ends_at=dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc),
        mode="local",
    )

    assert result.cache_header == "HIT"
    assert result.payload == expected
    assert cache.get_calls == 1
    assert cache.set_calls == 0


def test_search_use_case_returns_miss_and_sets_cache_for_non_empty_results():
    cache = FakeCache()
    use_case = SearchEventsUseCase(db=FakeSession([_row()]), cache=cache)

    result = use_case.execute(
        starts_at=dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc),
        ends_at=dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc),
        mode="local",
    )

    assert result.cache_header == "MISS"
    assert result.payload["error"] is None
    assert len(result.payload["data"]["events"]) == 1
    assert cache.set_calls == 1


def test_search_use_case_does_not_set_cache_for_empty_results():
    cache = FakeCache()
    use_case = SearchEventsUseCase(db=FakeSession([]), cache=cache)

    result = use_case.execute(
        starts_at=dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc),
        ends_at=dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc),
        mode="utc",
    )

    assert result.cache_header == "MISS"
    assert result.payload["data"]["events"] == []
    assert cache.set_calls == 0
