import ssl

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "nexe_agent",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

_ssl_opts = {"ssl_cert_reqs": ssl.CERT_NONE} if settings.redis_url.startswith("rediss://") else None

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # solo pool avoids Windows shared-memory PermissionError (WinError 5)
    worker_pool="solo",
    **({} if _ssl_opts is None else {
        "broker_use_ssl": _ssl_opts,
        "redis_backend_use_ssl": _ssl_opts,
    }),
)

celery_app.conf.include = [
    "app.tasks.plan_goal",
    "app.tasks.execute_run",
    "app.tasks.archive_logs",
]

celery_app.conf.beat_schedule = {
    "archive-old-logs-daily": {
        "task": "app.tasks.archive_logs.archive_old_logs",
        "schedule": crontab(hour=2, minute=0),
    },
}
