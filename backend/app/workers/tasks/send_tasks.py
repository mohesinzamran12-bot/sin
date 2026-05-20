"""Celery tasks for message sending and conversation sync via Playwright."""
import asyncio
from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="tasks.send_application_message", bind=True, max_retries=0)
def send_application_message_task(self, application_id: str) -> dict:
    """Send an approved application message via Playwright. Max 10/day enforced."""
    return asyncio.run(_send_async(application_id))


@celery_app.task(name="tasks.sync_conversations", bind=True, max_retries=0)
def sync_conversations_task(self, candidate_id: str) -> dict:
    """Sync conversations for all sent applications of a candidate."""
    return asyncio.run(_sync_async(candidate_id))


async def _send_async(application_id: str) -> dict:
    import uuid as uuid_lib
    from datetime import datetime, timezone
    from sqlmodel import select, func
    from app.core.database import async_session_factory
    from app.core.config import settings
    from app.models.application import Application
    from app.models.approval import ApprovalQueue
    from app.models.job import Job
    from app.models.browser import BrowserSession
    from app.models.system import SystemEvent
    from app.models.conversation import Conversation
    from playwright_worker.session_store import decrypt_cookies
    from playwright_worker.browser_manager import get_browser_context
    from playwright_worker.boss_scraper import CaptchaDetectedError, SessionInvalidError
    from playwright_worker.boss_sender import send_message_to_job

    async with async_session_factory() as session:
        # --- Daily send limit ---
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        sent_today = (await session.execute(
            select(func.count()).select_from(SystemEvent).where(
                SystemEvent.source == "send",
                SystemEvent.message == "message_sent",
                SystemEvent.created_at >= today_start,
            )
        )).scalar_one()

        if sent_today >= settings.MAX_APPLICATIONS_PER_DAY:
            return {"success": False, "error": f"Daily send limit reached ({settings.MAX_APPLICATIONS_PER_DAY}/day)"}

        # --- Load application ---
        app_result = await session.execute(
            select(Application).where(Application.id == uuid_lib.UUID(application_id))
        )
        application = app_result.scalar_one_or_none()
        if not application:
            return {"success": False, "error": "Application not found"}

        # --- Guard: must be approved status ---
        if application.status != "approved":
            return {"success": False, "error": f"Application status is '{application.status}', must be 'approved'"}

        # --- Guard: approval queue entry must be approved ---
        approval = (await session.execute(
            select(ApprovalQueue).where(
                ApprovalQueue.application_id == application.id,
                ApprovalQueue.action == "send_application",
                ApprovalQueue.status == "approved",
            )
        )).scalar_one_or_none()
        if not approval:
            return {"success": False, "error": "No approved approval queue entry found — cannot send"}

        # --- Load job ---
        job = (await session.execute(
            select(Job).where(Job.id == application.job_id)
        )).scalar_one_or_none()
        if not job or not job.url:
            return {"success": False, "error": "Job not found or has no URL"}

        message = application.final_message or application.draft_message
        if not message:
            return {"success": False, "error": "No message to send (no final_message or draft_message)"}

        # --- Load browser session ---
        browser_session = (await session.execute(
            select(BrowserSession).where(
                BrowserSession.platform == "boss_zhipin",
                BrowserSession.is_valid == True,
            ).order_by(BrowserSession.created_at.desc())
        )).scalars().first()
        if not browser_session:
            return {"success": False, "error": "No valid browser session"}

        cookies = decrypt_cookies(browser_session.cookies_encrypted)

        # --- Run Playwright ---
        result = None
        try:
            async with get_browser_context(cookies=cookies, user_agent=browser_session.user_agent or None) as (_, context):
                page = await context.new_page()
                result = await send_message_to_job(page, job.url, message)
        except CaptchaDetectedError as e:
            browser_session.is_valid = False
            session.add(browser_session)
            await session.commit()
            try:
                from app.services.notification_service import send_message as tg
                await tg(f"CAPTCHA detected while sending application to {job.company_name}. Session invalidated.")
            except Exception:
                pass
            return {"success": False, "error": f"CAPTCHA: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

        if not result or not result.success:
            return {"success": False, "error": result.error if result else "Unknown error"}

        # --- Update application ---
        application.status = "sent"
        application.sent_at = datetime.now(timezone.utc)
        application.boss_chat_id = result.boss_chat_id
        application.updated_at = datetime.now(timezone.utc)
        browser_session.last_used_at = datetime.now(timezone.utc)
        session.add(application)
        session.add(browser_session)

        # --- Save outbound message to conversations ---
        conv = Conversation(
            application_id=application.id,
            direction="outbound",
            body=message,
            sender_name="me",
            sent_at=application.sent_at,
        )
        session.add(conv)

        # --- Log send event ---
        session.add(SystemEvent(
            level="info", source="send", message="message_sent",
            event_metadata={
                "application_id": application_id,
                "job_title": job.title,
                "company": job.company_name,
                "boss_chat_id": result.boss_chat_id,
            },
        ))
        await session.commit()

        # Telegram notification
        try:
            from app.services.notification_service import send_message as tg
            await tg(f"Application sent to {job.company_name} - {job.title}")
        except Exception:
            pass

        return {"success": True, "boss_chat_id": result.boss_chat_id}


async def _sync_async(candidate_id: str) -> dict:
    import uuid as uuid_lib
    from datetime import datetime, timezone
    from fastapi import HTTPException
    from sqlmodel import select
    from app.core.database import async_session_factory
    from app.models.application import Application
    from app.models.conversation import Conversation
    from app.models.approval import ApprovalQueue
    from app.models.browser import BrowserSession
    from app.models.system import SystemEvent
    from app.models.job import Job
    from playwright_worker.session_store import decrypt_cookies
    from playwright_worker.browser_manager import get_browser_context
    from playwright_worker.boss_scraper import CaptchaDetectedError
    from playwright_worker.boss_sender import sync_conversation
    from app.services import claude_service

    synced = 0
    new_replies = 0
    errors: list[str] = []

    async with async_session_factory() as session:
        # Load applications with boss_chat_id (sent/replied/interviewing)
        apps_result = await session.execute(
            select(Application).where(
                Application.candidate_id == uuid_lib.UUID(candidate_id),
                Application.status.in_(["sent", "replied", "interviewing"]),
                Application.boss_chat_id.isnot(None),
            )
        )
        applications = apps_result.scalars().all()

        if not applications:
            return {"synced": 0, "new_replies": 0, "errors": ["No sent applications with chat IDs"]}

        browser_session = (await session.execute(
            select(BrowserSession).where(BrowserSession.is_valid == True)
            .order_by(BrowserSession.created_at.desc())
        )).scalars().first()
        if not browser_session:
            return {"synced": 0, "new_replies": 0, "errors": ["No valid browser session"]}

        cookies = decrypt_cookies(browser_session.cookies_encrypted)

        try:
            async with get_browser_context(cookies=cookies, user_agent=browser_session.user_agent or None) as (_, context):
                page = await context.new_page()

                for app in applications:
                    try:
                        messages = await sync_conversation(page, app.boss_chat_id)
                        synced += 1

                        # Load existing message bodies to deduplicate
                        existing_result = await session.execute(
                            select(Conversation.body).where(Conversation.application_id == app.id)
                        )
                        existing_bodies = {row[0] for row in existing_result.all()}

                        # Load job for title
                        job = (await session.execute(
                            select(Job).where(Job.id == app.job_id)
                        )).scalar_one_or_none()
                        job_title = job.title if job else str(app.job_id)

                        for msg in messages:
                            if msg.body in existing_bodies:
                                continue
                            conv = Conversation(
                                application_id=app.id,
                                direction=msg.direction,
                                body=msg.body,
                                sender_name=msg.sender_name,
                                sent_at=msg.sent_at,
                            )
                            # For inbound messages, classify with Claude
                            if msg.direction == "inbound":
                                try:
                                    reply_needed, draft = await claude_service.classify_and_draft_reply(
                                        message=msg.body,
                                        job_title=job_title,
                                        session=session,
                                        application=app,
                                    )
                                    conv.reply_needed = reply_needed
                                    conv.draft_reply = draft
                                    if reply_needed:
                                        new_replies += 1
                                        # Add to approval queue
                                        approval = ApprovalQueue(
                                            application_id=app.id,
                                            action="send_reply",
                                            payload={
                                                "message": draft or "",
                                                "inbound_message": msg.body,
                                                "sender": msg.sender_name,
                                                "job_title": job_title,
                                                "company": job.company_name if job else "",
                                                "score": None,
                                            },
                                        )
                                        session.add(approval)
                                except HTTPException as e:
                                    if e.status_code == 503:
                                        errors.append("Claude API not configured — skipping classification")
                                    else:
                                        errors.append(f"Claude classification error: {e.detail}")
                                except Exception as e:
                                    errors.append(f"Claude classification error: {e}")

                            session.add(conv)
                            existing_bodies.add(msg.body)

                        # Update application status if we got inbound messages
                        inbound_count = sum(1 for m in messages if m.direction == "inbound")
                        if inbound_count > 0 and app.status == "sent":
                            app.status = "replied"
                            app.updated_at = datetime.now(timezone.utc)
                            session.add(app)

                    except CaptchaDetectedError:
                        browser_session.is_valid = False
                        session.add(browser_session)
                        errors.append("CAPTCHA detected during sync")
                        break
                    except Exception as e:
                        errors.append(f"Sync error for app {app.id}: {e}")

                browser_session.last_used_at = datetime.now(timezone.utc)
                session.add(browser_session)

        except CaptchaDetectedError:
            browser_session.is_valid = False
            session.add(browser_session)
            try:
                from app.services.notification_service import send_message as tg
                await tg("CAPTCHA detected during conversation sync. Session invalidated.")
            except Exception:
                pass
            errors.append("CAPTCHA on browser launch")

        # Notify if new replies need attention
        if new_replies > 0:
            try:
                from app.services.notification_service import send_message as tg
                await tg(f"{new_replies} new repl{'y' if new_replies == 1 else 'ies'} need your response - check Approvals.")
            except Exception:
                pass

        session.add(SystemEvent(
            level="info", source="sync",
            message="conversations_synced",
            event_metadata={"candidate_id": candidate_id, "synced": synced, "new_replies": new_replies},
        ))
        await session.commit()

    return {"synced": synced, "new_replies": new_replies, "errors": errors}
