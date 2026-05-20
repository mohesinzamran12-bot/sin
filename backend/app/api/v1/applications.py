import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.score import JobScore
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationRead,
    ApplicationUpdate,
)
from app.services import claude_service, scoring_service

router = APIRouter()


@router.post("/", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application(
    body: ApplicationCreate,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> ApplicationRead:
    # Verify job exists
    job_result = await session.execute(select(Job).where(Job.id == body.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Verify candidate exists
    cand_result = await session.execute(
        select(Candidate).where(Candidate.id == body.candidate_id)
    )
    candidate = cand_result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
        )

    # Get or create score
    score: JobScore | None = None
    try:
        score = await scoring_service.get_or_create_score(
            job_id=body.job_id,
            candidate_id=body.candidate_id,
            session=session,
            force_rescore=False,
        )
    except HTTPException as exc:
        if exc.status_code not in (503, 402):
            raise
        # API not configured or budget exceeded — continue without score

    # Draft message
    draft: str | None = None
    if score is not None:
        try:
            draft = await claude_service.draft_application_message(
                job=job, candidate=candidate, score=score, session=session
            )
        except HTTPException as exc:
            if exc.status_code not in (503, 402):
                raise

    application = Application(
        job_id=body.job_id,
        candidate_id=body.candidate_id,
        status="pending_approval",
        draft_message=draft,
    )
    session.add(application)
    await session.flush()
    await session.refresh(application)
    return ApplicationRead.model_validate(application)


@router.get("/", response_model=ApplicationListResponse)
async def list_applications(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> ApplicationListResponse:
    query = select(Application)
    count_query = select(func.count()).select_from(Application)

    if status_filter:
        query = query.where(Application.status == status_filter)
        count_query = count_query.where(Application.status == status_filter)

    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Application.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    apps = result.scalars().all()

    return ApplicationListResponse(
        items=[ApplicationRead.model_validate(a) for a in apps],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(
    application_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> ApplicationRead:
    result = await session.execute(
        select(Application).where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )
    return ApplicationRead.model_validate(app)


@router.patch("/{application_id}", response_model=ApplicationRead)
async def update_application(
    application_id: uuid.UUID,
    body: ApplicationUpdate,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> ApplicationRead:
    result = await session.execute(
        select(Application).where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(app, field, value)
    app.updated_at = datetime.now(timezone.utc)
    session.add(app)
    await session.flush()
    await session.refresh(app)
    return ApplicationRead.model_validate(app)
