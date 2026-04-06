from __future__ import annotations

import os
from pathlib import Path

import httpx

from app.domain.events import NormalizedEvent
from app.domain.providers.event_provider import EventProvider
from app.infrastructure.providers.fever2.json_normalizer import normalize_provider_json


class FeverJsonEventProvider(EventProvider):
    """planList en JSON (misma forma lógica que el XML Fever). Sin URL fija: cuerpo vía env o fichero."""

    @property
    def provider_name(self) -> str:
        return "fever2"

    def fetch_raw(self) -> str:
        url = os.getenv("FEVER2_PROVIDER_EVENTS_URL", "").strip()
        if url:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.text

        path = os.getenv("FEVER2_JSON_PATH", "").strip()
        if path:
            return Path(path).read_text(encoding="utf-8")

        inline = os.getenv("FEVER2_JSON", "")
        if inline.strip():
            return inline

        raise ValueError(
            "FeverJsonEventProvider: configure FEVER2_PROVIDER_EVENTS_URL, FEVER2_JSON_PATH, or FEVER2_JSON"
        )

    def parse(self, raw: str) -> list[NormalizedEvent]:
        return normalize_provider_json(raw)
