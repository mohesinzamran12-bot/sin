import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.approval import ApprovalQueue
from app.models.application import Application
from app.models.job import Job
from app.schemas.approval import (
    ApprovalQueueListResponse,
    ApprovalQueueRead,
    ApproveRequest,
    RejectRequest,
)

router = APIRouter()


@router.get("/", response_model=ApprovalQueueListResponse)
async def list_approvals(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default="pending", alias="status"),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> ApprovalQueueListResponse:
    query = select(ApprovalQueue)
    count_query = select(func.count()).select_from(ApprovalQueue)
    if status_filter:
        query = query.where(ApprovalQueue.status == status_filter)
        count_query = count_query.where(ApprovalQueue.status == status_filter)
    total = (await session.execute(count_query)).scalar_one()
    query = query.order_by(ApprovalQueue.created_at.desc()).offset(skip).limit(limit)
    items = (await session.execute(query)).scalars().all()
    return ApprovalQueueListResponse(
        items=[ApprovalQueueRead.model_validate(i) for i in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/{approval_id}", response_model=ApprovalQueueRead)
async def get_approval(
    approval_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> ApprovalQueueRead:
    entry = (await session.execute(
        select(ApprovalQueue).where(ApprovalQueue.id == approval_id)
    )).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Approval not found")
    return ApprovalQueueRead.model_validate(entry)


@router.post("/{approval_id}/approve", response_model=ApprovalQueueRead)
async def approve(
    approval_id: uuid.UUID,
    body: ApproveRequest,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> ApprovalQueueRead:
    entry = (await session.execute(
        select(ApprovalQueue).where(ApprovalQueue.id == approval_id)
    )).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Approval not found")
    if entry.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot approve: status is '{entry.status}'")

    # Update approval entry
    entry.status = "approved"
    entry.reviewed_at = datetime.now(timezone.utc)
    entry.reviewer_notes = body.notes
    session.add(entry)

    # Update application
    app_result = await session.execute(
        select(Application).where(Application.id == entry.application_id)
    )
    application = app_result.scalar_one_or_none()
    if application:
        application.status = "approved"
        application.approved_at = datetime.now(timezone.utc)
        application.final_message = body.message or application.draft_message
        application.updated_at = datetime.now(timezone.utc)
        session.add(application)

    await session.flush()

    # Fire-and-forget notification (non-blocking)
    try:
        from app.workers.tasks.notification_tasks import send_result_notification
        job = (await session.execute(select(Job).where(Job.id == application.job_id))).scalar_one_or_none() if application else None
        if job:
            send_result_notification.delay(job.title, job.company_name, "approved")
    except Exception:
        pass  # Notifications are best-effort

    await session.refresh(entry)
    return ApprovalQueueRead.model_validate(entry)


@router.post("/{approval_id}/reject", response_model=ApprovalQueueRead)
async def reject(
    approval_id: uuid.UUID,
    body: RejectRequest,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> ApprovalQueueRead:
    entry = (await session.execute(
        select(ApprovalQueue).where(ApprovalQueue.id == approval_id)
    )).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Approval not found")
    if entry.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot reject: status is '{entry.status}'")

    entry.status = "rejected"
    entry.reviewed_at = datetime.now(timezone.utc)
    entry.reviewer_notes = body.notes
    session.add(entry)

    app_result = await session.execute(
        select(Application).where(Application.id == entry.application_id)
    )
    application = app_result.scalar_one_or_none()
    if application:
        application.status = "withdrawn"
        application.updated_at = datetime.now(timezone.utc)
        session.add(application)

    await session.flush()

    try:
        from app.workers.tasks.notification_tasks import send_result_notification
        job = (await session.execute(select(Job).where(Job.id == application.job_id))).scalar_one_or_none() if application else None
        if job:
            send_result_notification.delay(job.title, job.company_name, "rejected")
    except Exception:
        pass

    await session.refresh(entry)
    return ApprovalQueueRead.model_validate(entry)
