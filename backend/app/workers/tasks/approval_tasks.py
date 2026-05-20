import asyncio
from datetime import datetime, timezone, timedelta
from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.expire_old_approvals", ignore_result=True)
def expire_old_approvals() -> None:
    """Mark approval queue entries older than 24h as expired. Runs periodically."""
    asyncio.run(_expire_async())


async def _expire_async() -> None:
    from sqlmodel import select
    from app.core.database import async_session_factory
    from app.models.approval import ApprovalQueue

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    async with async_session_factory() as session:
        result = await session.execute(
            select(ApprovalQueue).where(
                ApprovalQueue.status == "pending",
                ApprovalQueue.created_at < cutoff,
            )
        )
        expired = result.scalars().all()
        for entry in expired:
            entry.status = "expired"
            entry.reviewed_at = datetime.now(timezone.utc)
            session.add(entry)
        await session.commit()
