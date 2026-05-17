"""Underwriter proposal table API (requires PostgreSQL)."""

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_agent_proposals_api import _minimal_valid_payload, _post_create


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def agent_token(client: TestClient) -> str:
    email = f"agent_uw_{uuid.uuid4().hex[:10]}@example.com"
    assert client.post(
        "/api/auth/register",
        json={"name": "Agent", "email": email, "password": "testpass12", "role_slug": "agent"},
    ).status_code == 201
    log = client.post(
        "/api/auth/login",
        json={"email": email, "password": "testpass12", "remember_me": False},
    )
    assert log.status_code == 200
    return log.json()["data"]["access_token"]


@pytest.fixture
def underwriter_token(client: TestClient) -> str:
    email = f"uw_{uuid.uuid4().hex[:10]}@example.com"
    assert client.post(
        "/api/auth/register",
        json={"name": "Underwriter", "email": email, "password": "testpass12", "role_slug": "underwriter"},
    ).status_code == 201
    log = client.post(
        "/api/auth/login",
        json={"email": email, "password": "testpass12", "remember_me": False},
    )
    assert log.status_code == 200
    return log.json()["data"]["access_token"]


def test_underwriter_table_lists_agent_proposals(client: TestClient, agent_token: str, underwriter_token: str):
    data, files = _minimal_valid_payload()
    cr = _post_create(
        client,
        agent_token,
        data,
        files,
        fa_number="FA-UW-TABLE-99",
        policy_type="term",
        submission_date="2026-06-01",
    )
    assert cr.status_code == 201, cr.text
    pid = cr.json()["data"]["proposal"]["id"]

    wh = {"Authorization": f"Bearer {underwriter_token}"}
    r = client.get("/api/underwriter/proposals", headers=wh, params={"limit": 20, "search": "FA-UW-TABLE"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    data = body["data"]
    assert data["total"] >= 1
    ids = {row["id"] for row in data["items"]}
    assert pid in ids
    row = next(x for x in data["items"] if x["id"] == pid)
    assert row["fa_number"] == "FA-UW-TABLE-99"
    assert row["document_count"] == 2
    assert "email" in row["creator"]


def test_underwriter_get_detail_and_download_document(
    client: TestClient, agent_token: str, underwriter_token: str
):
    data, files = _minimal_valid_payload()
    cr = _post_create(
        client,
        agent_token,
        data,
        files,
        fa_number="FA-DETAIL-1",
        policy_type="whole_life",
        submission_date="2026-07-01",
        ocr_extracted_data='{"insured":"Test"}',
    )
    assert cr.status_code == 201, cr.text
    prop = cr.json()["data"]["proposal"]
    pid, did = prop["id"], prop["documents"][0]["id"]

    wh = {"Authorization": f"Bearer {underwriter_token}"}
    g = client.get(f"/api/underwriter/proposals/{pid}", headers=wh)
    assert g.status_code == 200, g.text
    detail = g.json()["data"]["proposal"]
    assert detail["id"] == pid
    assert detail["fa_number"] == "FA-DETAIL-1"
    assert detail["documents"][0]["ocr_extracted_data"] == {"insured": "Test"}
    assert "ocr_by_document" in detail
    assert len(detail["ocr_by_document"]) == 2
    assert detail["ocr_by_document"][0]["document_id"] == did
    assert detail["ocr_by_document"][0]["original_filename"] == "app0.png"
    assert detail["ocr_by_document"][0]["ocr_extracted_data"] == {"insured": "Test"}

    dl = client.get(f"/api/underwriter/proposals/{pid}/documents/{did}/file", headers=wh)
    assert dl.status_code == 200
    assert dl.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_underwriter_detail_not_found(client: TestClient, underwriter_token: str):
    wh = {"Authorization": f"Bearer {underwriter_token}"}
    r = client.get("/api/underwriter/proposals/999999991", headers=wh)
    assert r.status_code == 404


def test_agent_forbidden_underwriter_detail(client: TestClient, agent_token: str):
    r = client.get(
        "/api/underwriter/proposals/1",
        headers={"Authorization": f"Bearer {agent_token}"},
    )
    assert r.status_code == 403


def test_agent_forbidden_on_underwriter_table(client: TestClient, agent_token: str):
    r = client.get(
        "/api/underwriter/proposals",
        headers={"Authorization": f"Bearer {agent_token}"},
    )
    assert r.status_code == 403


def test_underwriter_approve_proposal_updates_statuses(
    client: TestClient, agent_token: str, underwriter_token: str
):
    data, files = _minimal_valid_payload()
    cr = _post_create(
        client,
        agent_token,
        data,
        files,
        fa_number="FA-APPROVE-1",
        policy_type="term",
        submission_date="2026-08-01",
    )
    assert cr.status_code == 201, cr.text
    pid = cr.json()["data"]["proposal"]["id"]

    wh = {"Authorization": f"Bearer {underwriter_token}"}
    approve = client.post(f"/api/underwriter/proposals/{pid}/approve", headers=wh)
    assert approve.status_code == 200, approve.text
    body = approve.json()
    assert body["success"] is True
    proposal = body["data"]["proposal"]
    assert proposal["underwriter_status"] == "approved"
    assert proposal["final_status"] == "closed_approved"

    table = client.get("/api/underwriter/proposals", headers=wh, params={"search": "FA-APPROVE-1"})
    assert table.status_code == 200
    row = next(x for x in table.json()["data"]["items"] if x["id"] == pid)
    assert row["underwriter_status"] == "approved"
    assert row["final_status"] == "closed_approved"

    again = client.post(f"/api/underwriter/proposals/{pid}/approve", headers=wh)
    assert again.status_code == 200
    assert again.json()["data"]["proposal"]["underwriter_status"] == "approved"


def test_underwriter_approve_not_found(client: TestClient, underwriter_token: str):
    wh = {"Authorization": f"Bearer {underwriter_token}"}
    r = client.post("/api/underwriter/proposals/999999992/approve", headers=wh)
    assert r.status_code == 404
