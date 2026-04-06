from __future__ import annotations

import pytest

from app.domain.events import NormalizedEvent
from app.domain.providers.event_provider import EventProvider
from app.infrastructure.providers import factory
from app.infrastructure.providers.factory import build_event_provider
from app.infrastructure.providers.fever.provider import FeverXmlEventProvider


def test_build_event_provider_returns_fever_by_default(monkeypatch):
    monkeypatch.delenv("PROVIDER_NAME", raising=False)
    provider = build_event_provider()
    assert isinstance(provider, FeverXmlEventProvider)


def test_build_event_provider_raises_for_unknown_provider(monkeypatch):
    monkeypatch.setenv("PROVIDER_NAME", "unknown")
    with pytest.raises(ValueError, match="Unsupported provider: unknown"):
        build_event_provider()


def test_build_event_provider_returns_xml_provider_for_fever2(monkeypatch):
    monkeypatch.setenv("PROVIDER_NAME", "fever2")
    provider = build_event_provider()
    assert isinstance(provider, FeverXmlEventProvider)


def test_build_event_provider_supports_provider_b_registration(monkeypatch):
    class ProviderB(EventProvider):
        @property
        def provider_name(self) -> str:
            return "provider_b"

        def fetch_raw(self) -> str:
            return '{"events":[]}'

        def parse(self, raw: str) -> list[NormalizedEvent]:
            return []

    monkeypatch.setitem(factory.PROVIDER_BUILDERS, "provider_b", ProviderB)
    monkeypatch.setenv("PROVIDER_NAME", "provider_b")

    provider = build_event_provider()
    assert isinstance(provider, ProviderB)
