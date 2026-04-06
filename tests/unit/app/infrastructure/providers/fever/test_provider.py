from __future__ import annotations

import datetime as dt

from app.domain.events import NormalizedEvent
from app.infrastructure.providers.fever.provider import FeverXmlEventProvider


def test_fever_provider_fetch_raw_uses_http_client(monkeypatch):
    class DummyResponse:
        text = "<planList><output /></planList>"

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
            return DummyResponse()

    monkeypatch.setattr("app.infrastructure.providers.fever.provider.httpx.Client", DummyClient)
    monkeypatch.setenv("PROVIDER_EVENTS_URL", "https://example.com/events.xml")

    provider = FeverXmlEventProvider()
    raw = provider.fetch_raw()
    assert raw == "<planList><output /></planList>"


def test_fever_provider_parse_delegates_to_xml_normalizer(monkeypatch):
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

    monkeypatch.setattr("app.infrastructure.providers.fever.provider.normalize_provider_xml", lambda raw: expected)
    provider = FeverXmlEventProvider()
    assert provider.parse("<xml/>") == expected
