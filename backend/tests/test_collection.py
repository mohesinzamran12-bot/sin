"""Tests for collection API endpoints."""
import pytest
import uuid
from httpx import AsyncClient


def _fake_cookies() -> list[dict]:
    return [{"name": "wt2", "value": "fake_token", "domain": ".zhipin.com", "path": "/"}]


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient, auth_headers):
    resp = await client.post("/api/v1/collection/sessions", json={
        "cookies": _fake_cookies(),
        "user_agent": "Mozilla/5.0",
        "platform": "boss_zhipin",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["platform"] == "boss_zhipin"
    assert data["is_valid"] is True
    assert "cookies_encrypted" not in data  # NEVER expose encrypted cookies


@pytest.mark.asyncio
async def test_list_sessions(client: AsyncClient, auth_headers):
    await client.post("/api/v1/collection/sessions", json={
        "cookies": _fake_cookies()
    }, headers=auth_headers)
    resp = await client.get("/api/v1/collection/sessions", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_delete_session(client: AsyncClient, auth_headers):
    create_resp = await client.post("/api/v1/collection/sessions", json={
        "cookies": _fake_cookies()
    }, headers=auth_headers)
    session_id = create_resp.json()["id"]
    del_resp = await client.delete(f"/api/v1/collection/sessions/{session_id}", headers=auth_headers)
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_collection_status(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/collection/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "runs_today" in data
    assert "max_runs_per_day" in data
    assert "has_valid_session" in data


@pytest.mark.asyncio
async def test_trigger_no_session_returns_400(client: AsyncClient, auth_headers):
    """Triggering without a valid session should return 400."""
    cand_resp = await client.post("/api/v1/candidates/", json={
        "name": "Tester", "email": f"tester-{uuid.uuid4()}@example.com"
    }, headers=auth_headers)
    cand_id = cand_resp.json()["id"]
    resp = await client.post("/api/v1/collection/trigger", json={
        "candidate_id": cand_id
    }, headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_trigger_with_session(client: AsyncClient, auth_headers, monkeypatch):
    """Triggering with a valid session should queue the task (mocked)."""
    # Add a session first
    await client.post("/api/v1/collection/sessions", json={
        "cookies": _fake_cookies()
    }, headers=auth_headers)

    # Mock the Celery task
    class FakeTask:
        id = "fake-task-id"
    import app.workers.tasks.collection_tasks as ct
    monkeypatch.setattr(ct.collect_jobs_task, "delay", lambda *a, **kw: FakeTask())

    cand_resp = await client.post("/api/v1/candidates/", json={
        "name": "Tester2", "email": f"tester2-{uuid.uuid4()}@example.com"
    }, headers=auth_headers)
    cand_id = cand_resp.json()["id"]
    resp = await client.post("/api/v1/collection/trigger", json={
        "candidate_id": cand_id
    }, headers=auth_headers)
    assert resp.status_code == 202
    assert resp.json()["task_id"] == "fake-task-id"


@pytest.mark.asyncio
async def test_cookies_not_exposed(client: AsyncClient, auth_headers):
    """Cookie data must never appear in list or create responses."""
    await client.post("/api/v1/collection/sessions", json={
        "cookies": _fake_cookies()
    }, headers=auth_headers)
    list_resp = await client.get("/api/v1/collection/sessions", headers=auth_headers)
    for session in list_resp.json():
        assert "cookies" not in session
        assert "cookies_encrypted" not in session
