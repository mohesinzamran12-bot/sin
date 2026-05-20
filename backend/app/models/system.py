import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import JSON, Field, SQLModel


class SystemEvent(SQLModel, table=True):
    __tablename__ = "system_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    level: str
    source: str
    message: str = Field(sa_column=Column(Text, nullable=False))
    metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
