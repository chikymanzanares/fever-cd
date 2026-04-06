from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.domain.repositories.search_cache_repository import SearchCacheRepository
from app.infrastructure.db.models import EventCurrent

UUID_NAMESPACE = "fever-provider-event"
SEARCH_CACHE_TTL_SECONDS = 60
SEARCH_LOCAL_TIMEZONE = ZoneInfo("Europe/Madrid")


def _dt_cache_token(value: datetime | None) -> str:
    if value is None:
        return "none"
    utc_value = value.astimezone(timezone.utc)
    return utc_value.replace(microsecond=0).isoformat()


def _format_output_datetime(value: datetime | None, mode: str) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    if mode == "utc":
        rendered = value.astimezone(timezone.utc)
    else:
        rendered = value.astimezone(SEARCH_LOCAL_TIMEZONE)
    return rendered.date().isoformat(), rendered.time().replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class SearchEventsResult:
    payload: dict[str, object]
    cache_header: str


class SearchEventsUseCase:
    def __init__(self, db: Session, cache: SearchCacheRepository | None) -> None:
        self.db = db
        self.cache = cache

    def execute(
        self,
        starts_at: datetime | None,
        ends_at: datetime | None,
        mode: str,
    ) -> SearchEventsResult:
        if starts_at is not None and starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)
        if ends_at is not None and ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)
        if starts_at is not None and ends_at is not None and starts_at > ends_at:
            raise ValueError("starts_at must be less than or equal to ends_at")

        cache_key: str | None = None
        if self.cache is not None:
            try:
                version = self.cache.get_version()
                cache_key = (
                    f"search:v{version}:mode={mode}:starts_at={_dt_cache_token(starts_at)}:"
                    f"ends_at={_dt_cache_token(ends_at)}"
                )
                cached = self.cache.get(cache_key)
                if cached is not None:
                    return SearchEventsResult(payload=cached, cache_header="HIT")
            except Exception:
                self.cache = None

        query = self.db.query(EventCurrent).filter(EventCurrent.ever_online.is_(True))
        if starts_at is not None:
            query = query.filter(EventCurrent.end_at >= starts_at)
        if ends_at is not None:
            query = query.filter(EventCurrent.start_at <= ends_at)
        plans = query.order_by(EventCurrent.start_at.asc()).all()

        result = {
            "data": {
                "events": [self._event_response_row(p, mode) for p in plans]
            },
            "error": None,
        }

        if self.cache is not None and cache_key is not None and result["data"]["events"]:
            try:
                self.cache.set(cache_key, result, SEARCH_CACHE_TTL_SECONDS)
            except Exception:
                pass

        return SearchEventsResult(payload=result, cache_header="MISS")

    def _event_response_row(self, event: EventCurrent, mode: str) -> dict[str, object]:
        start_date, start_time = _format_output_datetime(event.start_at, mode)
        end_date, end_time = _format_output_datetime(event.end_at, mode)
        return {
            "id": str(uuid5(NAMESPACE_URL, f"{UUID_NAMESPACE}:{event.provider_event_id}")),
            "title": event.title,
            "start_date": start_date,
            "start_time": start_time,
            "end_date": end_date,
            "end_time": end_time,
            "min_price": float(event.min_price) if event.min_price is not None else None,
            "max_price": float(event.max_price) if event.max_price is not None else None,
        }
