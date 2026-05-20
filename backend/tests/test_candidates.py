import io
import os
import struct
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_candidate(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/candidates/",
        json={"name": "Jane Doe", "email": "jane@example.com", "phone": "123456"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Jane Doe"
    assert data["email"] == "jane@example.com"
    assert data["preferences"] is None


@pytest.mark.asyncio
async def test_create_candidate_duplicate_email(client: AsyncClient, auth_headers: dict):
    payload = {"name": "Jane", "email": "jane@example.com"}
    await client.post("/api/v1/candidates/", json=payload, headers=auth_headers)
    resp = await client.post("/api/v1/candidates/", json=payload, headers=auth_headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_candidate(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/candidates/",
        json={"name": "Bob", "email": "bob@example.com"},
        headers=auth_headers,
    )
    cid = create.json()["id"]
    resp = await client.get(f"/api/v1/candidates/{cid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == cid


@pytest.mark.asyncio
async def test_get_candidate_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/v1/candidates/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_candidate(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/candidates/",
        json={"name": "Old Name", "email": "update@example.com"},
        headers=auth_headers,
    )
    cid = create.json()["id"]
    resp = await client.patch(
        f"/api/v1/candidates/{cid}",
        json={"name": "New Name"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_upsert_preferences(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/candidates/",
        json={"name": "Pref User", "email": "pref@example.com"},
        headers=auth_headers,
    )
    cid = create.json()["id"]

    prefs = {
        "target_titles": ["Engineer", "Developer"],
        "target_cities": ["Beijing"],
        "min_salary": 20000,
        "max_salary": 40000,
        "remote_ok": True,
        "full_time_only": True,
        "excluded_companies": [],
        "preferred_industries": ["Tech"],
    }
    resp = await client.put(
        f"/api/v1/candidates/{cid}/preferences", json=prefs, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_titles"] == ["Engineer", "Developer"]
    assert data["min_salary"] == 20000

    # Upsert again — update
    resp2 = await client.put(
        f"/api/v1/candidates/{cid}/preferences",
        json={**prefs, "min_salary": 25000},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["min_salary"] == 25000


@pytest.mark.asyncio
async def test_upload_cv(client: AsyncClient, auth_headers: dict, tmp_path):
    """Upload a minimal PDF file and verify text extraction runs."""
    create = await client.post(
        "/api/v1/candidates/",
        json={"name": "CV User", "email": "cvuser@example.com"},
        headers=auth_headers,
    )
    cid = create.json()["id"]

    # Minimal valid PDF bytes
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj
2 0 obj<</Type /Pages /Kids[3 0 R] /Count 1>>endobj
3 0 obj<</Type /Page /Parent 2 0 R /MediaBox[0 0 612 792]>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000052 00000 n
0000000101 00000 n
trailer<</Size 4 /Root 1 0 R>>
startxref
168
%%EOF"""

    # Override the upload dir to tmp_path for tests
    import app.core.config as cfg_mod
    original_dir = cfg_mod.settings.CV_UPLOAD_DIR
    cfg_mod.settings.CV_UPLOAD_DIR = str(tmp_path)

    try:
        resp = await client.post(
            f"/api/v1/candidates/{cid}/cv",
            files={"file": ("test_cv.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=auth_headers,
        )
    finally:
        cfg_mod.settings.CV_UPLOAD_DIR = original_dir

    assert resp.status_code == 200
    data = resp.json()
    assert data["cv_file_path"] is not None
    assert data["cv_parsed_json"] is not None
