from __future__ import annotations

import datetime as dt
import sys
import types
import pytest

from app.application.use_cases.event_sync_service import SyncStats
from app.domain.events import NormalizedEvent


class _FakeTask:
    def __init__(self, fn):
        self.run = fn

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)


class _FakeCelery:
    def __init__(self, *args, **kwargs):
        self.conf: dict = {}

    def task(self, *args, **kwargs):
        def decorator(fn):
            return _FakeTask(fn)

        return decorator


fake_celery_module = types.ModuleType("celery")
fake_celery_module.Celery = _FakeCelery
sys.modules.setdefault("celery", fake_celery_module)

from app.worker.tasks import sync_events


def test_sync_events_orchestrates_fetch_normalize_and_sync(monkeypatch):
    class DummySessionScope:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    captured: dict[str, object] = {}
    fake_events = [
        NormalizedEvent(
            provider_event_id="1:1",
            title="event",
            start_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
            end_at=dt.datetime(2026, 1, 1, 1, tzinfo=dt.timezone.utc),
            sell_mode="online",
            min_price=None,
            max_price=None,
            event_payload={},
            payload_hash="hash",
        )
    ]

    class DummyProvider:
        def fetch_and_parse(self):
            captured["provider_called"] = True
            return fake_events

    sync_runs_calls: list[tuple] = []
    cache_calls: list[str] = []

    class DummySyncRunsRepo:
        def __init__(self, db):
            self.db = db

        def create_running(self, started_at):
            sync_runs_calls.append(("create_running", started_at))
            return 123

        def mark_success(self, **kwargs):
            sync_runs_calls.append(("mark_success", kwargs))

        def mark_failed(self, **kwargs):
            sync_runs_calls.append(("mark_failed", kwargs))

    class DummySyncService:
        def __init__(self, events_current_repo, snapshots_repo):
            captured["repos"] = (events_current_repo, snapshots_repo)

        def sync(self, events, observed_at):
            captured["synced_events"] = events
            return SyncStats(
                events_received=1,
                events_inserted=1,
                events_updated=0,
                events_unchanged=0,
                events_marked_missing=0,
            )

    monkeypatch.setattr("app.worker.tasks.build_event_provider", lambda: DummyProvider())
    monkeypatch.setattr("app.worker.tasks.session_scope", lambda: DummySessionScope())
    monkeypatch.setattr("app.worker.tasks.PostgresEventsCurrentRepository", lambda db: "current-repo")
    monkeypatch.setattr("app.worker.tasks.PostgresEventSnapshotsRepository", lambda db: "snapshots-repo")
    monkeypatch.setattr("app.worker.tasks.PostgresSyncRunsRepository", DummySyncRunsRepo)
    monkeypatch.setattr("app.worker.tasks.EventSyncService", DummySyncService)
    monkeypatch.setattr(
        "app.worker.tasks.get_search_cache",
        lambda: types.SimpleNamespace(bump_version=lambda: cache_calls.append("bump_version")),
    )

    result = sync_events.run(None)

    assert captured["provider_called"] is True
    assert captured["synced_events"] == fake_events
    assert result == {
        "events_received": 1,
        "events_inserted": 1,
        "events_updated": 0,
        "events_unchanged": 0,
        "events_marked_missing": 0,
    }
    assert sync_runs_calls[0][0] == "create_running"
    assert sync_runs_calls[1][0] == "mark_success"
    assert sync_runs_calls[1][1]["events_marked_missing"] == 0
    assert all(call[0] != "mark_failed" for call in sync_runs_calls)
    assert cache_calls == ["bump_version"]


