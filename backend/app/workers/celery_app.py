from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "jobcrm",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Import tasks to register them with Celery
celery_app.autodiscover_tasks(["app.workers.tasks"])

celery_app.conf.task_routes = {
    "tasks.collect_jobs": {"queue": "playwright"},
    "tasks.*": {"queue": "celery"},
}

celery_app.conf.beat_schedule = {
    "expire-old-approvals": {
        "task": "tasks.expire_old_approvals",
        "schedule": crontab(minute="*/30"),  # every 30 minutes
    },
}
