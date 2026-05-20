import asyncio
from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.send_approval_notification", ignore_result=True)
def send_approval_notification(
    job_title: str,
    company: str,
    score: float | None,
    draft_message: str,
    approval_id: str,
) -> None:
    """Send Telegram notification for pending approval. Runs in Celery worker."""
    from app.services.notification_service import notify_approval_needed
    asyncio.run(notify_approval_needed(job_title, company, score, draft_message, approval_id))


@celery_app.task(name="tasks.send_result_notification", ignore_result=True)
def send_result_notification(job_title: str, company: str, action: str) -> None:
    from app.services.notification_service import notify_approval_result
    asyncio.run(notify_approval_result(job_title, company, action))
