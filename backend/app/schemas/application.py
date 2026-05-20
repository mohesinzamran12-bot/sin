import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    candidate_id: uuid.UUID


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    final_message: Optional[str] = None


class ApplicationRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    status: str
    draft_message: Optional[str]
    final_message: Optional[str]
    approved_at: Optional[datetime]
    sent_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationListResponse(BaseModel):
    items: list[ApplicationRead]
    total: int
    skip: int
    limit: int
