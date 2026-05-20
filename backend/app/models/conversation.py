import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    application_id: uuid.UUID = Field(foreign_key="applications.id", index=True)
    direction: str  # "inbound" | "outbound"
    body: str = Field(sa_column=Column(Text, nullable=False))
    sender_name: str = Field(default="")
    sent_at: datetime  # when the message was sent (from BOSS)
    reply_needed: bool = Field(default=False, index=True)
    reply_deadline: Optional[datetime] = None
    draft_reply: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
