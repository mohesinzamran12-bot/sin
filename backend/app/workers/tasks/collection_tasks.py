"""Celery tasks for job collection from BOSS Zhipin."""
import asyncio
from datetime import datetime, timezone

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="tasks.collect_jobs", bind=True, max_retries=0)
def collect_jobs_task(self, candidate_id: str) -> dict:
    """
    Collect jobs from BOSS Zhipin for a given candidate.
    Returns {collected: N, new: M, errors: [...], skipped_reason: str | None}
    """
    return asyncio.run(_collect_async(candidate_id))


async def _collect_async(candidate_id: str) -> dict:
    import uuid as uuid_lib
    from sqlmodel import select, func
    from app.core.database import async_session_factory
    from app.models.browser import BrowserSession
    from app.models.candidate import Candidate, JobPreferences
    from app.models.job import Job
    from app.models.system import SystemEvent
    from app.core.config import settings
    from playwright_worker.session_store import decrypt_cookies
    from playwright_worker.browser_manager import get_browser_context
    from playwright_worker.boss_scraper import collect_jobs, CaptchaDetectedError, SessionInvalidError

    async with async_session_factory() as session:
        # --- Daily run limit check ---
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        run_count_result = await session.execute(
            select(func.count()).select_from(SystemEvent).where(
                SystemEvent.source == "collection",
                SystemEvent.level == "info",
                SystemEvent.message == "collection_started",
                SystemEvent.created_at >= today_start,
            )
        )
        run_count = run_count_result.scalar_one()
        if run_count >= settings.MAX_COLLECTION_RUNS_PER_DAY:
            reason = f"Daily collection limit reached ({settings.MAX_COLLECTION_RUNS_PER_DAY} runs)"
            logger.warning("collection_skipped", reason=reason)
            return {"collected": 0, "new": 0, "errors": [], "skipped_reason": reason}

        # --- Log run start ---
        start_event = SystemEvent(
            level="info", source="collection",
            message="collection_started",
            event_metadata={"candidate_id": candidate_id},
        )
        session.add(start_event)
        await session.commit()

        # --- Load candidate & preferences ---
        cand_result = await session.execute(
            select(Candidate).where(Candidate.id == uuid_lib.UUID(candidate_id))
        )
        candidate = cand_result.scalar_one_or_none()
        if not candidate:
            return {"collected": 0, "new": 0, "errors": ["Candidate not found"], "skipped_reason": None}

        prefs_result = await session.execute(
            select(JobPreferences).where(JobPreferences.candidate_id == candidate.id)
        )
        prefs = prefs_result.scalar_one_or_none()
        search_queries = (prefs.target_titles if prefs and prefs.target_titles else ["Python developer"])
        cities = (prefs.target_cities if prefs and prefs.target_cities else ["上海"])

        # --- Load browser session ---
        sess_result = await session.execute(
            select(BrowserSession).where(
                BrowserSession.platform == "boss_zhipin",
                BrowserSession.is_valid == True,
            ).order_by(BrowserSession.created_at.desc())
        )
        browser_session = sess_result.scalars().first()
        if not browser_session:
            return {"collected": 0, "new": 0, "errors": ["No valid BOSS Zhipin session found. Please add cookies in Settings."], "skipped_reason": None}

        cookies = decrypt_cookies(browser_session.cookies_encrypted)

        # --- Run Playwright ---
        errors: list[str] = []
        scraped = []
        try:
            async with get_browser_context(
                cookies=cookies,
                user_agent=browser_session.user_agent or None,
            ) as (browser, context):
                page = await context.new_page()
                scraped = await collect_jobs(page, search_queries, cities)
        except CaptchaDetectedError as e:
            errors.append(f"CAPTCHA detected: {e}")
            # Invalidate session and notify
            browser_session.is_valid = False
            session.add(browser_session)
            await session.commit()
            # Send Telegram notification
            try:
                from app.services.notification_service import send_message
                await send_message("⚠️ BOSS Zhipin job collection paused: CAPTCHA detected. Please update your session in Settings.")
            except Exception:
                pass
            return {"collected": 0, "new": 0, "errors": errors, "skipped_reason": None}
        except SessionInvalidError as e:
            errors.append(f"Session invalid: {e}")
            browser_session.is_valid = False
            session.add(browser_session)
            await session.commit()
            return {"collected": 0, "new": 0, "errors": errors, "skipped_reason": None}
        except Exception as e:
            errors.append(f"Unexpected error: {e}")
            logger.error("collection_error", error=str(e))
            return {"collected": 0, "new": 0, "errors": errors, "skipped_reason": None}

        # Update last_used_at
        browser_session.last_used_at = datetime.now(timezone.utc)
        session.add(browser_session)

        # --- Upsert jobs ---
        new_count = 0
        for s in scraped:
            existing = (await session.execute(
                select(Job).where(Job.external_id == s.external_id)
            )).scalar_one_or_none()
            if existing:
                # Update if needed
                existing.is_active = True
                existing.salary_range = s.salary_range or existing.salary_range
                session.add(existing)
            else:
                job = Job(
                    external_id=s.external_id,
                    source=s.source,
                    title=s.title,
                    company_name=s.company_name,
                    city=s.city,
                    salary_range=s.salary_range,
                    description=s.description or s.raw_snippet,
                    url=s.url,
                    collected_at=datetime.now(timezone.utc),
                    is_active=True,
                )
                session.add(job)
                new_count += 1

        # Log completion
        end_event = SystemEvent(
            level="info", source="collection",
            message="collection_completed",
            event_metadata={
                "candidate_id": candidate_id,
                "collected": len(scraped),
                "new": new_count,
                "errors": errors,
            },
        )
        session.add(end_event)
        await session.commit()

        logger.info("collection_done", total=len(scraped), new=new_count)
        return {"collected": len(scraped), "new": new_count, "errors": errors, "skipped_reason": None}
