import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class Application(SQLModel, table=True):
    __tablename__ = "applications"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", index=True)
    candidate_id: uuid.UUID = Field(foreign_key="candidates.id", index=True)
    status: str = Field(default="pending_approval")  # pending_approval/approved/sent/replied/interviewing/rejected/withdrawn
    draft_message: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    final_message: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    boss_chat_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
