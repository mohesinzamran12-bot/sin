import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JobPreferencesCreate(BaseModel):
    target_titles: list[str] = []
    target_cities: list[str] = []
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    excluded_companies: list[str] = []
    preferred_industries: list[str] = []
    remote_ok: bool = False
    full_time_only: bool = True


class JobPreferencesUpdate(BaseModel):
    target_titles: Optional[list[str]] = None
    target_cities: Optional[list[str]] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    excluded_companies: Optional[list[str]] = None
    preferred_industries: Optional[list[str]] = None
    remote_ok: Optional[bool] = None
    full_time_only: Optional[bool] = None


class JobPreferencesRead(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    target_titles: list[str]
    target_cities: list[str]
    min_salary: Optional[int]
    max_salary: Optional[int]
    excluded_companies: list[str]
    preferred_industries: list[str]
    remote_ok: bool
    full_time_only: bool

    model_config = {"from_attributes": True}


class CandidateCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None


class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class CandidateRead(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone: Optional[str]
    cv_file_path: Optional[str]
    cv_parsed_json: Optional[dict]
    created_at: datetime
    updated_at: datetime
    preferences: Optional[JobPreferencesRead] = None

    model_config = {"from_attributes": True}
