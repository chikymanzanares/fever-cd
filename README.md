# Fever Provider Integration

This repository implements the Fever backend challenge: ingest provider XML feeds asynchronously and expose a single public API endpoint, `/search`, aligned with the requested contract.

## Quick Start

### Requirements
- Docker
- Docker Compose

### Setup Environment
- Copy `.env.example` to `.env` before running the stack:
  - `cp .env.example .env`

### Run
- `make up` to start the stack
- `make down` to stop it

### First Run Validation
- `make up`
- `make test-e2e`
- optional full validation:
  - `make test-unit`
  - `make test-all`

### Tests
- `make test-unit` — unit tests in the dev image
- `make test-integration` — FastAPI `/search` via `TestClient` (needs Postgres/Redis reachable; see Makefile)
- `make test-e2e` — **end-to-end** on the real stack (compose + Celery sync + DB checks + `/search`); this is the main E2E
- `make test-e2e VERBOSE=1`
- `make test-all` — unit + integration + shell E2E above
- `make test-perf-cold`
- `make test-perf-warm`

### Commit Gate (git pre-commit hook)
- Install hooks once: `make install-hooks`
- Optional manual check: `make run-pre-commit`
- From that point, every `git commit` runs unit tests first (`make test-unit`).
- If unit tests fail, the commit is blocked.

## Performance Benchmark (`/search`)

Perf benchmark setup, commands, and latest measurements are documented in [`tests/perf/README.md`](./tests/perf/README.md).

## Public API

- `GET /search`
  - query params: `starts_at` and `ends_at` (optional, date-time)
  - response shape:
    - success: `{ "data": { "events": [...] }, "error": null }`
    - bad request: `{ "data": null, "error": { "code": "...", "message": "..." } }`

The endpoint serves only plans that were ever online, including historical plans no longer present in the latest provider feed.

### Time Rendering Mode

`/search` supports two rendering modes for `start_date/start_time/end_date/end_time` using `SEARCH_TIME_MODE`:
- `local` (default): render in provider local timezone (`Europe/Madrid`)
- `utc`: render in UTC

Example: a provider value interpreted as local `20:00:00` is rendered as `18:00:00` in `utc` mode during summer (UTC+2 offset).

## Architecture Summary

- `app/domain`: entities + repository contracts
- `app/application`: use cases (`EventSyncService`)
- `app/infrastructure`: Postgres repositories, Redis cache, XML normalization
- `app/worker`: Celery task orchestration
- `app/api`: FastAPI route for `/search`

Sync is decoupled from reads:
- background sync (Celery + Redis broker) ingests provider XML into Postgres
- `/search` reads from local DB and uses Redis cache for hot ranges

Detailed architecture and runtime notes: see [`ARCHITECTURE.md`](./ARCHITECTURE.md).

## Design Decisions (Short)

- Asynchronous ingestion to isolate search latency from provider instability.
- Historical availability via `ever_online` and persisted snapshots.
- Per-run audit trail in `sync_runs` for success/failure observability.
- Cache invalidation by namespace version bump (`search:version`) on successful sync.
- Contract-focused error mapping (`400`) for malformed query params.

## AI Usage

AI agents were used to accelerate implementation and test authoring. All generated changes were reviewed, adjusted, and validated through unit and e2e tests before acceptance.

## Essential Next Steps

- **Observability:** add metrics/tracing and dashboards using Prometheus + Grafana (API latency, cache hit ratio, sync duration, sync failures, DB query timings).
- **Authorization:** protect public/internal endpoints with JWT-based authentication and role-based access rules where needed.
- **CI/CD:** add automated pipelines for lint/tests/build, image publishing, and controlled deployments across environments.
- **Transport benchmark:** implement an equivalent gRPC entrypoint for search and compare gRPC vs FastAPI performance using `ghz` (same dataset and traffic profiles for a fair A/B comparison).

## Original Challenge Statement

The original challenge text is preserved in [`CHALLENGE.md`](./CHALLENGE.md).
