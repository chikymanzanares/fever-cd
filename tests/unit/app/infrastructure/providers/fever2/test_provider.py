from __future__ import annotations

import datetime as dt

import pytest

from app.domain.events import NormalizedEvent
from app.infrastructure.providers.fever2.provider import FeverJsonEventProvider


def test_fever_json_provider_name():
    assert FeverJsonEventProvider().provider_name == "fever2"


def test_fever_json_fetch_raw_from_env_inline(monkeypatch):
    monkeypatch.setenv("FEVER2_JSON", '{"planList":{"output":{"base_plan":[]}}}')
    monkeypatch.delenv("FEVER2_JSON_PATH", raising=False)
    monkeypatch.delenv("FEVER2_PROVIDER_EVENTS_URL", raising=False)
    raw = FeverJsonEventProvider().fetch_raw()
    assert "base_plan" in raw


def test_fever_json_fetch_raw_from_file(monkeypatch, tmp_path):
    p = tmp_path / "events.json"
    p.write_text('{"planList":{"output":{"base_plan":[]}}}', encoding="utf-8")
    monkeypatch.delenv("FEVER2_JSON", raising=False)
    monkeypatch.delenv("FEVER2_PROVIDER_EVENTS_URL", raising=False)
    monkeypatch.setenv("FEVER2_JSON_PATH", str(p))
    raw = FeverJsonEventProvider().fetch_raw()
    assert "base_plan" in raw


def test_fever_json_fetch_raw_prefers_url_over_path_and_inline(monkeypatch, tmp_path):
    p = tmp_path / "ignored.json"
    p.write_text('{"planList":{"output":{"base_plan":[]}}}', encoding="utf-8")
    monkeypatch.setenv("FEVER2_JSON", '{"x":1}')
    monkeypatch.setenv("FEVER2_JSON_PATH", str(p))

    class DummyResponse:
        text = '{"planList":{"output":{"base_plan":[]}}}'
        status_code = 200

        def raise_for_status(self):
            return None

    class DummyClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url):
            assert url == "https://example.com/plan.json"
            return DummyResponse()

    monkeypatch.setattr("app.infrastructure.providers.fever2.provider.httpx.Client", DummyClient)
    monkeypatch.setenv("FEVER2_PROVIDER_EVENTS_URL", "https://example.com/plan.json")

    raw = FeverJsonEventProvider().fetch_raw()
    assert "base_plan" in raw


def test_fever_json_provider_parse_delegates_to_json_normalizer(monkeypatch):
    expected = [
        NormalizedEvent(
            provider_event_id="1:1",
            title="event",
            start_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
            end_at=dt.datetime(2026, 1, 1, 1, tzinfo=dt.timezone.utc),
            sell_mode="online",
            min_price=None,
            max_price=None,
            event_payload={},
            payload_hash="h",
        )
    ]

    monkeypatch.setattr(
        "app.infrastructure.providers.fever2.provider.normalize_provider_json",
        lambda raw: expected,
    )
    provider = FeverJsonEventProvider()
    assert provider.parse("{}") == expected


def test_fever_json_fetch_raw_raises_when_unconfigured(monkeypatch):
    monkeypatch.delenv("FEVER2_JSON", raising=False)
    monkeypatch.delenv("FEVER2_JSON_PATH", raising=False)
    monkeypatch.delenv("FEVER2_PROVIDER_EVENTS_URL", raising=False)
    with pytest.raises(ValueError, match="FEVER2_PROVIDER_EVENTS_URL"):
        FeverJsonEventProvider().fetch_raw()
