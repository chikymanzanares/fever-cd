from __future__ import annotations

import os

import httpx

from app.domain.events import NormalizedEvent
from app.domain.providers.event_provider import EventProvider
from app.infrastructure.providers.fever.xml_normalizer import normalize_provider_xml


class FeverXmlEventProvider(EventProvider):
    @property
    def provider_name(self) -> str:
        return "fever"

    def fetch_raw(self) -> str:
        provider_url = os.getenv("PROVIDER_EVENTS_URL", "https://provider.code-challenge.feverup.com/api/events")
        with httpx.Client(timeout=10.0) as client:
            response = client.get(provider_url)
            response.raise_for_status()
            return response.text

    def parse(self, raw: str) -> list[NormalizedEvent]:
        return normalize_provider_xml(raw)
