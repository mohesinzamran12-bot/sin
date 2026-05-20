from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.core.config import settings
from app.services.notification_service import test_connection

router = APIRouter()


@router.get("/settings")
async def get_notification_settings(_: dict = Depends(get_current_user)) -> dict:
    return {
        "telegram_configured": bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID),
        "telegram_chat_id": settings.TELEGRAM_CHAT_ID or None,
    }


@router.post("/test")
async def test_notification(_: dict = Depends(get_current_user)) -> dict:
    result = await test_connection()
    return result
