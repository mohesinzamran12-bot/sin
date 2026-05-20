import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.job import Job
from app.schemas.job import JobCreate, JobListResponse, JobRead, JobUpdate

router = APIRouter()


async def _get_job_or_404(job_id: uuid.UUID, session: AsyncSession) -> Job:
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    city: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> JobListResponse:
    """List all jobs with optional filtering and pagination."""
    query = select(Job)
    count_query = select(func.count()).select_from(Job)

    if is_active is not None:
        query = query.where(Job.is_active == is_active)
        count_query = count_query.where(Job.is_active == is_active)
    if city:
        query = query.where(Job.city.ilike(f"%{city}%"))
        count_query = count_query.where(Job.city.ilike(f"%{city}%"))

    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Job.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        items=[JobRead.model_validate(j) for j in jobs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> JobRead:
    """Get a single job by ID."""
    job = await _get_job_or_404(job_id, session)
    return JobRead.model_validate(job)


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    data: JobCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> JobRead:
    """Manually create a new job entry."""
    job = Job(**data.model_dump())
    session.add(job)
    await session.flush()
    await session.refresh(job)
    return JobRead.model_validate(job)


@router.patch("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: uuid.UUID,
    data: JobUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> JobRead:
    """Partially update a job entry."""
    job = await _get_job_or_404(job_id, session)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)
    job.updated_at = datetime.now(timezone.utc)

    session.add(job)
    await session.flush()
    await session.refresh(job)
    return JobRead.model_validate(job)


@router.delete("/{job_id}", response_model=JobRead)
async def delete_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> JobRead:
    """Soft-delete a job by marking it inactive."""
    job = await _get_job_or_404(job_id, session)
    job.is_active = False
    job.updated_at = datetime.now(timezone.utc)
    session.add(job)
    await session.flush()
    await session.refresh(job)
    return JobRead.model_validate(job)
