import pytest
from httpx import AsyncClient


JOB_PAYLOAD = {
    "title": "Backend Engineer",
    "company_name": "Acme Corp",
    "city": "Shanghai",
    "salary_range": "20k-30k",
    "salary_min": 20000,
    "salary_max": 30000,
    "description": "Build great things.",
    "requirements": "Python experience required.",
    "url": "https://example.com/job/1",
}


@pytest.mark.asyncio
async def test_create_job(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/jobs/", json=JOB_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Backend Engineer"
    assert data["source"] == "manual"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient, auth_headers: dict):
    for i in range(3):
        await client.post(
            "/api/v1/jobs/",
            json={**JOB_PAYLOAD, "title": f"Job {i}"},
            headers=auth_headers,
        )
    resp = await client.get("/api/v1/jobs/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_list_jobs_pagination(client: AsyncClient, auth_headers: dict):
    for i in range(5):
        await client.post(
            "/api/v1/jobs/",
            json={**JOB_PAYLOAD, "title": f"Job {i}"},
            headers=auth_headers,
        )
    resp = await client.get("/api/v1/jobs/?skip=0&limit=2", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_job(client: AsyncClient, auth_headers: dict):
    create = await client.post("/api/v1/jobs/", json=JOB_PAYLOAD, headers=auth_headers)
    jid = create.json()["id"]
    resp = await client.get(f"/api/v1/jobs/{jid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == jid


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_job(client: AsyncClient, auth_headers: dict):
    create = await client.post("/api/v1/jobs/", json=JOB_PAYLOAD, headers=auth_headers)
    jid = create.json()["id"]
    resp = await client.patch(
        f"/api/v1/jobs/{jid}", json={"title": "Senior Engineer"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Senior Engineer"


@pytest.mark.asyncio
async def test_soft_delete_job(client: AsyncClient, auth_headers: dict):
    create = await client.post("/api/v1/jobs/", json=JOB_PAYLOAD, headers=auth_headers)
    jid = create.json()["id"]

    resp = await client.delete(f"/api/v1/jobs/{jid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Should not appear in active-only list
    list_resp = await client.get("/api/v1/jobs/?is_active=true", headers=auth_headers)
    ids = [j["id"] for j in list_resp.json()["items"]]
    assert jid not in ids
