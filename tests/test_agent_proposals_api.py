"""Integration tests for /api/agent/proposals (requires PostgreSQL from DATABASE_URL)."""

import base64
import io
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

# 1×1 transparent PNG
_MINI_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def agent_token(client: TestClient) -> str:
    email = f"agent_api_test_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "name": "Agent API Test",
            "email": email,
            "password": "testpass12",
            "role_slug": "agent",
        },
    )
    assert reg.status_code == 201, reg.text
    log = client.post(
        "/api/auth/login",
        json={"email": email, "password": "testpass12", "remember_me": False},
    )
    assert log.status_code == 200, log.text
    body = log.json()
    assert body.get("success") is True
    return body["data"]["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_list_get_download(client: TestClient, agent_token: str):
    headers = _auth_headers(agent_token)
    files = {"document": ("scan.png", io.BytesIO(_MINI_PNG), "image/png")}
    form = {
        "fa_number": "FA-TEST-001",
        "policy_type": "term_life",
        "submission_date": "2026-05-12",
        "note": "integration note",
        "ocr_extracted_data": '{"insured":"Jane Doe","premium":120}',
    }
    create = client.post("/api/agent/proposals", headers=headers, files=files, data=form)
    assert create.status_code == 201, create.text
    cj = create.json()
    assert cj["success"] is True
    prop = cj["data"]["proposal"]
    assert prop["fa_number"] == "FA-TEST-001"
    assert prop["policy_type"] == "term_life"
    assert prop["ocr_status"] == "completed"
    assert prop["underwriter_status"] == "pending"
    assert prop["final_status"] == "open"
    assert prop["created_by_id"]
    assert len(prop["documents"]) == 1
    doc = prop["documents"][0]
    assert doc["ocr_extracted_data"] == {"insured": "Jane Doe", "premium": 120}
    pid, did = prop["id"], doc["id"]

    lst = client.get("/api/agent/proposals", headers=headers, params={"limit": 10})
    assert lst.status_code == 200, lst.text
    lj = lst.json()
    assert lj["data"]["total"] >= 1
    assert any(p["id"] == pid for p in lj["data"]["items"])

    one = client.get(f"/api/agent/proposals/{pid}", headers=headers)
    assert one.status_code == 200
    assert one.json()["data"]["proposal"]["id"] == pid

    dl = client.get(f"/api/agent/proposals/{pid}/documents/{did}/file", headers=headers)
    assert dl.status_code == 200
    assert dl.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_create_ocr_pending_without_json(client: TestClient, agent_token: str):
    headers = _auth_headers(agent_token)
    files = {"document": ("x.png", io.BytesIO(_MINI_PNG), "image/png")}
    form = {
        "fa_number": "FA-NO-OCR",
        "policy_type": "whole_life",
        "submission_date": "2026-01-01",
    }
    r = client.post("/api/agent/proposals", headers=headers, files=files, data=form)
    assert r.status_code == 201, r.text
    assert r.json()["data"]["proposal"]["ocr_status"] == "pending"


def test_cursor_params_must_pair(client: TestClient, agent_token: str):
    headers = _auth_headers(agent_token)
    r = client.get("/api/agent/proposals", headers=headers, params={"cursor_id": 1})
    assert r.status_code == 422


def test_non_agent_forbidden(client: TestClient):
    """Admin from seeder cannot call agent routes."""
    log = client.post(
        "/api/auth/login",
        json={
            "email": "admin@apptriangle.com",
            "password": "admin@3$!12313__)(",
            "remember_me": False,
        },
    )
    if log.status_code != 200:
        pytest.skip("Default admin not present or password changed")
    token = log.json()["data"]["access_token"]
    files = {"document": ("a.png", io.BytesIO(_MINI_PNG), "image/png")}
    form = {"fa_number": "X", "policy_type": "Y", "submission_date": "2026-05-01"}
    r = client.post("/api/agent/proposals", headers=_auth_headers(token), files=files, data=form)
    assert r.status_code == 403
