import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import JSON, Field, SQLModel


class JobScore(SQLModel, table=True):
    __tablename__ = "job_scores"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", index=True)
    candidate_id: uuid.UUID = Field(foreign_key="candidates.id", index=True)
    score: float  # 0-100
    score_breakdown: dict = Field(sa_column=Column(JSON, nullable=False))
    match_summary: str = Field(sa_column=Column(Text, nullable=False))
    strengths: list = Field(default_factory=list, sa_column=Column(JSON, nullable=True))
    concerns: list = Field(default_factory=list, sa_column=Column(JSON, nullable=True))
    model_used: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    scored_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AIAuditLog(SQLModel, table=True):
    __tablename__ = "ai_audit_log"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    event_type: str  # score / draft_message / draft_reply / classify
    entity_type: str  # job / application / conversation
    entity_id: uuid.UUID
    model: str
    prompt_hash: str  # SHA-256 of the full prompt
    input_tokens: int = 0
    output_tokens: int = 0
    result_summary: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
