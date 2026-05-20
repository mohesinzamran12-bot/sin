import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.core.config import settings
from app.models.browser import BrowserSession
from app.models.system import SystemEvent
from app.schemas.collection import (
    BrowserSessionCreate,
    BrowserSessionRead,
    CollectionTriggerRequest,
    CollectionStatusRead,
)
from playwright_worker.session_store import encrypt_cookies

router = APIRouter()


@router.post("/trigger", status_code=202)
async def trigger_collection(
    body: CollectionTriggerRequest,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> dict:
    """Enqueue a job collection run for the given candidate."""
    # Check daily limit before enqueuing
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    run_count = (await session.execute(
        select(func.count()).select_from(SystemEvent).where(
            SystemEvent.source == "collection",
            SystemEvent.message == "collection_started",
            SystemEvent.created_at >= today_start,
        )
    )).scalar_one()

    if run_count >= settings.MAX_COLLECTION_RUNS_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail=f"Daily collection limit reached ({settings.MAX_COLLECTION_RUNS_PER_DAY} runs/day)",
        )

    # Check valid session exists
    has_session = (await session.execute(
        select(func.count()).select_from(BrowserSession).where(
            BrowserSession.platform == "boss_zhipin",
            BrowserSession.is_valid == True,
        )
    )).scalar_one()
    if not has_session:
        raise HTTPException(
            status_code=400,
            detail="No valid BOSS Zhipin session. Add cookies in Settings first.",
        )

    from app.workers.tasks.collection_tasks import collect_jobs_task
    task = collect_jobs_task.delay(str(body.candidate_id))
    return {"task_id": task.id, "status": "queued", "message": "Collection started"}


@router.get("/status", response_model=CollectionStatusRead)
async def collection_status(
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> CollectionStatusRead:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    runs_today = (await session.execute(
        select(func.count()).select_from(SystemEvent).where(
            SystemEvent.source == "collection",
            SystemEvent.message == "collection_started",
            SystemEvent.created_at >= today_start,
        )
    )).scalar_one()

    last_event = (await session.execute(
        select(SystemEvent).where(
            SystemEvent.source == "collection",
            SystemEvent.message == "collection_completed",
        ).order_by(SystemEvent.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    has_session = (await session.execute(
        select(func.count()).select_from(BrowserSession).where(
            BrowserSession.is_valid == True
        )
    )).scalar_one() > 0

    return CollectionStatusRead(
        last_run_at=last_event.created_at if last_event else None,
        last_run_result=last_event.event_metadata if last_event else None,
        runs_today=runs_today,
        max_runs_per_day=settings.MAX_COLLECTION_RUNS_PER_DAY,
        has_valid_session=has_session,
    )


@router.get("/sessions", response_model=list[BrowserSessionRead])
async def list_sessions(
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> list[BrowserSessionRead]:
    result = await session.execute(
        select(BrowserSession).order_by(BrowserSession.created_at.desc())
    )
    return [BrowserSessionRead.model_validate(s) for s in result.scalars().all()]


@router.post("/sessions", response_model=BrowserSessionRead, status_code=201)
async def create_session(
    body: BrowserSessionCreate,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> BrowserSessionRead:
    if not body.cookies:
        raise HTTPException(status_code=400, detail="cookies list cannot be empty")
    encrypted = encrypt_cookies(body.cookies)
    browser_session = BrowserSession(
        platform=body.platform,
        cookies_encrypted=encrypted,
        user_agent=body.user_agent,
        is_valid=True,
    )
    session.add(browser_session)
    await session.flush()
    await session.refresh(browser_session)
    return BrowserSessionRead.model_validate(browser_session)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> None:
    result = await session.execute(
        select(BrowserSession).where(BrowserSession.id == session_id)
    )
    bs = result.scalar_one_or_none()
    if not bs:
        raise HTTPException(status_code=404, detail="Session not found")
    await session.delete(bs)
    await session.flush()
