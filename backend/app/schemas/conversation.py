import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ConversationRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    direction: str
    body: str
    sender_name: str
    sent_at: datetime
    reply_needed: bool
    reply_deadline: Optional[datetime]
    draft_reply: Optional[str]
    collected_at: datetime
    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    items: list[ConversationRead]
    total: int
    skip: int
    limit: int


class SyncRequest(BaseModel):
    candidate_id: uuid.UUID
