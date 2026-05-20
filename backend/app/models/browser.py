import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class BrowserSession(SQLModel, table=True):
    __tablename__ = "browser_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    platform: str = Field(default="boss_zhipin", index=True)
    cookies_encrypted: bytes  # AES Fernet encrypted JSON cookie array
    is_valid: bool = Field(default=True, index=True)
    user_agent: str = Field(default="")
    last_used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
