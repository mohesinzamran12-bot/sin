import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

TELEGRAM_API = "https://api.telegram.org"

def _is_configured() -> bool:
    return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)

async def send_message(text: str) -> bool:
    """Send a Telegram message. Returns True on success, False if not configured or failed."""
    if not _is_configured():
        logger.info("telegram_not_configured", reason="missing token or chat_id")
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": settings.TELEGRAM_CHAT_ID,
                    "text": text,
                    "parse_mode": "HTML",
                },
            )
            if resp.status_code != 200:
                logger.warning("telegram_send_failed", status=resp.status_code, body=resp.text)
                return False
            return True
    except Exception as exc:
        logger.error("telegram_send_error", error=str(exc))
        return False

async def notify_approval_needed(
    job_title: str,
    company: str,
    score: float | None,
    draft_message: str,
    approval_id: str,
) -> bool:
    score_str = f"{score:.0f}/100" if score is not None else "N/A"
    text = (
        f"🔔 <b>Approval Needed</b>\n\n"
        f"<b>Job:</b> {job_title} @ {company}\n"
        f"<b>Match Score:</b> {score_str}\n\n"
        f"<b>Draft Message:</b>\n{draft_message[:500]}{'...' if len(draft_message) > 500 else ''}\n\n"
        f"Open the app to approve or reject."
    )
    return await send_message(text)

async def notify_approval_result(job_title: str, company: str, action: str) -> bool:
    emoji = "✅" if action == "approved" else "❌"
    text = f"{emoji} Application <b>{action}</b>: {job_title} @ {company}"
    return await send_message(text)

async def test_connection() -> dict:
    """Test Telegram config. Returns {ok: bool, configured: bool, error: str | None}."""
    if not _is_configured():
        return {"ok": False, "configured": False, "error": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set"}
    sent = await send_message("✅ Job CRM notification test — connection working!")
    if sent:
        return {"ok": True, "configured": True, "error": None}
    return {"ok": False, "configured": True, "error": "Failed to send message — check token and chat_id"}
