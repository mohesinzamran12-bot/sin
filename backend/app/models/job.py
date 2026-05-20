import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import JSON, Field, SQLModel


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    external_id: Optional[str] = Field(default=None, unique=True, index=True)
    source: str = Field(default="manual")
    title: str
    company_name: str
    city: Optional[str] = None
    salary_range: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    requirements: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    url: Optional[str] = None
    raw_html: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    collected_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
