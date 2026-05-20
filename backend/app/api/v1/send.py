import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from datetime import datetime, timezone

from app.core.database import get_session
from app.core.security import get_current_user
from app.core.config import settings
from app.models.application import Application
from app.models.approval import ApprovalQueue
from app.models.system import SystemEvent

router = APIRouter()


@router.post("/applications/{application_id}/send", status_code=202)
async def send_application(
    application_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> dict:
    """Enqueue the Playwright send task for an approved application."""
    # Load application
    app = (await session.execute(
        select(Application).where(Application.id == application_id)
    )).scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status != "approved":
        raise HTTPException(status_code=400, detail=f"Application status is '{app.status}', must be 'approved' to send")

    # Verify approval queue entry is approved
    approval = (await session.execute(
        select(ApprovalQueue).where(
            ApprovalQueue.application_id == application_id,
            ApprovalQueue.action == "send_application",
            ApprovalQueue.status == "approved",
        )
    )).scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=400, detail="Application has not been approved in the approval queue")

    # Daily limit check
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    sent_today = (await session.execute(
        select(func.count()).select_from(SystemEvent).where(
            SystemEvent.source == "send",
            SystemEvent.message == "message_sent",
            SystemEvent.created_at >= today_start,
        )
    )).scalar_one()
    if sent_today >= settings.MAX_APPLICATIONS_PER_DAY:
        raise HTTPException(status_code=429, detail=f"Daily send limit reached ({settings.MAX_APPLICATIONS_PER_DAY}/day)")

    from app.workers.tasks.send_tasks import send_application_message_task
    task = send_application_message_task.delay(str(application_id))
    return {"task_id": task.id, "status": "queued", "message": "Send task enqueued"}
