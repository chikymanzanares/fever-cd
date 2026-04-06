from __future__ import annotations

import json
from decimal import Decimal

from app.infrastructure.providers.fever2.json_normalizer import normalize_provider_json


def _sample_plan_list() -> dict:
    return {
        "planList": {
            "version": "1.0",
            "output": {
                "base_plan": [
                    {
                        "base_plan_id": "291",
                        "sell_mode": "online",
                        "title": "Camela en concierto",
                        "plan": [
                            {
                                "plan_start_date": "2021-06-30T21:00:00",
                                "plan_end_date": "2021-06-30T22:00:00",
                                "plan_id": "291",
                                "sell_from": "2020-07-01T00:00:00",
                                "sell_to": "2021-06-30T20:00:00",
                                "sold_out": "false",
                                "zone": [
                                    {
                                        "zone_id": "40",
                                        "capacity": "243",
                                        "price": "20.00",
                                        "name": "Platea",
                                        "numbered": "true",
                                    },
                                    {
                                        "zone_id": "38",
                                        "capacity": "100",
                                        "price": "15.00",
                                        "name": "Grada 2",
                                        "numbered": "false",
                                    },
                                ],
                            }
                        ],
                    }
                ]
            },
        }
    }


def test_normalize_provider_json_returns_expected_events_and_prices():
    text = json.dumps(_sample_plan_list())
    events = normalize_provider_json(text)

    assert len(events) == 1
    event = events[0]
    assert event.provider_event_id == "291:291"
    assert event.title == "Camela en concierto"
    assert event.sell_mode == "online"
    assert event.min_price == Decimal("15.00")
    assert event.max_price == Decimal("20.00")
    assert event.event_payload["zones"][0]["name"] == "Platea"


def test_normalize_provider_json_skips_invalid_dates():
    bad = {
        "planList": {
            "output": {
                "base_plan": [
                    {
                        "base_plan_id": "444",
                        "sell_mode": "offline",
                        "title": "Bad dates",
                        "plan": [
                            {
                                "plan_start_date": "2021-09-31T20:00:00",
                                "plan_end_date": "2021-09-31T20:00:00",
                                "plan_id": "1642",
                                "zone": [{"zone_id": "7", "price": "65.00", "name": "Amfiteatre"}],
                            }
                        ],
                    }
                ]
            }
        }
    }
    events = normalize_provider_json(json.dumps(bad))
    assert events == []


def test_normalize_provider_json_payload_hash_is_stable():
    text = json.dumps(_sample_plan_list())
    first = normalize_provider_json(text)
    second = normalize_provider_json(text)
    assert len(first) == 1
    assert first[0].payload_hash == second[0].payload_hash


def test_normalize_provider_json_without_planList_wrapper():
    root = {
        "output": {
            "base_plan": [
                {
                    "base_plan_id": "1",
                    "sell_mode": "online",
                    "title": "Solo output",
                    "plan": {
                        "plan_start_date": "2021-06-30T21:00:00",
                        "plan_end_date": "2021-06-30T22:00:00",
                        "plan_id": "1",
                        "zone": {"zone_id": "1", "price": "10.00", "name": "Z"},
                    },
                }
            ]
        }
    }
    events = normalize_provider_json(json.dumps(root))
    assert len(events) == 1
    assert events[0].provider_event_id == "1:1"


def test_normalize_provider_json_single_zone_object():
    root = {
        "planList": {
            "output": {
                "base_plan": {
                    "base_plan_id": "2",
                    "sell_mode": "online",
                    "title": "One zone dict",
                    "plan": {
                        "plan_start_date": "2021-06-30T21:00:00",
                        "plan_end_date": "2021-06-30T22:00:00",
                        "plan_id": "2",
                        "zone": {"zone_id": "1", "price": "12.50", "name": "A"},
                    },
                }
            }
        }
    }
    events = normalize_provider_json(json.dumps(root))
    assert len(events) == 1
    assert events[0].min_price == Decimal("12.50")


def test_normalize_provider_json_multiple_plans_same_base():
    root = {
        "planList": {
            "output": {
                "base_plan": [
                    {
                        "base_plan_id": "322",
                        "sell_mode": "online",
                        "title": "Dos fechas",
                        "plan": [
                            {
                                "plan_start_date": "2021-02-10T20:00:00",
                                "plan_end_date": "2021-02-10T21:30:00",
                                "plan_id": "1642",
                                "zone": [{"zone_id": "311", "price": "55.00", "name": "A42"}],
                            },
                            {
                                "plan_start_date": "2021-02-11T20:00:00",
                                "plan_end_date": "2021-02-11T21:30:00",
                                "plan_id": "1643",
                                "zone": [{"zone_id": "311", "price": "55.00", "name": "A42"}],
                            },
                        ],
                    }
                ]
            }
        }
    }
    events = normalize_provider_json(json.dumps(root))
    assert len(events) == 2
    assert {e.provider_event_id for e in events} == {"322:1642", "322:1643"}