def test_sync_events_marks_failed_when_provider_request_fails(monkeypatch):
    class DummyProvider:
        def fetch_and_parse(self):
            raise RuntimeError("provider down")

    class DummySessionScope:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    sync_runs_calls: list[tuple] = []
    cache_calls: list[str] = []

    class DummySyncRunsRepo:
        def __init__(self, db):
            self.db = db

        def create_running(self, started_at):
            sync_runs_calls.append(("create_running", started_at))
            return 456

        def mark_success(self, **kwargs):
            sync_runs_calls.append(("mark_success", kwargs))

        def mark_failed(self, **kwargs):
            sync_runs_calls.append(("mark_failed", kwargs))

    monkeypatch.setattr("app.worker.tasks.build_event_provider", lambda: DummyProvider())
    monkeypatch.setattr("app.worker.tasks.session_scope", lambda: DummySessionScope())
    monkeypatch.setattr("app.worker.tasks.PostgresSyncRunsRepository", DummySyncRunsRepo)
    monkeypatch.setattr(
        "app.worker.tasks.get_search_cache",
        lambda: types.SimpleNamespace(bump_version=lambda: cache_calls.append("bump_version")),
    )

    with pytest.raises(RuntimeError, match="provider down"):
        sync_events.run(None)

    assert sync_runs_calls[0][0] == "create_running"
    assert sync_runs_calls[1][0] == "mark_failed"
    assert all(call[0] != "mark_success" for call in sync_runs_calls)
    assert cache_calls == []


def test_sync_events_does_not_fail_when_cache_bump_fails(monkeypatch):
    class DummyProvider:
        def fetch_and_parse(self):
            return fake_events

    class DummySessionScope:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_events = [
        NormalizedEvent(
            provider_event_id="1:1",
            title="event",
            start_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
            end_at=dt.datetime(2026, 1, 1, 1, tzinfo=dt.timezone.utc),
            sell_mode="online",
            min_price=None,
            max_price=None,
            event_payload={},
            payload_hash="hash",
        )
    ]

    class DummySyncRunsRepo:
        def __init__(self, db):
            self.db = db

        def create_running(self, started_at):
            return 1

        def mark_success(self, **kwargs):
            return None

        def mark_failed(self, **kwargs):
            return None

    class DummySyncService:
        def __init__(self, events_current_repo, snapshots_repo):
            self.events_current_repo = events_current_repo
            self.snapshots_repo = snapshots_repo

        def sync(self, events, observed_at):
            return SyncStats(
                events_received=1,
                events_inserted=1,
                events_updated=0,
                events_unchanged=0,
                events_marked_missing=0,
            )

    monkeypatch.setattr("app.worker.tasks.build_event_provider", lambda: DummyProvider())
    monkeypatch.setattr("app.worker.tasks.session_scope", lambda: DummySessionScope())
    monkeypatch.setattr("app.worker.tasks.PostgresEventsCurrentRepository", lambda db: "current-repo")
    monkeypatch.setattr("app.worker.tasks.PostgresEventSnapshotsRepository", lambda db: "snapshots-repo")
    monkeypatch.setattr("app.worker.tasks.PostgresSyncRunsRepository", DummySyncRunsRepo)
    monkeypatch.setattr("app.worker.tasks.EventSyncService", DummySyncService)
    monkeypatch.setattr(
        "app.worker.tasks.get_search_cache",
        lambda: types.SimpleNamespace(bump_version=lambda: (_ for _ in ()).throw(RuntimeError("redis down"))),
    )

    result = sync_events.run(None)
    assert result["events_received"] == 1


def test_sync_events_re_raises_original_error_when_mark_failed_also_fails(monkeypatch):
    class DummyProvider:
        def fetch_and_parse(self):
            raise RuntimeError("provider down")

    class DummySessionScope:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummySyncRunsRepo:
        def __init__(self, db):
            self.db = db

        def create_running(self, started_at):
            return 1

        def mark_success(self, **kwargs):
            return None

        def mark_failed(self, **kwargs):
            raise RuntimeError("cannot mark failed")

    monkeypatch.setattr("app.worker.tasks.build_event_provider", lambda: DummyProvider())
    monkeypatch.setattr("app.worker.tasks.session_scope", lambda: DummySessionScope())
    monkeypatch.setattr("app.worker.tasks.PostgresSyncRunsRepository", DummySyncRunsRepo)

    with pytest.raises(RuntimeError, match="provider down"):
        sync_events.run(None)
