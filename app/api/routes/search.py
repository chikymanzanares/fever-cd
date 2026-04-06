from datetime import datetime
import os

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.application.use_cases.search_events_use_case import SearchEventsUseCase
from app.infrastructure.cache.redis_search_cache_repository import get_search_cache
from app.infrastructure.db.session import get_db

router = APIRouter()


def _search_time_mode() -> str:
    mode = os.getenv("SEARCH_TIME_MODE", "local").strip().lower()
    if mode not in {"local", "utc"}:
        return "local"
    return mode


def _build_search_use_case(db: Session) -> SearchEventsUseCase:
    cache = None
    try:
        cache = get_search_cache()
    except Exception:
        cache = None
    return SearchEventsUseCase(db=db, cache=cache)


@router.get("/search")
def search(
    starts_at: datetime | None = Query(None, description="Return only events that starts after this date"),
    ends_at: datetime | None = Query(None, description="Return only events that finishes before this date"),
    db: Session = Depends(get_db),
    response: Response = None,
):
    use_case = _build_search_use_case(db)
    try:
        result = use_case.execute(
            starts_at=starts_at,
            ends_at=ends_at,
            mode=_search_time_mode(),
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "BAD_REQUEST",
                    "message": str(exc),
                },
                "data": None,
            },
        )
    if response is not None:
        response.headers["X-Search-Cache"] = result.cache_header
    return result.payload

