from __future__ import annotations

from decimal import Decimal

from app.infrastructure.providers.fever.xml_normalizer import normalize_provider_xml


def test_normalize_provider_xml_returns_expected_events_and_prices():
    xml = """\
<planList>
  <output>
    <base_plan base_plan_id="291" sell_mode="online" title="Camela en concierto">
      <plan plan_start_date="2021-06-30T21:00:00" plan_end_date="2021-06-30T21:30:00" plan_id="291">
        <zone zone_id="40" capacity="200" price="20.00" name="Platea" numbered="true" />
        <zone zone_id="38" capacity="0" price="15.00" name="Grada 2" numbered="false" />
        <zone zone_id="30" capacity="80" price="30.00" name="A28" numbered="true" />
      </plan>
    </base_plan>
  </output>
</planList>
"""
    events = normalize_provider_xml(xml)

    assert len(events) == 1
    event = events[0]
    assert event.provider_event_id == "291:291"
    assert event.title == "Camela en concierto"
    assert event.sell_mode == "online"
    assert event.min_price == Decimal("15.00")
    assert event.max_price == Decimal("30.00")


def test_normalize_provider_xml_skips_invalid_dates():
    xml = """\
<planList>
  <output>
    <base_plan base_plan_id="444" sell_mode="offline" title="Tributo a Juanito Valderrama">
      <plan plan_start_date="2021-09-31T20:00:00" plan_end_date="2021-09-31T20:00:00" plan_id="1642">
        <zone zone_id="7" capacity="22" price="65.00" name="Amfiteatre" numbered="false" />
      </plan>
    </base_plan>
  </output>
</planList>
"""
    events = normalize_provider_xml(xml)
    assert events == []


def test_normalize_provider_xml_payload_hash_is_stable():
    xml = """\
<planList>
  <output>
    <base_plan base_plan_id="1591" sell_mode="online" title="Los Morancos">
      <plan plan_start_date="2021-07-31T20:00:00" plan_end_date="2021-07-31T21:00:00" plan_id="1642">
        <zone zone_id="186" capacity="12" price="65.00" name="Amfiteatre" numbered="false" />
      </plan>
    </base_plan>
  </output>
</planList>
"""
    first = normalize_provider_xml(xml)
    second = normalize_provider_xml(xml)

    assert len(first) == 1
    assert len(second) == 1
    assert first[0].payload_hash == second[0].payload_hash
