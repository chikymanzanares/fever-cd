from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class NormalizedEvent:
    provider_event_id: str
    title: str
    start_at: dt.datetime
    end_at: dt.datetime
    sell_mode: str
    min_price: Decimal | None
    max_price: Decimal | None
    event_payload: dict[str, Any]
    payload_hash: str

