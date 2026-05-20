import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationListResponse, ConversationRead, SyncRequest

router = APIRouter()


@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    application_id: uuid.UUID | None = Query(default=None),
    reply_needed: bool | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> ConversationListResponse:
    query = select(Conversation)
    count_query = select(func.count()).select_from(Conversation)

    if application_id:
        query = query.where(Conversation.application_id == application_id)
        count_query = count_query.where(Conversation.application_id == application_id)
    if reply_needed is not None:
        query = query.where(Conversation.reply_needed == reply_needed)
        count_query = count_query.where(Conversation.reply_needed == reply_needed)

    total = (await session.execute(count_query)).scalar_one()
    query = query.order_by(Conversation.sent_at.asc()).offset(skip).limit(limit)
    items = (await session.execute(query)).scalars().all()

    return ConversationListResponse(
        items=[ConversationRead.model_validate(c) for c in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/{conversation_id}", response_model=ConversationRead)
async def get_conversation(
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> ConversationRead:
    conv = (await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationRead.model_validate(conv)


@router.post("/sync", status_code=202)
async def trigger_sync(
    body: SyncRequest,
    _: dict = Depends(get_current_user),
) -> dict:
    from app.workers.tasks.send_tasks import sync_conversations_task
    task = sync_conversations_task.delay(str(body.candidate_id))
    return {"task_id": task.id, "status": "queued"}
