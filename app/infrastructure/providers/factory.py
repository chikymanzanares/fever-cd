from __future__ import annotations

import os

from app.domain.providers.event_provider import EventProvider
from app.infrastructure.providers.fever.provider import FeverXmlEventProvider

PROVIDER_BUILDERS: dict[str, type[EventProvider]] = {
    "fever": FeverXmlEventProvider,
    "fever2": FeverXmlEventProvider,
}


def build_event_provider() -> EventProvider:
    provider_name = os.getenv("PROVIDER_NAME", "fever").strip().lower()
    provider_cls = PROVIDER_BUILDERS.get(provider_name)
    if provider_cls is not None:
        return provider_cls()
    raise ValueError(f"Unsupported provider: {provider_name}")
