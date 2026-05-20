import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.score import JobScore
from app.schemas.score import JobScoreRead
from app.services import scoring_service

router = APIRouter()


@router.get("/jobs/{job_id}/score", response_model=JobScoreRead)
async def get_job_score(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> JobScoreRead:
    """Return existing score or 404 — does NOT trigger scoring."""
    result = await session.execute(
        select(JobScore)
        .where(JobScore.job_id == job_id)
        .where(JobScore.candidate_id == candidate_id)
        .order_by(JobScore.scored_at.desc())
    )
    score = result.scalars().first()
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No score found for this job/candidate pair",
        )
    return JobScoreRead.model_validate(score)


class ScoreRequestBody(BaseModel):
    candidate_id: uuid.UUID


@router.post("/jobs/{job_id}/score", response_model=JobScoreRead)
async def score_job(
    job_id: uuid.UUID,
    body: ScoreRequestBody,
    force: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> JobScoreRead:
    """Trigger scoring (or force rescore) for a job/candidate pair."""
    score = await scoring_service.get_or_create_score(
        job_id=job_id,
        candidate_id=body.candidate_id,
        session=session,
        force_rescore=force,
    )
    return JobScoreRead.model_validate(score)
