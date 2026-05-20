import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.database import get_session
from app.core.security import get_current_user
from app.models.candidate import Candidate, JobPreferences
from app.schemas.candidate import (
    CandidateCreate,
    CandidateRead,
    CandidateUpdate,
    JobPreferencesCreate,
    JobPreferencesRead,
    JobPreferencesUpdate,
)
from app.services.cv_parser import extract_text_from_pdf, parse_cv_sections

router = APIRouter()


async def _get_candidate_or_404(
    candidate_id: uuid.UUID, session: AsyncSession
) -> Candidate:
    result = await session.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )
    return candidate


async def _get_preferences(
    candidate_id: uuid.UUID, session: AsyncSession
) -> Optional[JobPreferences]:
    result = await session.execute(
        select(JobPreferences).where(JobPreferences.candidate_id == candidate_id)
    )
    return result.scalar_one_or_none()


@router.post("/", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    data: CandidateCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> CandidateRead:
    """Create a new candidate profile."""
    # Check for existing email
    existing = await session.execute(
        select(Candidate).where(Candidate.email == data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A candidate with this email already exists",
        )

    candidate = Candidate(
        name=data.name,
        email=data.email,
        phone=data.phone,
    )
    session.add(candidate)
    await session.flush()
    await session.refresh(candidate)

    return CandidateRead(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        cv_file_path=candidate.cv_file_path,
        cv_parsed_json=candidate.cv_parsed_json,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        preferences=None,
    )


@router.get("/{candidate_id}", response_model=CandidateRead)
async def get_candidate(
    candidate_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> CandidateRead:
    """Get candidate by ID, including job preferences."""
    candidate = await _get_candidate_or_404(candidate_id, session)
    prefs = await _get_preferences(candidate_id, session)

    prefs_read = None
    if prefs:
        prefs_read = JobPreferencesRead.model_validate(prefs)

    return CandidateRead(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        cv_file_path=candidate.cv_file_path,
        cv_parsed_json=candidate.cv_parsed_json,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        preferences=prefs_read,
    )


@router.patch("/{candidate_id}", response_model=CandidateRead)
async def update_candidate(
    candidate_id: uuid.UUID,
    data: CandidateUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> CandidateRead:
    """Partially update a candidate's profile."""
    candidate = await _get_candidate_or_404(candidate_id, session)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(candidate, field, value)
    candidate.updated_at = datetime.now(timezone.utc)

    session.add(candidate)
    await session.flush()
    await session.refresh(candidate)

    prefs = await _get_preferences(candidate_id, session)
    prefs_read = JobPreferencesRead.model_validate(prefs) if prefs else None

    return CandidateRead(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        cv_file_path=candidate.cv_file_path,
        cv_parsed_json=candidate.cv_parsed_json,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        preferences=prefs_read,
    )


@router.post("/{candidate_id}/cv", response_model=CandidateRead)
async def upload_cv(
    candidate_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> CandidateRead:
    """Upload a PDF CV for a candidate. Extracts and stores text."""
    candidate = await _get_candidate_or_404(candidate_id, session)

    # Validate content type
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        # Also check filename extension as fallback
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only PDF files are accepted",
            )

    file_bytes = await file.read()

    # Validate size
    if len(file_bytes) > settings.MAX_CV_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.MAX_CV_SIZE_BYTES} bytes",
        )

    # Ensure upload directory exists
    os.makedirs(settings.CV_UPLOAD_DIR, exist_ok=True)

    # Save file to disk
    safe_name = f"{candidate_id}_{file.filename or 'cv.pdf'}"
    file_path = os.path.join(settings.CV_UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Extract text from PDF
    try:
        raw_text = extract_text_from_pdf(file_bytes)
    except Exception:
        raw_text = ""

    parsed = parse_cv_sections(raw_text)

    # Update candidate
    candidate.cv_file_path = file_path
    candidate.cv_raw_text = raw_text
    candidate.cv_parsed_json = parsed
    candidate.updated_at = datetime.now(timezone.utc)

    session.add(candidate)
    await session.flush()
    await session.refresh(candidate)

    prefs = await _get_preferences(candidate_id, session)
    prefs_read = JobPreferencesRead.model_validate(prefs) if prefs else None

    return CandidateRead(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        cv_file_path=candidate.cv_file_path,
        cv_parsed_json=candidate.cv_parsed_json,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        preferences=prefs_read,
    )


@router.get("/{candidate_id}/preferences", response_model=JobPreferencesRead)
async def get_preferences(
    candidate_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> JobPreferencesRead:
    """Get job preferences for a candidate."""
    await _get_candidate_or_404(candidate_id, session)
    prefs = await _get_preferences(candidate_id, session)
    if not prefs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job preferences not found",
        )
    return JobPreferencesRead.model_validate(prefs)


@router.put("/{candidate_id}/preferences", response_model=JobPreferencesRead)
async def upsert_preferences(
    candidate_id: uuid.UUID,
    data: JobPreferencesCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> JobPreferencesRead:
    """Create or replace job preferences for a candidate."""
    await _get_candidate_or_404(candidate_id, session)
    prefs = await _get_preferences(candidate_id, session)

    if prefs:
        # Update existing
        for field, value in data.model_dump().items():
            setattr(prefs, field, value)
    else:
        prefs = JobPreferences(
            candidate_id=candidate_id,
            **data.model_dump(),
        )
        session.add(prefs)

    await session.flush()
    await session.refresh(prefs)

    return JobPreferencesRead.model_validate(prefs)


@router.patch("/{candidate_id}/preferences", response_model=JobPreferencesRead)
async def patch_preferences(
    candidate_id: uuid.UUID,
    data: JobPreferencesUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
) -> JobPreferencesRead:
    """Partially update job preferences for a candidate."""
    await _get_candidate_or_404(candidate_id, session)
    prefs = await _get_preferences(candidate_id, session)

    if not prefs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job preferences not found. Use PUT to create.",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prefs, field, value)

    await session.flush()
    await session.refresh(prefs)

    return JobPreferencesRead.model_validate(prefs)
