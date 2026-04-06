from __future__ import annotations

import datetime as dt
import logging

from app.application.use_cases.event_sync_service import EventSyncService
from app.domain.repositories.sync_runs_repository import SyncRunsRepository
from app.infrastructure.cache.redis_search_cache_repository import get_search_cache
from app.infrastructure.db.repositories.postgres_event_snapshots_repository import (
    PostgresEventSnapshotsRepository,
)
from app.infrastructure.db.repositories.postgres_events_current_repository import (
    PostgresEventsCurrentRepository,
)
from app.infrastructure.db.repositories.postgres_sync_runs_repository import (
    PostgresSyncRunsRepository,
)
from app.infrastructure.providers.factory import build_event_provider
from app.infrastructure.db.session import session_scope
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.sync_events", bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def sync_events(self) -> dict[str, int]:
    started_at = dt.datetime.now(dt.timezone.utc)
    with session_scope() as db:
        sync_runs_repo: SyncRunsRepository = PostgresSyncRunsRepository(db)
        sync_run_id = sync_runs_repo.create_running(started_at)

    try:
        provider = build_event_provider()
        events = provider.fetch_and_parse()
        logger.info("sync_events normalized %s events", len(events))

        with session_scope() as db:
            current_repo = PostgresEventsCurrentRepository(db)
            snapshots_repo = PostgresEventSnapshotsRepository(db)
            sync_service = EventSyncService(current_repo, snapshots_repo)
            stats = sync_service.sync(events, observed_at=dt.datetime.now(dt.timezone.utc))

        finished_at = dt.datetime.now(dt.timezone.utc)
        with session_scope() as db:
            sync_runs_repo: SyncRunsRepository = PostgresSyncRunsRepository(db)
            sync_runs_repo.mark_success(
                sync_run_id=sync_run_id,
                finished_at=finished_at,
                events_received=stats.events_received,
                events_inserted=stats.events_inserted,
                events_updated=stats.events_updated,
                events_unchanged=stats.events_unchanged,
                events_marked_missing=stats.events_marked_missing,
            )
        try:
            # Invalidate all cached search ranges atomically by bumping version namespace.
            get_search_cache().bump_version()
        except Exception:
            logger.exception("sync_events could not bump search cache version")

        logger.info(
            "sync_events stats received=%s inserted=%s updated=%s unchanged=%s missing=%s",
            stats.events_received,
            stats.events_inserted,
            stats.events_updated,
            stats.events_unchanged,
            stats.events_marked_missing,
        )
        return {
            "events_received": stats.events_received,
            "events_inserted": stats.events_inserted,
            "events_updated": stats.events_updated,
            "events_unchanged": stats.events_unchanged,
            "events_marked_missing": stats.events_marked_missing,
        }
    except Exception as exc:
        finished_at = dt.datetime.now(dt.timezone.utc)
        try:
            with session_scope() as db:
                sync_runs_repo: SyncRunsRepository = PostgresSyncRunsRepository(db)
                sync_runs_repo.mark_failed(
                    sync_run_id=sync_run_id,
                    finished_at=finished_at,
                    error_message=str(exc),
                )
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("sync_events could not mark sync_run as failed")
        raise

