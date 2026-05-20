"""Tests for conversation endpoints and send API."""
import pytest
import uuid
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_conversations_empty(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/conversations/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_send_requires_approved_status(client: AsyncClient, auth_headers, mock_claude):
    """Send endpoint must reject applications not in 'approved' status."""
    job_resp = await client.post("/api/v1/jobs/", json={
        "title": "Engineer", "company_name": "Corp"
    }, headers=auth_headers)
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    cand_resp = await client.post("/api/v1/candidates/", json={
        "name": "Eve", "email": f"eve-{uuid.uuid4()}@example.com"
    }, headers=auth_headers)
    assert cand_resp.status_code == 201
    cand_id = cand_resp.json()["id"]

    # Create application (status = pending_approval)
    app_resp = await client.post("/api/v1/applications/", json={
        "job_id": job_id, "candidate_id": cand_id
    }, headers=auth_headers)
    assert app_resp.status_code == 201
    app_id = app_resp.json()["id"]

    # Attempt to send — should fail (not approved yet)
    send_resp = await client.post(f"/api/v1/applications/{app_id}/send", headers=auth_headers)
    assert send_resp.status_code == 400
    assert "approved" in send_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_send_requires_approval_queue_entry(client: AsyncClient, auth_headers, mock_claude):
    """Send endpoint must verify the approval queue entry exists and is approved."""
    job_resp = await client.post("/api/v1/jobs/", json={
        "title": "Dev", "company_name": "Startup"
    }, headers=auth_headers)
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    cand_resp = await client.post("/api/v1/candidates/", json={
        "name": "Frank", "email": f"frank-{uuid.uuid4()}@example.com"
    }, headers=auth_headers)
    assert cand_resp.status_code == 201
    cand_id = cand_resp.json()["id"]

    app_resp = await client.post("/api/v1/applications/", json={
        "job_id": job_id, "candidate_id": cand_id
    }, headers=auth_headers)
    assert app_resp.status_code == 201
    app_id = app_resp.json()["id"]

    # Manually set status to approved without going through approval queue
    patch_resp = await client.patch(f"/api/v1/applications/{app_id}", json={
        "status": "approved"
    }, headers=auth_headers)
    assert patch_resp.status_code == 200

    # Send should fail because approval queue entry is still pending
    send_resp = await client.post(f"/api/v1/applications/{app_id}/send", headers=auth_headers)
    assert send_resp.status_code == 400


@pytest.mark.asyncio
async def test_send_after_full_approval(client: AsyncClient, auth_headers, mock_claude, monkeypatch):
    """Full approved flow -> send endpoint accepts and queues task."""
    job_resp = await client.post("/api/v1/jobs/", json={
        "title": "ML Engineer", "company_name": "AI Co",
        "url": "https://www.zhipin.com/job_detail/abc123.html"
    }, headers=auth_headers)
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    cand_resp = await client.post("/api/v1/candidates/", json={
        "name": "Grace", "email": f"grace-{uuid.uuid4()}@example.com"
    }, headers=auth_headers)
    assert cand_resp.status_code == 201
    cand_id = cand_resp.json()["id"]

    app_resp = await client.post("/api/v1/applications/", json={
        "job_id": job_id, "candidate_id": cand_id
    }, headers=auth_headers)
    assert app_resp.status_code == 201
    app_id = app_resp.json()["id"]

    # Approve via approval queue
    approvals_resp = await client.get("/api/v1/approvals/", headers=auth_headers)
    assert approvals_resp.status_code == 200
    approval_id = next(
        a["id"] for a in approvals_resp.json()["items"] if a["application_id"] == app_id
    )
    approve_resp = await client.post(
        f"/api/v1/approvals/{approval_id}/approve", json={}, headers=auth_headers
    )
    assert approve_resp.status_code == 200

    # Mock the Celery task
    class FakeTask:
        id = "send-task-id"

    import app.workers.tasks.send_tasks as st
    monkeypatch.setattr(st.send_application_message_task, "delay", lambda *a, **kw: FakeTask())

    send_resp = await client.post(f"/api/v1/applications/{app_id}/send", headers=auth_headers)
    assert send_resp.status_code == 202
    assert send_resp.json()["task_id"] == "send-task-id"


@pytest.mark.asyncio
async def test_sync_trigger(client: AsyncClient, auth_headers, monkeypatch):
    """Sync endpoint should accept and queue a task."""
    cand_resp = await client.post("/api/v1/candidates/", json={
        "name": "Hank", "email": f"hank-{uuid.uuid4()}@example.com"
    }, headers=auth_headers)
    assert cand_resp.status_code == 201
    cand_id = cand_resp.json()["id"]

    class FakeTask:
        id = "sync-task-id"

    import app.workers.tasks.send_tasks as st
    monkeypatch.setattr(st.sync_conversations_task, "delay", lambda *a, **kw: FakeTask())

    resp = await client.post("/api/v1/conversations/sync", json={
        "candidate_id": cand_id
    }, headers=auth_headers)
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_list_conversations_filter(client: AsyncClient, auth_headers):
    """reply_needed filter should work."""
    resp = await client.get("/api/v1/conversations/?reply_needed=true", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
