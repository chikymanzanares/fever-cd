from __future__ import annotations

import json
import logging
from typing import Any

from app.domain.events import NormalizedEvent
from app.infrastructure.providers.fever.xml_normalizer import (
    _parse_iso8601,
    _parse_price,
    _payload_hash,
)

logger = logging.getLogger(__name__)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _attr_row(d: dict[str, Any], exclude: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in d.items():
        if k == exclude:
            continue
        out[k] = str(v) if v is not None else ""
    return out


def _extract_base_plans(root: dict[str, Any]) -> list[dict[str, Any]]:
    node: dict[str, Any] = root.get("planList") or root
    if not isinstance(node, dict):
        return []
    out_section = node.get("output") if isinstance(node.get("output"), dict) else node
    if not isinstance(out_section, dict):
        return []
    return _as_list(out_section.get("base_plan"))


def normalize_provider_json(json_text: str) -> list[NormalizedEvent]:
    root = json.loads(json_text)
    if not isinstance(root, dict):
        return []

    normalized: list[NormalizedEvent] = []

    for base_plan in _extract_base_plans(root):
        if not isinstance(base_plan, dict):
            continue
        base_plan_id = str(base_plan.get("base_plan_id", ""))
        base_title = str(base_plan.get("title", ""))
        base_sell_mode = str(base_plan.get("sell_mode", ""))

        for plan in _as_list(base_plan.get("plan")):
            if not isinstance(plan, dict):
                continue
            plan_id = str(plan.get("plan_id", ""))
            provider_event_id = f"{base_plan_id}:{plan_id}" if base_plan_id else plan_id

            try:
                start_at = _parse_iso8601(str(plan["plan_start_date"]))
                end_at = _parse_iso8601(str(plan["plan_end_date"]))
            except (KeyError, ValueError) as exc:
                logger.warning(
                    "normalize_provider_json skipped invalid plan dates base_plan_id=%s plan_id=%s error=%s",
                    base_plan_id,
                    plan_id,
                    exc,
                )
                continue

            zones_payload: list[dict[str, str]] = []
            prices: list = []
            for zone in _as_list(plan.get("zone")):
                if not isinstance(zone, dict):
                    continue
                zone_data = {k: str(v) if v is not None else "" for k, v in zone.items()}
                zones_payload.append(zone_data)
                zone_price = _parse_price(zone_data.get("price"))
                if zone_price is not None:
                    prices.append(zone_price)

            min_price = min(prices) if prices else None
            max_price = max(prices) if prices else None
            payload = {
                "base_plan": _attr_row(base_plan, "plan"),
                "plan": _attr_row(plan, "zone"),
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
