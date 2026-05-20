"""Thin orchestration layer for job scoring."""
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.candidate import Candidate
from app.models.job import Job
from app.models.score import JobScore
from app.services import claude_service


async def get_or_create_score(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    session: AsyncSession,
    force_rescore: bool = False,
) -> JobScore:
    """
    Return existing score if present and force_rescore=False.
    Otherwise call claude_service.score_job_against_cv and return new score.
    """
    if not force_rescore:
        result = await session.execute(
            select(JobScore)
            .where(JobScore.job_id == job_id)
            .where(JobScore.candidate_id == candidate_id)
            .order_by(JobScore.scored_at.desc())
        )
        existing = result.scalars().first()
        if existing:
            return existing

    # Load job
    job_result = await session.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Load candidate
    candidate_result = await session.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = candidate_result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )

    return await claude_service.score_job_against_cv(job, candidate, session)
