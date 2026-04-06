from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from app.domain.events import NormalizedEvent

logger = logging.getLogger(__name__)
PROVIDER_LOCAL_TIMEZONE = ZoneInfo("Europe/Madrid")


def _parse_iso8601(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=PROVIDER_LOCAL_TIMEZONE).astimezone(dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _parse_price(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _payload_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_provider_xml(xml_text: str) -> list[NormalizedEvent]:
    root = ET.fromstring(xml_text)
    normalized: list[NormalizedEvent] = []

    for base_plan in root.findall(".//base_plan"):
        base_plan_id = base_plan.attrib.get("base_plan_id", "")
        base_title = base_plan.attrib.get("title", "")
        base_sell_mode = base_plan.attrib.get("sell_mode", "")

        for plan in base_plan.findall("./plan"):
            plan_id = plan.attrib.get("plan_id", "")
            provider_event_id = f"{base_plan_id}:{plan_id}" if base_plan_id else plan_id

            try:
                start_at = _parse_iso8601(plan.attrib["plan_start_date"])
                end_at = _parse_iso8601(plan.attrib["plan_end_date"])
            except (KeyError, ValueError) as exc:
                logger.warning(
                    "normalize_provider_xml skipped invalid plan dates base_plan_id=%s plan_id=%s error=%s",
                    base_plan_id,
                    plan_id,
                    exc,
                )
                continue

            zones_payload: list[dict[str, str]] = []
            prices: list[Decimal] = []
            for zone in plan.findall("./zone"):
                zone_data = dict(zone.attrib)
                zones_payload.append(zone_data)
                zone_price = _parse_price(zone.attrib.get("price"))
                if zone_price is not None:
                    prices.append(zone_price)

            min_price = min(prices) if prices else None
            max_price = max(prices) if prices else None
            payload = {
                "base_plan": dict(base_plan.attrib),
                "plan": dict(plan.attrib),
                "zones": zones_payload,
            }

            normalized.append(
                NormalizedEvent(
                    provider_event_id=provider_event_id,
                    title=base_title,
                    start_at=start_at,
                    end_at=end_at,
                    sell_mode=base_sell_mode,
                    min_price=min_price,
                    max_price=max_price,
                    event_payload=payload,
                    payload_hash=_payload_hash(payload),
                )
            )

    return normalized
