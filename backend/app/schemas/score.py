import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScoreBreakdownRead(BaseModel):
    skills: float
    experience: float
    salary: float
    culture: float


class JobScoreRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    score: float
    score_breakdown: ScoreBreakdownRead
    match_summary: str
    strengths: list[str]
    concerns: list[str]
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    scored_at: datetime

    model_config = {"from_attributes": True}


class AIAuditLogRead(BaseModel):
    id: uuid.UUID
    event_type: str
    entity_type: str
    entity_id: uuid.UUID
    model: str
    input_tokens: int
    output_tokens: int
    result_summary: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AIAuditLogListResponse(BaseModel):
    items: list[AIAuditLogRead]
    total: int
    skip: int
    limit: int
