# Performance Benchmark (`/search`)

This folder contains Locust-based benchmarks for the FastAPI `/search` endpoint.

## Prerequisites

- API stack running (`db`, `redis`, `api`, and data already synchronized).
- Dev image built with `locust` installed via `requirements-dev.txt`.

## Quick Run

```bash
make test-perf
```

## Compare Cold vs Warm Cache

```bash
make test-perf-cold
make test-perf-warm
```

- `test-perf-cold` clears Redis before the run.
- `test-perf-warm` preloads a common `/search` range before the run.

## Custom Run

```bash
docker run --rm -v "$(pwd):/app" -w /app juanjo-velasco-dev \
  locust -f tests/perf/locustfile.py --headless \
  --users 100 --spawn-rate 20 --run-time 2m \
  --host http://host.docker.internal:8000
```

## Query Workload

The request mix is loaded from `tests/perf/data/queries.json`.

## Latest Results

Measured with `30` users for `30s`:

- cold cache: `2831` requests, `0.00%` failures, ~`95.18 req/s`, avg `8ms`, p95 `20ms`, p99 `91ms`
- warm cache: `2807` requests, `0.00%` failures, ~`94.21 req/s`, avg `6ms`, p95 `15ms`, p99 `64ms`

Conclusion: warm cache improves latency percentiles (especially p95/p99) while throughput at this load level remains similar.
