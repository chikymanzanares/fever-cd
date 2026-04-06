SHELL := /bin/sh
-include .env
export
POSTGRES_USER ?= fever
POSTGRES_PASSWORD ?= fever
POSTGRES_DB ?= fever
POSTGRES_PORT ?= 5432
REDIS_PORT ?= 6379
DEV_TEST_IMAGE ?= juanjo-velasco-dev
DOCKERHUB_USER ?= chikymanzanares
API_IMAGE_NAME ?= fever
API_IMAGE_TAG ?= latest
API_IMAGE ?= $(DOCKERHUB_USER)/$(API_IMAGE_NAME):$(API_IMAGE_TAG)
VERBOSE ?= 0

ifeq ($(VERBOSE),1)
QUIET_REDIR =
else
QUIET_REDIR = >/dev/null
endif

.PHONY: help up up-logs down build rebuild logs logs-celery ps migrate db-shell db-psql test-build test-unit test-integration test-e2e test-perf test-perf-cold test-perf-warm test-all install-hooks run-pre-commit image-build image-push run

help:
	@echo "Targets:"
	@echo "  make up       # Start services (build if needed)"
	@echo "  make down     # Stop services"
	@echo "  make build    # Build images"
	@echo "  make rebuild  # Build images without cache"
	@echo "  make logs     # Tail logs"
	@echo "  make logs-celery # Tail celery-worker and celery-beat logs"
	@echo "  make up-logs  # Start detached and follow logs"
	@echo "  make ps       # Show container status"
	@echo "  make migrate  # Run Alembic migrations (upgrade head)"
	@echo "  make db-shell # Open shell inside Postgres container"
	@echo "  make db-psql  # Open psql using POSTGRES_USER/POSTGRES_DB from .env"
	@echo "  make test-build # Build/rebuild dev test image"
	@echo "  make test-unit # Run all unit tests in dev container"
	@echo "  make test-integration # API/integration tests (needs db+redis up, ports published)"
	@echo "  make test-e2e  # Run real-stack e2e (db+redis+celery+api)"
	@echo "  make test-e2e VERBOSE=1  # Same as above with detailed logs"
	@echo "  make test-perf # Run Locust benchmark against /search"
	@echo "  make test-perf-cold # Flush redis then benchmark /search"
	@echo "  make test-perf-warm # Warm /search cache then benchmark"
	@echo "  make test-all  # Run test-unit, test-integration, and test-e2e"
	@echo "  make install-hooks # Install git pre-commit hook for unit tests"
	@echo "  make run-pre-commit # Run local pre-commit hook now"
	@echo "  make image-build # Build API image ($(API_IMAGE))"
	@echo "  make image-push  # Push API image ($(API_IMAGE))"
	@echo "  make run      # Alias for up"

up:
	docker compose up --build

up-logs:
	docker compose up -d --build && docker compose logs -f --tail=200

down:
	docker compose down

build:
	docker compose build

rebuild:
	docker compose build --no-cache

logs:
	docker compose logs -f --tail=200

logs-celery:
	docker compose logs -f celery-worker celery-beat

migrate:
	docker compose run --rm migrate

db-shell:
	docker compose exec db sh

db-psql:
	docker compose exec db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)
# psql -U $POSTGRES_USER -d $POSTGRES_DB

test-build:
	docker build --target development -t $(DEV_TEST_IMAGE) .

test-unit:
	@docker image inspect $(DEV_TEST_IMAGE) >/dev/null 2>&1 || $(MAKE) test-build
	docker run --rm -v "$$(pwd):/app" -w /app $(DEV_TEST_IMAGE) pytest tests/unit -q

test-integration:
	@docker image inspect $(DEV_TEST_IMAGE) >/dev/null 2>&1 || $(MAKE) test-build
	docker run --rm \
	  -v "$$(pwd):/app" -w /app \
	  --add-host=host.docker.internal:host-gateway \
	  -e DATABASE_URL=postgresql+psycopg2://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@host.docker.internal:$(POSTGRES_PORT)/$(POSTGRES_DB) \
	  -e REDIS_URL=redis://host.docker.internal:$(REDIS_PORT)/0 \
	  $(DEV_TEST_IMAGE) pytest tests/integration -q

