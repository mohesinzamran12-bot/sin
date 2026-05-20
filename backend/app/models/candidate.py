import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String
from sqlmodel import JSON, Field, SQLModel


class Candidate(SQLModel, table=True):
    __tablename__ = "candidates"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    phone: Optional[str] = None
    cv_raw_text: Optional[str] = Field(default=None, sa_column=Column("cv_raw_text", String, nullable=True))
    cv_file_path: Optional[str] = None
    cv_parsed_json: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobPreferences(SQLModel, table=True):
    __tablename__ = "job_preferences"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    candidate_id: uuid.UUID = Field(foreign_key="candidates.id")
    # Using JSON columns for cross-DB compatibility (works on both PostgreSQL and SQLite)
    target_titles: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=True),
    )
    target_cities: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=True),
    )
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    excluded_companies: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=True),
    )
    preferred_industries: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=True),
    )
    remote_ok: bool = False
    full_time_only: bool = True
