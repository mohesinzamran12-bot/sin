"""
BOSS Zhipin job scraper.

Safety rules enforced here:
- Random delays between every navigation
- Hard cap: MAX_JOBS_COLLECTED_PER_RUN jobs per call
- CAPTCHA detection → raise CaptchaDetectedError immediately
- No sending, no CAPTCHA solving, no fake accounts
"""
import re
from dataclasses import dataclass, field
from typing import Optional

from playwright.async_api import Page

from app.core.config import settings
from app.core.logging import get_logger
from playwright_worker.browser_manager import human_delay

logger = get_logger(__name__)

BOSS_BASE = "https://www.zhipin.com"
BOSS_SEARCH = "https://www.zhipin.com/web/geek/job"

# City name → BOSS city code mapping (extend as needed)
CITY_CODES: dict[str, str] = {
    "北京": "101010100",
    "beijing": "101010100",
    "上海": "101020100",
    "shanghai": "101020100",
    "广州": "101280100",
    "guangzhou": "101280100",
    "深圳": "101280600",
    "shenzhen": "101280600",
    "杭州": "101210100",
    "hangzhou": "101210100",
    "成都": "101270100",
    "chengdu": "101270100",
    "武汉": "101200100",
    "wuhan": "101200100",
    "南京": "101190100",
    "nanjing": "101190100",
    "苏州": "101190400",
    "suzhou": "101190400",
    "西安": "101110100",
    "xian": "101110100",
    "全国": "100010000",
    "remote": "100010000",
}


class CaptchaDetectedError(Exception):
    """Raised when BOSS Zhipin shows a CAPTCHA challenge."""


class SessionInvalidError(Exception):
    """Raised when the stored session is no longer valid (user logged out)."""


@dataclass
class ScrapedJob:
    external_id: str
    title: str
    company_name: str
    city: str
    salary_range: str
    description: str
    requirements: str
    url: str
    source: str = "boss_zhipin"
    raw_snippet: str = ""


async def _check_captcha(page: Page) -> None:
    """Raise CaptchaDetectedError if BOSS is showing a CAPTCHA."""
    captcha_selectors = [
        "#captcha-verify-image",
        ".geetest_holder",
        ".slide-verify",
        "text=请完成安全验证",
        "text=滑动验证",
    ]
    for sel in captcha_selectors:
        try:
            if await page.locator(sel).count() > 0:
                raise CaptchaDetectedError(f"CAPTCHA detected via selector: {sel}")
        except CaptchaDetectedError:
            raise
        except Exception:
            pass


async def _check_login(page: Page) -> bool:
    """Return True if the user appears to be logged in."""
    await page.goto(BOSS_BASE, wait_until="domcontentloaded", timeout=30000)
    await human_delay()
    await _check_captcha(page)
    # Logged-in indicators on BOSS homepage
    login_indicators = [
        ".nav-figure",      # user avatar in nav
        ".user-nav",
        "[data-sentry-element='UserNav']",
    ]
    for sel in login_indicators:
        try:
            if await page.locator(sel).count() > 0:
                return True
        except Exception:
            pass
    return False


async def _extract_job_from_card(page: Page, card_index: int) -> Optional[ScrapedJob]:
    """Extract a single job from a search result card by index."""
    try:
        cards = page.locator(".job-card-wrapper, li.job-card-wrapper")
        card = cards.nth(card_index)

        # Title
        title_el = card.locator(".job-name, .job-title")
        title = (await title_el.first.inner_text()).strip() if await title_el.count() > 0 else ""
        if not title:
            return None

        # Company
        company_el = card.locator(".company-name")
        company = (await company_el.first.inner_text()).strip() if await company_el.count() > 0 else ""

        # Salary
        salary_el = card.locator(".salary")
        salary = (await salary_el.first.inner_text()).strip() if await salary_el.count() > 0 else ""

        # City / area
        area_el = card.locator(".job-area, .job-area-wrapper")
        city = (await area_el.first.inner_text()).strip() if await area_el.count() > 0 else ""
        # Clean up city (remove experience/education tags if merged)
        city = city.split("·")[0].strip()

        # Link and external ID
        link_el = card.locator("a[href*='/job_detail/']")
        href = ""
        if await link_el.count() > 0:
            href = await link_el.first.get_attribute("href") or ""
        if not href:
            link_el = card.locator("a").first
            href = await link_el.get_attribute("href") or "" if await link_el.count() > 0 else ""

        url = f"{BOSS_BASE}{href}" if href.startswith("/") else href

        # Extract job ID from URL (e.g. /job_detail/abc123.html)
        external_id_match = re.search(r"/job_detail/([^.?/]+)", href)
        external_id = external_id_match.group(1) if external_id_match else url

        if not external_id or not company:
            return None

        return ScrapedJob(
            external_id=external_id,
            title=title,
            company_name=company,
            city=city,
            salary_range=salary,
            description="",   # fetched on detail page if needed
            requirements="",
            url=url,
            raw_snippet=f"{title} | {company} | {salary} | {city}",
        )
    except Exception as exc:
        logger.warning("card_extraction_failed", index=card_index, error=str(exc))
        return None


async def collect_jobs(
    page: Page,
    search_queries: list[str],
    cities: list[str],
    max_jobs: int | None = None,
) -> list[ScrapedJob]:
    """
    Collect jobs from BOSS Zhipin search results.

    Args:
        page: Active Playwright page with valid session cookies set
        search_queries: list of job title queries (e.g. ["Python", "FastAPI developer"])
        cities: list of city names (mapped to BOSS city codes)
        max_jobs: hard cap; defaults to settings.MAX_JOBS_COLLECTED_PER_RUN

    Returns:
        List of ScrapedJob objects (deduplicated by external_id)

    Raises:
        CaptchaDetectedError: if BOSS shows a CAPTCHA at any point
        SessionInvalidError: if the session appears to be expired
    """
    cap = min(max_jobs or settings.MAX_JOBS_COLLECTED_PER_RUN, settings.MAX_JOBS_COLLECTED_PER_RUN)
    seen_ids: set[str] = set()
    results: list[ScrapedJob] = []

    # Verify login first
    logged_in = await _check_login(page)
    if not logged_in:
        raise SessionInvalidError("Not logged in to BOSS Zhipin — session may have expired")

    for query in search_queries:
        if len(results) >= cap:
            break
        for city_name in cities:
            if len(results) >= cap:
                break

            city_code = CITY_CODES.get(city_name.lower(), CITY_CODES.get(city_name, "100010000"))
            search_url = f"{BOSS_SEARCH}?query={query}&city={city_code}"

            logger.info("boss_search", query=query, city=city_name, url=search_url)
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await human_delay()
            await _check_captcha(page)

            # Wait for job cards to appear (or timeout gracefully)
            try:
                await page.wait_for_selector(
                    ".job-card-wrapper, li.job-card-wrapper",
                    timeout=10000,
                )
            except Exception:
                logger.warning("no_job_cards_found", query=query, city=city_name)
                continue

            card_count = await page.locator(".job-card-wrapper, li.job-card-wrapper").count()
            logger.info("cards_found", count=card_count, query=query)

            for i in range(card_count):
                if len(results) >= cap:
                    break
                job = await _extract_job_from_card(page, i)
                if job and job.external_id not in seen_ids:
                    seen_ids.add(job.external_id)
                    results.append(job)
                await human_delay()

            await human_delay()  # extra delay between searches

    logger.info("collection_complete", total=len(results))
    return results
