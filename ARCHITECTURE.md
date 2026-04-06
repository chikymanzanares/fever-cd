# Architecture and Runtime Guide

## How To Start The App

### Requirements
- Docker
- Docker Compose

### Main Commands
- `make up` - start full stack in foreground
- `make up-logs` - start detached and follow logs
- `make down` - stop stack
- `make migrate` - run Alembic migrations
- `make logs` - tail all container logs
- `make logs-celery` - tail worker/beat logs

### Testing Commands
- `make test-unit` - unit tests in dev container
- `make test-integration` - API/integration tests (`TestClient`; needs DB/Redis on host ports)
- `make test-e2e` - **real-stack E2E** (shell: compose, Celery `sync_events`, psql, curl `/search`)
- `make test-e2e VERBOSE=1` - same with verbose shell output
- `make test-all` - unit + integration + shell E2E

## System Components

- `api` (FastAPI)
  - endpoint: `/search`
  - reads from Postgres and uses Redis cache for `/search`
- `celery-worker`
  - executes `app.worker.tasks.sync_events`
- `celery-beat`
  - schedules sync periodically (60s)
- `redis`
  - Celery broker/result backend
  - search response cache
- `db` (Postgres)
  - event persistence and sync run audit
- `migrate`
  - applies DB schema migrations

## Architecture Layers

- `app/domain`
  - core contracts and entities
  - repository interfaces (ABCs)
- `app/application`
  - use cases (`EventSyncService`)
- `app/infrastructure`
  - adapters: Postgres repositories, Redis cache, XML normalization
- `app/api`
  - HTTP routes and response mapping
- `app/worker`
  - task orchestration for sync

## Data Model Overview

- `events_current`
  - current view of provider events
  - includes `ever_online` and `is_present_in_latest_feed`
- `event_snapshots`
  - append-like history of distinct payload hashes over time
- `sync_runs`
  - per-sync execution audit (`running/success/failed`, stats, errors)

## Sync Flow

1. Celery beat triggers `sync_events`.
2. Worker fetches provider XML.
3. XML normalizer converts to `NormalizedEvent`.
4. `EventSyncService` applies four cases:
   - new event
   - changed event
   - unchanged event
   - missing from latest feed
5. Repositories persist to `events_current` and `event_snapshots`.
6. `sync_runs` is updated with success/failure and counters.
7. Search cache namespace version is bumped on successful sync.

## Search Flow (`/search`)

1. Validate optional `starts_at`/`ends_at`.
2. Build cache key using current cache version + time range.
3. Cache hit returns immediately (`X-Search-Cache: HIT`).
4. Cache miss queries Postgres, maps response, stores in Redis (`X-Search-Cache: MISS`).
5. Response follows contract:
   - `data.events`
   - `error` (null on success)

## Cache Strategy

- Global version key: `search:version`
- Data keys: `search:v{version}:starts_at=...:ends_at=...`
- Invalidation: bump version on successful sync (no mass delete needed)
- TTL keeps short-term hot ranges fast

## E2E Strategy

- Real-stack E2E runs with Docker Compose services.
- Test cleans DB before and after execution.
- Verifies:
  - Celery-triggered sync writes expected DB rows
  - `/search` returns expected online events
  - `sync_runs` captures success and failure scenarios
  - cache behavior can be observed via response header
