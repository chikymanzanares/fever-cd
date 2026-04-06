from __future__ import annotations

import os

from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery(
    "juanjo_velasco_worker",
    broker=broker_url,
    backend=result_backend,
)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    imports=("app.worker.tasks",),
    beat_schedule={
        "sync-events-every-minute": {
            "task": "app.worker.tasks.sync_events",
            "schedule": 60.0,
        }
    },
)

