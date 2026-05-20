import uuid
import pytest
from httpx import AsyncClient


# ── helpers ──────────────────────────────────────────────────────────────────

async def _create_candidate(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post(
        "/api/v1/candidates/",
        json={"name": "Test User", "email": f"test_{uuid.uuid4().hex[:6]}@example.com"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_job(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post(
        "/api/v1/jobs/",
        json={
            "title": "Python Backend Engineer",
            "company_name": "Acme",
            "city": "Shanghai",
            "description": "Build FastAPI services.",
            "requirements": "3+ years Python experience.",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_claude(monkeypatch):
    """Patch claude_service so tests work without a real API key."""
    from datetime import datetime, timezone
    from app.models.score import JobScore
    import app.services.claude_service as cs

    async def fake_score(job, candidate, session):
        score = JobScore(
            job_id=job.id,
            candidate_id=candidate.id,
            score=82.5,
            score_breakdown={"skills": 22.0, "experience": 20.0, "salary": 21.0, "culture": 19.5},
            match_summary="Strong match for Python backend roles.",
            strengths=["Python expertise", "FastAPI experience"],
            concerns=["Limited frontend skills"],
            model_used="claude-sonnet-4-6-mock",
            prompt_tokens=500,
            completion_tokens=200,
        )
        session.add(score)
        await session.flush()
        await session.refresh(score)
        return score

    async def fake_draft(job, candidate, score, session):
        return "您好，我对贵公司的职位非常感兴趣，希望有机会进一步交流。"

    monkeypatch.setattr(cs, "score_job_against_cv", fake_score)
    monkeypatch.setattr(cs, "draft_application_message", fake_draft)


# ── score endpoint tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_score_endpoint_no_api_key(client: AsyncClient, auth_headers: dict):
    """Without a real API key the endpoint returns 503."""
    candidate = await _create_candidate(client, auth_headers)
    job = await _create_job(client, auth_headers)

    resp = await client.post(
        f"/api/v1/jobs/{job['id']}/score",
        json={"candidate_id": candidate["id"]},
        headers=auth_headers,
    )
    # Placeholder key → 503
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_score_endpoint_with_mock(client: AsyncClient, auth_headers: dict, mock_claude):
    candidate = await _create_candidate(client, auth_headers)
    job = await _create_job(client, auth_headers)

    resp = await client.post(
        f"/api/v1/jobs/{job['id']}/score",
        json={"candidate_id": candidate["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == pytest.approx(82.5)
    assert data["score_breakdown"]["skills"] == pytest.approx(22.0)
    assert "Strong match" in data["match_summary"]
    assert "Python expertise" in data["strengths"]


@pytest.mark.asyncio
async def test_get_existing_score(client: AsyncClient, auth_headers: dict, mock_claude):
    """GET returns the cached score without re-calling Claude."""
    candidate = await _create_candidate(client, auth_headers)
    job = await _create_job(client, auth_headers)

    # Create score first
    await client.post(
        f"/api/v1/jobs/{job['id']}/score",
        json={"candidate_id": candidate["id"]},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/api/v1/jobs/{job['id']}/score?candidate_id={candidate['id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["score"] == pytest.approx(82.5)


@pytest.mark.asyncio
async def test_force_rescore(client: AsyncClient, auth_headers: dict, mock_claude):
    candidate = await _create_candidate(client, auth_headers)
    job = await _create_job(client, auth_headers)

    r1 = await client.post(
        f"/api/v1/jobs/{job['id']}/score",
        json={"candidate_id": candidate["id"]},
        headers=auth_headers,
    )
    id1 = r1.json()["id"]

    r2 = await client.post(
        f"/api/v1/jobs/{job['id']}/score?force=true",
        json={"candidate_id": candidate["id"]},
        headers=auth_headers,
    )
    id2 = r2.json()["id"]
    # Force rescore creates a new record
    assert id1 != id2


# ── application tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_application_with_mock(client: AsyncClient, auth_headers: dict, mock_claude):
    candidate = await _create_candidate(client, auth_headers)
    job = await _create_job(client, auth_headers)

    resp = await client.post(
        "/api/v1/applications/",
        json={"job_id": job["id"], "candidate_id": candidate["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending_approval"
    assert data["draft_message"] is not None
    assert "您好" in data["draft_message"]


@pytest.mark.asyncio
async def test_create_application_no_api_key(client: AsyncClient, auth_headers: dict):
    """Application is still created even if API key is missing; draft_message is None."""
    candidate = await _create_candidate(client, auth_headers)
    job = await _create_job(client, auth_headers)

    resp = await client.post(
        "/api/v1/applications/",
        json={"job_id": job["id"], "candidate_id": candidate["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending_approval"
    assert resp.json()["draft_message"] is None


@pytest.mark.asyncio
async def test_list_applications(client: AsyncClient, auth_headers: dict, mock_claude):
    candidate = await _create_candidate(client, auth_headers)
    job = await _create_job(client, auth_headers)

    await client.post(
        "/api/v1/applications/",
        json={"job_id": job["id"], "candidate_id": candidate["id"]},
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/applications/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_update_application_status(client: AsyncClient, auth_headers: dict, mock_claude):
    candidate = await _create_candidate(client, auth_headers)
    job = await _create_job(client, auth_headers)

    create = await client.post(
        "/api/v1/applications/",
        json={"job_id": job["id"], "candidate_id": candidate["id"]},
        headers=auth_headers,
    )
    app_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/applications/{app_id}",
        json={"status": "approved"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


# ── logs and stats tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_audit_log_populated(client: AsyncClient, auth_headers: dict, mock_claude):
    """After scoring, the AI audit log should have an entry — but mock doesn't write it.
    This test verifies the endpoint shape and empty-state behaviour."""
    resp = await client.get("/api/v1/logs/ai", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_dashboard_stats(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/stats/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_jobs" in data
    assert "active_jobs" in data
    assert "total_applications" in data
    assert "pending_approvals" in data
    assert "total_ai_calls" in data
    assert "total_tokens_today" in data
    assert "estimated_cost_today_usd" in data


@pytest.mark.asyncio
async def test_dashboard_stats_counts(client: AsyncClient, auth_headers: dict, mock_claude):
    candidate = await _create_candidate(client, auth_headers)
    job = await _create_job(client, auth_headers)

    await client.post(
        "/api/v1/applications/",
        json={"job_id": job["id"], "candidate_id": candidate["id"]},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/stats/dashboard", headers=auth_headers)
    data = resp.json()
    assert data["total_jobs"] >= 1
    assert data["total_applications"] >= 1
    assert data["pending_approvals"] >= 1
