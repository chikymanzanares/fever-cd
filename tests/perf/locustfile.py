from __future__ import annotations

import json
from pathlib import Path
from random import choice

from locust import HttpUser, between, task


QUERIES_PATH = Path(__file__).parent / "data" / "queries.json"


def _load_queries() -> list[dict[str, str]]:
    raw = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("queries.json must contain a non-empty array")
    return raw


QUERIES = _load_queries()


class SearchUser(HttpUser):
    # Short pause to simulate realistic traffic pacing.
    wait_time = between(0.1, 0.5)

    @task
    def search(self) -> None:
        params = choice(QUERIES)
        with self.client.get("/search", params=params, name="/search", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"unexpected status {response.status_code}")
                return
            body = response.json()
            if body.get("error") is not None:
                response.failure("error field is not null")
