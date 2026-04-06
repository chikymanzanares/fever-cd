import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.search import router as search_router

app = FastAPI(title="Fever Code Challenge")

app.include_router(search_router)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "BAD_REQUEST",
                "message": "The request is not correctly formed.",
            },
            "data": None,
        },
    )


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


if _env_bool("ENABLE_DEV_ENDPOINTS", default=False):
    @app.get("/health")
    def health():
        return {"status": "ok"}

