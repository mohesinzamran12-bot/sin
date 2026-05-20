import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Text
from sqlmodel import JSON, Field, SQLModel


class ApprovalQueue(SQLModel, table=True):
    __tablename__ = "approval_queue"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    application_id: uuid.UUID = Field(foreign_key="applications.id", index=True)
    action: str  # "send_application" | "send_reply"
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    # payload contains: {"message": "...", "job_title": "...", "company": "...", "score": 82.5}
    status: str = Field(default="pending")  # pending / approved / rejected / expired
    reviewer_notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
