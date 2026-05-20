import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.database import get_session
from app.core.security import create_access_token
from app.main import app

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    # Import models to register them
    from app.models import candidate, job, system, score, application, approval  # noqa: F401
    from app.models.browser import BrowserSession  # noqa: F401
    from app.models.conversation import Conversation  # noqa: F401

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture
async def session():
    async with TestSessionLocal() as s:
        yield s


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict:
    token = create_access_token({"sub": "admin@example.com"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_claude(monkeypatch):
    """Mock Claude service so tests run without a real Anthropic API key."""
    import uuid as _uuid
    from datetime import datetime, timezone
    from app.models.score import JobScore

    async def fake_score(job, candidate, session):
        s = JobScore(
            job_id=job.id,
            candidate_id=candidate.id,
            score=82.5,
            score_breakdown={"skills": 22, "experience": 20, "salary": 21, "culture": 19.5},
            match_summary="Strong match for this role.",
            strengths=["Python expertise", "FastAPI experience"],
            concerns=["Limited frontend skills"],
            model_used="claude-sonnet-4-6-mock",
            prompt_tokens=500,
            completion_tokens=200,
        )
        session.add(s)
        await session.flush()
        await session.refresh(s)
        return s

    async def fake_draft(job, candidate, score, session):
        return "您好，我对贵公司的职位非常感兴趣，希望有机会进一步交流。"

    import app.services.claude_service as cs
    monkeypatch.setattr(cs, "score_job_against_cv", fake_score)
    monkeypatch.setattr(cs, "draft_application_message", fake_draft)
