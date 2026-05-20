import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ApprovalQueueRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    action: str
    payload: dict
    status: str
    reviewer_notes: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]
    model_config = {"from_attributes": True}


class ApprovalQueueListResponse(BaseModel):
    items: list[ApprovalQueueRead]
    total: int
    skip: int
    limit: int


class ApproveRequest(BaseModel):
    message: Optional[str] = None   # if provided, overrides draft_message as final_message
    notes: Optional[str] = None


class RejectRequest(BaseModel):
    notes: Optional[str] = None
