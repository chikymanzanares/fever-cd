import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from uuid import UUID

from app.main import app
from app.infrastructure.db.models import Base, EventCurrent
from app.infrastructure.db.session import get_database_url, session_scope


def _ensure_one_event_for_search_cache_tests() -> None:
    """Search only caches non-empty payloads; cache header tests need ≥1 matching row."""
    tz = dt.timezone.utc
    start = dt.datetime(2025, 1, 1, tzinfo=tz)
    end = dt.datetime(2025, 12, 31, tzinfo=tz)
    pid = "integration-test:cache-seed"
    with session_scope() as db:
        if db.query(EventCurrent).filter(EventCurrent.provider_event_id == pid).first() is not None:
            return
        db.add(
            EventCurrent(
                provider_event_id=pid,
                title="Cache seed",
                start_at=start,
                end_at=end,
                sell_mode="online",
                min_price=None,
                max_price=None,
                event_payload={},
                payload_hash="0" * 64,
                first_seen_at=start,
                last_seen_at=start,
                ever_online=True,
                is_present_in_latest_feed=True,
            )
        )


def test_search_returns_plans_list_from_postgres():
    """
    El challenge corre con Postgres (docker-compose + alembic).
    Este test asume que Postgres está accesible vía DATABASE_URL.
    """
    url = get_database_url()
    engine = create_engine(url, pool_pre_ping=True)

    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError:
        # Si alguien corre tests sin levantar el stack, no queremos fallar ruidosamente.
        import pytest

        pytest.skip("Postgres no está disponible (no se pudo conectar con DATABASE_URL).")

    client = TestClient(app)
    res = client.get(
        "/search",
        params={
            "starts_at": "2020-01-01T00:00:00Z",
            "ends_at": "2030-01-01T00:00:00Z",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert "error" in body
    assert body["error"] is None
    assert "events" in body["data"]
    assert isinstance(body["data"]["events"], list)
    if body["data"]["events"]:
        event = body["data"]["events"][0]
        UUID(event["id"])
        assert "provider_base_plan_id" not in event
        assert "provider_plan_id" not in event


def test_search_returns_400_for_invalid_range():
    client = TestClient(app)
    res = client.get(
        "/search",
        params={
            "starts_at": "2030-01-01T00:00:00Z",
            "ends_at": "2020-01-01T00:00:00Z",
        },
    )
    assert res.status_code == 400
    body = res.json()
    assert body["data"] is None
    assert body["error"]["code"] == "BAD_REQUEST"


def test_search_returns_400_for_invalid_datetime_format():
    client = TestClient(app)
    res = client.get(
        "/search",
        params={
            "starts_at": "not-a-date",
            "ends_at": "2030-01-01T00:00:00Z",
        },
    )
    assert res.status_code == 400
    body = res.json()
    assert body["data"] is None
    assert body["error"]["code"] == "BAD_REQUEST"


def test_search_cache_header_hit_after_second_call(monkeypatch):
    _ensure_one_event_for_search_cache_tests()
    cache_store: dict[str, dict] = {}
    cache_meta = {"version": 1, "set_calls": 0}

    class FakeCache:
        def get_version(self) -> int:
            return cache_meta["version"]

        def bump_version(self) -> int:
            cache_meta["version"] += 1
            return cache_meta["version"]

        def get(self, key: str):
            return cache_store.get(key)

        def set(self, key: str, value: dict, ttl_seconds: int) -> None:
            cache_meta["set_calls"] += 1
            cache_store[key] = value

    monkeypatch.setattr(
        "app.api.routes.search.get_search_cache",
        lambda: FakeCache(),
    )

    client = TestClient(app)
    params = {
        "starts_at": "2020-01-01T00:00:00Z",
        "ends_at": "2030-01-01T00:00:00Z",
    }
    first = client.get("/search", params=params)
    second = client.get("/search", params=params)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.headers["x-search-cache"] == "MISS"
    assert second.headers["x-search-cache"] == "HIT"
    assert cache_meta["set_calls"] == 1


def test_search_cache_key_normalization_uses_equivalent_utc_tokens(monkeypatch):
    _ensure_one_event_for_search_cache_tests()
    cache_store: dict[str, dict] = {}
    cache_meta = {"version": 1, "set_calls": 0}

    class FakeCache:
        def get_version(self) -> int:
            return cache_meta["version"]

        def bump_version(self) -> int:
            cache_meta["version"] += 1
            return cache_meta["version"]

        def get(self, key: str):
            return cache_store.get(key)

        def set(self, key: str, value: dict, ttl_seconds: int) -> None:
            cache_meta["set_calls"] += 1
            cache_store[key] = value

    monkeypatch.setattr("app.api.routes.search.get_search_cache", lambda: FakeCache())

    client = TestClient(app)
    first = client.get(
        "/search",
        params={
            "starts_at": "2020-01-01T00:00:00Z",
            "ends_at": "2030-01-01T00:00:00Z",
        },
    )
    second = client.get(
        "/search",
        params={
            "starts_at": "2020-01-01T00:00:00+00:00",
            "ends_at": "2030-01-01T00:00:00+00:00",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.headers["x-search-cache"] == "MISS"
    assert second.headers["x-search-cache"] == "HIT"
    assert cache_meta["set_calls"] == 1


def test_search_fail_open_when_cache_backend_fails(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.search.get_search_cache",
        lambda: (_ for _ in ()).throw(RuntimeError("redis down")),
    )
    client = TestClient(app)
    res = client.get(
        "/search",
        params={
            "starts_at": "2020-01-01T00:00:00Z",
            "ends_at": "2030-01-01T00:00:00Z",
        },
    )
    assert res.status_code == 200
    assert res.headers["x-search-cache"] == "MISS"


def test_search_does_not_cache_empty_results(monkeypatch):
    cache_store: dict[str, dict] = {}
    cache_meta = {"version": 1, "set_calls": 0}

    class FakeCache:
        def get_version(self) -> int:
            return cache_meta["version"]

        def bump_version(self) -> int:
            cache_meta["version"] += 1
            return cache_meta["version"]

        def get(self, key: str):
            return cache_store.get(key)

        def set(self, key: str, value: dict, ttl_seconds: int) -> None:
            cache_meta["set_calls"] += 1
            cache_store[key] = value

    monkeypatch.setattr("app.api.routes.search.get_search_cache", lambda: FakeCache())

    client = TestClient(app)
    res = client.get(
        "/search",
        params={
            "starts_at": "1900-01-01T00:00:00Z",
            "ends_at": "1900-01-02T00:00:00Z",
        },
    )
    assert res.status_code == 200
    assert res.headers["x-search-cache"] == "MISS"
    assert res.json()["data"]["events"] == []
    assert cache_meta["set_calls"] == 0


def test_search_fail_open_when_cache_get_raises(monkeypatch):
    class FakeCache:
        def get_version(self) -> int:
            return 1

        def bump_version(self) -> int:
            return 2

        def get(self, key: str):
            raise RuntimeError("redis get failed")

        def set(self, key: str, value: dict, ttl_seconds: int) -> None:
            return None

    monkeypatch.setattr("app.api.routes.search.get_search_cache", lambda: FakeCache())

    client = TestClient(app)
    res = client.get(
        "/search",
        params={
            "starts_at": "2020-01-01T00:00:00Z",
            "ends_at": "2030-01-01T00:00:00Z",
        },
    )
    assert res.status_code == 200
    assert res.headers["x-search-cache"] == "MISS"


def test_search_fail_open_when_cache_set_raises(monkeypatch):
    cache_store: dict[str, dict] = {}

    class FakeCache:
        def get_version(self) -> int:
            return 1

        def bump_version(self) -> int:
            return 2

        def get(self, key: str):
            return cache_store.get(key)

        def set(self, key: str, value: dict, ttl_seconds: int) -> None:
            raise RuntimeError("redis set failed")

    monkeypatch.setattr("app.api.routes.search.get_search_cache", lambda: FakeCache())

    client = TestClient(app)
    res = client.get(
        "/search",
        params={
            "starts_at": "2020-01-01T00:00:00Z",
            "ends_at": "2030-01-01T00:00:00Z",
        },
    )
    assert res.status_code == 200
    assert res.headers["x-search-cache"] == "MISS"
