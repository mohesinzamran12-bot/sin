"""Tests for approval queue endpoints."""
import uuid
import pytest
from httpx import AsyncClient


# ── helpers ──────────────────────────────────────────────────────────────────

async def _make_job(client: AsyncClient, auth_headers: dict, title: str = "Backend Engineer", company: str = "TechCo") -> str:
    resp = await client.post(
        "/api/v1/jobs/",
        json={"title": title, "company_name": company, "city": "Shanghai"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _make_candidate(client: AsyncClient, auth_headers: dict, name: str = "Test User") -> str:
    resp = await client.post(
        "/api/v1/candidates/",
        json={"name": name, "email": f"{uuid.uuid4()}@example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _make_application(client: AsyncClient, auth_headers: dict, job_id: str, cand_id: str) -> str:
    resp = await client.post(
        "/api/v1/applications/",
        json={"job_id": job_id, "candidate_id": cand_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _get_approval_for_app(client: AsyncClient, auth_headers: dict, app_id: str) -> dict:
    resp = await client.get("/api/v1/approvals/", headers=auth_headers)
    assert resp.status_code == 200
    return next(a for a in resp.json()["items"] if a["application_id"] == app_id)


# ── tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_application_creates_approval_entry(
    client: AsyncClient, auth_headers: dict, mock_claude
):
    """Creating an application must auto-create a pending approval queue entry."""
    job_id = await _make_job(client, auth_headers)
    cand_id = await _make_candidate(client, auth_headers)
    app_id = await _make_application(client, auth_headers, job_id, cand_id)

    resp = await client.get("/api/v1/approvals/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    matching = [a for a in data["items"] if a["application_id"] == app_id]
    assert len(matching) == 1
    assert matching[0]["status"] == "pending"
    assert matching[0]["action"] == "send_application"
    assert matching[0]["payload"]["job_title"] == "Backend Engineer"


@pytest.mark.asyncio
async def test_approve_changes_application_status(
    client: AsyncClient, auth_headers: dict, mock_claude
):
    """Approving moves application to 'approved' and records approved_at."""
    job_id = await _make_job(client, auth_headers, "Frontend Dev", "StartupX")
    cand_id = await _make_candidate(client, auth_headers, "Alice")
    app_id = await _make_application(client, auth_headers, job_id, cand_id)
    approval = await _get_approval_for_app(client, auth_headers, app_id)

    resp = await client.post(
        f"/api/v1/approvals/{approval['id']}/approve",
        json={"notes": "Looks good"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    app_resp = await client.get(f"/api/v1/applications/{app_id}", headers=auth_headers)
    assert app_resp.json()["status"] == "approved"
    assert app_resp.json()["approved_at"] is not None


@pytest.mark.asyncio
async def test_approve_with_custom_message(
    client: AsyncClient, auth_headers: dict, mock_claude
):
    """Approving with a custom message sets final_message to that message."""
    job_id = await _make_job(client, auth_headers, "PM", "Corp")
    cand_id = await _make_candidate(client, auth_headers, "Bob")
    app_id = await _make_application(client, auth_headers, job_id, cand_id)
    approval = await _get_approval_for_app(client, auth_headers, app_id)

    custom_msg = "我对这个职位非常感兴趣，希望进一步了解。"
    resp = await client.post(
        f"/api/v1/approvals/{approval['id']}/approve",
        json={"message": custom_msg},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    app_resp = await client.get(f"/api/v1/applications/{app_id}", headers=auth_headers)
    assert app_resp.json()["final_message"] == custom_msg


@pytest.mark.asyncio
async def test_reject_changes_application_to_withdrawn(
    client: AsyncClient, auth_headers: dict, mock_claude
):
    """Rejecting moves application to 'withdrawn'."""
    job_id = await _make_job(client, auth_headers, "Data Analyst", "DataCo")
    cand_id = await _make_candidate(client, auth_headers, "Charlie")
    app_id = await _make_application(client, auth_headers, job_id, cand_id)
    approval = await _get_approval_for_app(client, auth_headers, app_id)

    resp = await client.post(
        f"/api/v1/approvals/{approval['id']}/reject",
        json={"notes": "Not a good fit"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    app_resp = await client.get(f"/api/v1/applications/{app_id}", headers=auth_headers)
    assert app_resp.json()["status"] == "withdrawn"


@pytest.mark.asyncio
async def test_double_approve_fails(
    client: AsyncClient, auth_headers: dict, mock_claude
):
    """Approving an already-approved entry must return 400."""
    job_id = await _make_job(client, auth_headers, "DevOps", "CloudCo")
    cand_id = await _make_candidate(client, auth_headers, "Dave")
    app_id = await _make_application(client, auth_headers, job_id, cand_id)
    approval = await _get_approval_for_app(client, auth_headers, app_id)

    await client.post(
        f"/api/v1/approvals/{approval['id']}/approve", json={}, headers=auth_headers
    )
    second = await client.post(
        f"/api/v1/approvals/{approval['id']}/approve", json={}, headers=auth_headers
    )
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_reject_already_approved_fails(
    client: AsyncClient, auth_headers: dict, mock_claude
):
    """Rejecting an approved entry must return 400."""
    job_id = await _make_job(client, auth_headers, "SRE", "NetCo")
    cand_id = await _make_candidate(client, auth_headers, "Eve")
    app_id = await _make_application(client, auth_headers, job_id, cand_id)
    approval = await _get_approval_for_app(client, auth_headers, app_id)

    await client.post(
        f"/api/v1/approvals/{approval['id']}/approve", json={}, headers=auth_headers
    )
    reject = await client.post(
        f"/api/v1/approvals/{approval['id']}/reject", json={}, headers=auth_headers
    )
    assert reject.status_code == 400


@pytest.mark.asyncio
async def test_notification_settings_endpoint(
    client: AsyncClient, auth_headers: dict
):
    """Notification settings endpoint returns configuration status."""
    resp = await client.get("/api/v1/notifications/settings", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "telegram_configured" in data
    assert data["telegram_configured"] is False  # no token in test env
