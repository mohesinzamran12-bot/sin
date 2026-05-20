from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.application import Application
from app.models.job import Job
from app.models.score import AIAuditLog
from app.schemas.score import AIAuditLogListResponse, AIAuditLogRead

router = APIRouter()

_INPUT_COST_PER_M = 3.0
_OUTPUT_COST_PER_M = 15.0


@router.get("/logs/ai", response_model=AIAuditLogListResponse)
async def list_ai_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> AIAuditLogListResponse:
    count_result = await session.execute(
        select(func.count()).select_from(AIAuditLog)
    )
    total = count_result.scalar_one()

    result = await session.execute(
        select(AIAuditLog)
        .order_by(AIAuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    logs = result.scalars().all()

    return AIAuditLogListResponse(
        items=[AIAuditLogRead.model_validate(log) for log in logs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/stats/dashboard")
async def dashboard_stats(
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> dict:
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    total_jobs = (
        await session.execute(select(func.count()).select_from(Job))
    ).scalar_one()

    active_jobs = (
        await session.execute(
            select(func.count()).select_from(Job).where(Job.is_active == True)
        )
    ).scalar_one()

    total_applications = (
        await session.execute(select(func.count()).select_from(Application))
    ).scalar_one()

    pending_approvals = (
        await session.execute(
            select(func.count())
            .select_from(Application)
            .where(Application.status == "pending_approval")
        )
    ).scalar_one()

    total_ai_calls = (
        await session.execute(select(func.count()).select_from(AIAuditLog))
    ).scalar_one()

    today_logs_result = await session.execute(
        select(AIAuditLog.input_tokens, AIAuditLog.output_tokens).where(
            AIAuditLog.created_at >= today_start
        )
    )
    today_logs = today_logs_result.all()

    total_tokens_today = sum(row.input_tokens + row.output_tokens for row in today_logs)
    estimated_cost_today = sum(
        row.input_tokens * _INPUT_COST_PER_M / 1_000_000
        + row.output_tokens * _OUTPUT_COST_PER_M / 1_000_000
        for row in today_logs
    )

    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "total_applications": total_applications,
        "pending_approvals": pending_approvals,
        "total_ai_calls": total_ai_calls,
        "total_tokens_today": total_tokens_today,
        "estimated_cost_today_usd": round(estimated_cost_today, 6),
    }