test-e2e:
	@set -e; \
	cleanup() { \
		docker compose exec -T db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "TRUNCATE TABLE event_snapshots, events_current, sync_runs RESTART IDENTITY CASCADE;" $(QUIET_REDIR); \
	}; \
	trap cleanup EXIT; \
	docker compose up -d db redis migrate api celery-worker celery-beat $(QUIET_REDIR); \
	cleanup; \
	docker compose exec -T celery-worker celery -A app.worker.celery_app:celery_app call app.worker.tasks.sync_events $(QUIET_REDIR); \
	i=0; \
	count=0; \
	until [ $$i -ge 30 ]; do \
		count=$$(docker compose exec -T db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -tAc "SELECT count(*) FROM events_current;" | tr -d '[:space:]'); \
		if [ "$$count" -ge 2 ] 2>/dev/null; then break; fi; \
		i=$$((i+1)); \
		sleep 1; \
	done; \
	test "$$count" -ge 2; \
	has_291=$$(docker compose exec -T db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -tAc "SELECT count(*) FROM events_current WHERE provider_event_id='291:291';" | tr -d '[:space:]'); \
	has_1591=$$(docker compose exec -T db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -tAc "SELECT count(*) FROM events_current WHERE provider_event_id='1591:1642';" | tr -d '[:space:]'); \
	has_444=$$(docker compose exec -T db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -tAc "SELECT count(*) FROM events_current WHERE provider_event_id='444:1642';" | tr -d '[:space:]'); \
	test "$$has_291" -ge 1; \
	test "$$has_1591" -ge 1; \
	test "$$has_444" -eq 0; \
	search_json=$$(curl -s "http://localhost:$(API_PORT)/search?starts_at=2020-01-01T00:00:00Z&ends_at=2035-01-01T00:00:00Z"); \
	SEARCH_JSON="$$search_json" python3 -c "import json, os; b=json.loads(os.environ['SEARCH_JSON']); assert b.get('error') is None; events=b.get('data',{}).get('events',[]); titles={e.get('title') for e in events}; assert 'Camela en concierto' in titles; assert 'Los Morancos' in titles; assert 'Tributo a Juanito Valderrama' not in titles"; \
	echo "real-stack e2e passed"

test-perf:
	@docker image inspect $(DEV_TEST_IMAGE) >/dev/null 2>&1 || $(MAKE) test-build
	docker run --rm -v "$$(pwd):/app" -w /app $(DEV_TEST_IMAGE) \
		locust -f tests/perf/locustfile.py --headless --users 30 --spawn-rate 10 --run-time 30s \
		--host http://host.docker.internal:$(API_PORT)

test-perf-cold:
	docker compose exec -T redis redis-cli FLUSHALL
	$(MAKE) test-perf

test-perf-warm:
	@set -e; \
	for i in 1 2 3 4 5; do \
		curl -s "http://localhost:$(API_PORT)/search?starts_at=2020-01-01T00:00:00Z&ends_at=2035-01-01T00:00:00Z" >/dev/null; \
	done
	$(MAKE) test-perf

test-all: test-unit test-integration test-e2e

install-hooks:
	@test -d .git || (echo "Not a git repository"; exit 1)
	@mkdir -p .git/hooks
	@printf '%s\n' '#!/bin/sh' 'set -e' '' 'echo "[pre-commit] Running unit tests..."' 'make test-unit' > .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "Installed .git/hooks/pre-commit"

run-pre-commit:
	@test -x .git/hooks/pre-commit || (echo "Hook not installed. Run: make install-hooks"; exit 1)
	@.git/hooks/pre-commit

# ---------------------------------------------------------------------------
# Docker image commands (API only)
# ---------------------------------------------------------------------------
image-build:
	docker build --platform linux/amd64 --target production -t $(API_IMAGE) .

image-push:
	docker push $(API_IMAGE)

run: up

