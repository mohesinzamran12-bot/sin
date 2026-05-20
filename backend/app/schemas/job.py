import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JobCreate(BaseModel):
    title: str
    company_name: str
    city: Optional[str] = None
    salary_range: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    url: Optional[str] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    company_name: Optional[str] = None
    city: Optional[str] = None
    salary_range: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    url: Optional[str] = None
    is_active: Optional[bool] = None


class JobRead(BaseModel):
    id: uuid.UUID
    title: str
    company_name: str
    city: Optional[str]
    salary_range: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    description: Optional[str]
    requirements: Optional[str]
    url: Optional[str]
    is_active: bool
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobRead]
    total: int
    skip: int
    limit: int
