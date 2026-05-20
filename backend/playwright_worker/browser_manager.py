"""Playwright browser manager with rate limiting and safety controls."""
import asyncio
import random
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def human_delay() -> None:
    """Wait a random human-like delay between actions."""
    ms = random.randint(settings.PLAYWRIGHT_MIN_DELAY_MS, settings.PLAYWRIGHT_MAX_DELAY_MS)
    await asyncio.sleep(ms / 1000)


@asynccontextmanager
async def get_browser_context(
    cookies: list[dict] | None = None,
    user_agent: str | None = None,
) -> AsyncGenerator[tuple[Browser, BrowserContext], None]:
    """
    Async context manager that yields (browser, context).
    Applies cookies and user_agent if provided.
    Always launches headless chromium.
    """
    ua = user_agent or (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent=ua,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        # Hide webdriver flag
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        if cookies:
            await context.add_cookies(cookies)
        try:
            yield browser, context
        finally:
            await context.close()
            await browser.close()
