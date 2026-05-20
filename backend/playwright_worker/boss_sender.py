"""
BOSS Zhipin message sender and conversation sync.

Safety rules:
- Only called after application is human-approved
- Daily send limit enforced at task level (not here)
- CAPTCHA → raise CaptchaDetectedError immediately
- Human-like typing delays
- No CAPTCHA solving
"""
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

from playwright.async_api import Page

from app.core.logging import get_logger
from playwright_worker.boss_scraper import (
    BOSS_BASE,
    CaptchaDetectedError,
    _check_captcha,
)
from playwright_worker.browser_manager import human_delay

logger = get_logger(__name__)

BOSS_CHAT_URL = "https://www.zhipin.com/web/geek/chat"


@dataclass
class SentResult:
    success: bool
    boss_chat_id: Optional[str]  # conversation/encryptJobId from URL
    error: Optional[str] = None


@dataclass
class ConversationMessage:
    direction: str          # "inbound" | "outbound"
    body: str
    sender_name: str
    sent_at: datetime


async def _type_message(page: Page, selector: str, text: str) -> None:
    """Type a message with human-like character delays."""
    import asyncio
    import random
    el = page.locator(selector).first
    await el.click()
    await human_delay()
    # Type in small chunks to simulate human typing
    chunk_size = random.randint(5, 15)
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        await el.type(chunk, delay=random.randint(30, 100))
        if random.random() < 0.2:  # occasional pause
            await asyncio.sleep(random.uniform(0.3, 0.8))


async def send_message_to_job(
    page: Page,
    job_url: str,
    message: str,
) -> SentResult:
    """
    Navigate to a BOSS job posting and send an initial application message.

    Flow:
    1. Go to job URL
    2. Click the contact/chat button
    3. Wait for chat input
    4. Type the message with human delays
    5. Click send
    6. Extract chat ID from URL

    Returns SentResult with success status and boss_chat_id.
    """
    try:
        logger.info("navigating_to_job", url=job_url)
        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        await human_delay()
        await _check_captcha(page)

        # Try multiple selectors for the contact button
        contact_selectors = [
            "button:has-text('立即沟通')",
            "button:has-text('与TA沟通')",
            "button:has-text('沟通')",
            ".btn-startchat",
            ".op-btn-chat",
            "[class*='chat-btn']",
        ]
        clicked = False
        for sel in contact_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    clicked = True
                    logger.info("contact_button_clicked", selector=sel)
                    break
            except Exception:
                continue

        if not clicked:
            return SentResult(
                success=False,
                boss_chat_id=None,
                error="Could not find contact button on job page",
            )

        await human_delay()
        await _check_captcha(page)

        # Wait for chat input to appear
        input_selectors = [
            "textarea.chat-input",
            "textarea[placeholder*='输入']",
            ".input-area textarea",
            "[class*='chat'] textarea",
            "div[contenteditable='true']",
        ]
        input_found = False
        for sel in input_selectors:
            try:
                await page.wait_for_selector(sel, timeout=8000)
                input_found = True
                await _type_message(page, sel, message)
                break
            except Exception:
                continue

        if not input_found:
            return SentResult(
                success=False,
                boss_chat_id=None,
                error="Chat input not found after clicking contact",
            )

        await human_delay()

        # Click send button
        send_selectors = [
            "button:has-text('发送')",
            ".btn-send",
            "[class*='send-btn']",
            "button[type='submit']",
        ]
        sent = False
        for sel in send_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    sent = True
                    break
            except Exception:
                continue

        if not sent:
            # Try Enter key as fallback
            await page.keyboard.press("Enter")
            sent = True

        await human_delay()
        await _check_captcha(page)

        # Extract chat ID from current URL
        current_url = page.url
        boss_chat_id = None
        import re
        for pattern in [r"conversationId=([^&]+)", r"encryptJobId=([^&/]+)", r"/chat/([^?/]+)"]:
            m = re.search(pattern, current_url)
            if m:
                boss_chat_id = m.group(1)
                break

        logger.info("message_sent", boss_chat_id=boss_chat_id, url=current_url)
        return SentResult(success=True, boss_chat_id=boss_chat_id)

    except CaptchaDetectedError:
        raise
    except Exception as exc:
        logger.error("send_failed", error=str(exc))
        return SentResult(success=False, boss_chat_id=None, error=str(exc))


async def sync_conversation(
    page: Page,
    boss_chat_id: str,
) -> list[ConversationMessage]:
    """
    Sync messages for a specific conversation from BOSS chat.
    Navigate to the chat page and extract messages.
    Returns list of ConversationMessage ordered oldest-first.
    """
    try:
        chat_url = f"{BOSS_CHAT_URL}?conversationId={boss_chat_id}"
        await page.goto(chat_url, wait_until="domcontentloaded", timeout=30000)
        await human_delay()
        await _check_captcha(page)

        # Wait for messages to load
        msg_selectors = [
            ".message-content",
            ".msg-item",
            "[class*='message-item']",
            ".chat-message",
        ]
        for sel in msg_selectors:
            try:
                await page.wait_for_selector(sel, timeout=8000)
                break
            except Exception:
                continue

        messages: list[ConversationMessage] = []

        # Attempt structured extraction
        all_msgs = page.locator(".message-content, .msg-item, [class*='message-item']")
        count = await all_msgs.count()

        for i in range(count):
            msg = all_msgs.nth(i)
            # Determine direction by checking class
            cls = await msg.get_attribute("class") or ""
            direction = "outbound"
            if any(x in cls for x in ["left", "other", "their", "receive"]):
                direction = "inbound"
            elif any(x in cls for x in ["right", "self", "mine", "send"]):
                direction = "outbound"

            # Extract text
            text_el = msg.locator("p, span, .text, [class*='text']").first
            body = ""
            try:
                body = (await text_el.inner_text()).strip() if await text_el.count() > 0 else ""
                if not body:
                    body = (await msg.inner_text()).strip()
            except Exception:
                continue

            if not body or len(body) < 2:
                continue

            # Sender name
            sender_el = msg.locator(".sender-name, .name, [class*='name']").first
            sender_name = ""
            try:
                if await sender_el.count() > 0:
                    sender_name = (await sender_el.inner_text()).strip()
            except Exception:
                pass

            messages.append(ConversationMessage(
                direction=direction,
                body=body,
                sender_name=sender_name,
                sent_at=datetime.now(timezone.utc),  # BOSS timestamps vary by page version
            ))

        logger.info("conversation_synced", chat_id=boss_chat_id, message_count=len(messages))
        return messages

    except CaptchaDetectedError:
        raise
    except Exception as exc:
        logger.error("sync_failed", chat_id=boss_chat_id, error=str(exc))
        return []
