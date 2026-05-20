import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class BrowserSessionCreate(BaseModel):
    cookies: list[dict]           # raw cookie array from browser export
    user_agent: str = ""
    platform: str = "boss_zhipin"


class BrowserSessionRead(BaseModel):
    id: uuid.UUID
    platform: str
    is_valid: bool
    user_agent: str
    last_used_at: Optional[datetime]
    created_at: datetime
    # NOTE: cookies_encrypted is NEVER returned to the client
    model_config = {"from_attributes": True}


class CollectionTriggerRequest(BaseModel):
    candidate_id: uuid.UUID


class CollectionStatusRead(BaseModel):
    last_run_at: Optional[datetime]
    last_run_result: Optional[dict]
    runs_today: int
    max_runs_per_day: int
    has_valid_session: bool
