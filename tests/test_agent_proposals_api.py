"""Integration tests for /api/agent/proposals (requires PostgreSQL from DATABASE_URL)."""

import base64
import io
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.proposal_storage_service import ProposalStorageService

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


def _base_form(**overrides: str) -> dict[str, str]:
    data = {
        "fa_number": "FA-TEST-001",
        "policy_type": "term_life",
        "submission_date": "2026-05-12",
        "note": "integration note",
    }
    data.update(overrides)
    return data


def _application_fields(index: int = 0, doc_type: str = "application_form") -> tuple[dict[str, str], list]:
    data = {f"application_documents[{index}][document_type]": doc_type}
    files = [
        (
            f"application_documents[{index}][file]",
            (f"app{index}.png", io.BytesIO(_MINI_PNG), "image/png"),
        ),
    ]
    return data, files


def _applicant_fields(
    index: int,
    doc_type: str,
    side: str | None = None,
    filename: str | None = None,
) -> tuple[dict[str, str], list]:
    fname = filename or f"{doc_type}_{index}.png"
    data = {f"applicant_documents[{index}][document_type]": doc_type}
    if side is not None:
        data[f"applicant_documents[{index}][side]"] = side
    files = [(f"applicant_documents[{index}][file]", (fname, io.BytesIO(_MINI_PNG), "image/png"))]
    return data, files


def _merge_payload(*parts: tuple[dict[str, str], list]) -> tuple[dict[str, str], list]:
    data: dict[str, str] = {}
    files: list = []
    for d, f in parts:
        data.update(d)
        files.extend(f)
    return data, files


def _minimal_valid_payload() -> tuple[dict[str, str], list]:
    return _merge_payload(_application_fields(0), _applicant_fields(0, "birth_certificate"))


def _post_create(client, token, data, files, **form_overrides):
    merged = {**_base_form(**form_overrides), **data}
    return client.post(
        "/api/agent/proposals",
        headers=_auth_headers(token),
        data=merged,
        files=files,
    )


def test_create_with_application_documents(client: TestClient, agent_token: str):
    data, files = _merge_payload(_application_fields(0, "application_form"), _applicant_fields(0, "ssc_certificate"))
    r = _post_create(client, agent_token, data, files)
    assert r.status_code == 201, r.text
    app_docs = [d for d in r.json()["data"]["proposal"]["documents"] if d["section_type"] == "application"]
    assert len(app_docs) == 1
    assert app_docs[0]["document_type"] == "application_form"


def test_create_applicant_nid_front_back(client: TestClient, agent_token: str):
    data, files = _merge_payload(
        _application_fields(0),
        _applicant_fields(0, "nid", "front", "nid_front.png"),
        _applicant_fields(1, "nid", "back", "nid_back.png"),
    )
    r = _post_create(client, agent_token, data, files, fa_number="FA-NID-FB")
    assert r.status_code == 201, r.text
    docs = [d for d in r.json()["data"]["proposal"]["documents"] if d["section_type"] == "applicant"]
    assert len(docs) == 2
    assert {d["side"] for d in docs} == {"front", "back"}
    assert len({d["document_group_id"] for d in docs}) == 1


def test_create_applicant_photo(client: TestClient, agent_token: str):
    data, files = _merge_payload(
        _application_fields(0),
        _applicant_fields(0, "birth_certificate"),
        _applicant_fields(1, "photo", filename="applicant_photo.png"),
    )
    r = _post_create(client, agent_token, data, files, fa_number="FA-APP-PHOTO")
    assert r.status_code == 201, r.text
    app_docs = [d for d in r.json()["data"]["proposal"]["documents"] if d["section_type"] == "applicant"]
    assert len(app_docs) == 2
    photo = [d for d in app_docs if d["document_type"] == "photo"]
    assert len(photo) == 1
    assert photo[0]["side"] is None


def test_reject_applicant_photo_only(client: TestClient, agent_token: str):
    data, files = _merge_payload(_application_fields(0), _applicant_fields(0, "photo"))
    r = _post_create(client, agent_token, data, files, fa_number="FA-PHOTO-ONLY")
    assert r.status_code == 400
    assert "identity document" in r.json()["message"].lower()


def test_create_with_nominees(client: TestClient, agent_token: str):
    data, files = _merge_payload(_application_fields(0), _applicant_fields(0, "passport"))
    data.update(
        {
            "nominees[0][documents][0][document_type]": "nid",
            "nominees[0][documents][0][side]": "front",
            "nominees[1][documents][0][document_type]": "photo",
        }
    )
    files.extend(
        [
            ("nominees[0][documents][0][file]", ("n0.png", io.BytesIO(_MINI_PNG), "image/png")),
            ("nominees[1][documents][0][file]", ("n1.png", io.BytesIO(_MINI_PNG), "image/png")),
        ]
    )
    r = _post_create(client, agent_token, data, files, fa_number="FA-NOM")
    assert r.status_code == 201, r.text
    nom_docs = [d for d in r.json()["data"]["proposal"]["documents"] if d["section_type"] == "nominee"]
    assert len(nom_docs) == 2
    assert {d["nominee_index"] for d in nom_docs} == {0, 1}


def test_reject_more_than_three_nominees(client: TestClient, agent_token: str):
    data, files = _minimal_valid_payload()
    data["nominees[3][documents][0][document_type]"] = "photo"
    files.append(("nominees[3][documents][0][file]", ("x.png", io.BytesIO(_MINI_PNG), "image/png")))
    r = _post_create(client, agent_token, data, files, fa_number="FA-NOM-MAX")
    assert r.status_code == 400
    assert "nominee" in r.json()["message"].lower()


def test_reject_more_than_six_nominee_photos(client: TestClient, agent_token: str):
    data, files = _merge_payload(_application_fields(0), _applicant_fields(0, "birth_certificate"))
    for i in range(7):
        data[f"nominees[0][documents][{i}][document_type]"] = "photo"
        files.append((f"nominees[0][documents][{i}][file]", (f"p{i}.png", io.BytesIO(_MINI_PNG), "image/png")))
    r = _post_create(client, agent_token, data, files, fa_number="FA-PHOTO-MAX")
    assert r.status_code == 400
    assert "photo" in r.json()["message"].lower()


def test_reject_more_than_eight_application_documents(client: TestClient, agent_token: str):
    parts = [_application_fields(i, "supporting_document") for i in range(9)]
    parts.append(_applicant_fields(0, "birth_certificate"))
    data, files = _merge_payload(*parts)
    r = _post_create(client, agent_token, data, files, fa_number="FA-APP-MAX")
    assert r.status_code == 400
    assert "application" in r.json()["message"].lower()


def test_create_with_guardian_documents(client: TestClient, agent_token: str):
    data, files = _minimal_valid_payload()
    data.update(
        {
            "guardian_documents[0][document_type]": "nid",
            "guardian_documents[0][side]": "front",
        }
    )
    files.append(("guardian_documents[0][file]", ("g.png", io.BytesIO(_MINI_PNG), "image/png")))
    r = _post_create(client, agent_token, data, files, fa_number="FA-GUARD")
    assert r.status_code == 201, r.text
    g_docs = [d for d in r.json()["data"]["proposal"]["documents"] if d["section_type"] == "guardian"]
    assert len(g_docs) == 1
    assert g_docs[0]["side"] == "front"


def test_reject_invalid_document_type(client: TestClient, agent_token: str):
    data, files = _merge_payload(_application_fields(0), _applicant_fields(0, "invalid_type_xyz"))
    r = _post_create(client, agent_token, data, files, fa_number="FA-BAD-TYPE")
    assert r.status_code == 400
    assert "document_type" in r.json()["message"].lower()


def test_reject_side_on_birth_certificate(client: TestClient, agent_token: str):
    data, files = _merge_payload(_application_fields(0), _applicant_fields(0, "birth_certificate", side="front"))
    r = _post_create(client, agent_token, data, files, fa_number="FA-BAD-SIDE")
    assert r.status_code == 400
    assert "side" in r.json()["message"].lower()


def test_create_list_get_download(client: TestClient, agent_token: str):
    data, files = _minimal_valid_payload()
    r = _post_create(
        client,
        agent_token,
        data,
        files,
        fa_number="FA-FULL",
        ocr_extracted_data='{"insured":"Jane Doe","premium":120}',
    )
    assert r.status_code == 201, r.text
    prop = r.json()["data"]["proposal"]
    assert prop["ocr_status"] == "completed"
    assert prop["documents"][0]["ocr_extracted_data"] == {"insured": "Jane Doe", "premium": 120}
    pid, did = prop["id"], prop["documents"][0]["id"]

    lst = client.get("/api/agent/proposals", headers=_auth_headers(agent_token), params={"limit": 10})
    assert lst.status_code == 200
    assert any(p["id"] == pid for p in lst.json()["data"]["items"])

    dl = client.get(f"/api/agent/proposals/{pid}/documents/{did}/file", headers=_auth_headers(agent_token))
    assert dl.status_code == 200
    assert dl.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_create_ocr_pending_without_json(client: TestClient, agent_token: str):
    data, files = _minimal_valid_payload()
    r = _post_create(client, agent_token, data, files, fa_number="FA-NO-OCR")
    assert r.status_code == 201, r.text
    assert r.json()["data"]["proposal"]["ocr_status"] == "pending"


def test_rollback_on_upload_failure(client: TestClient, agent_token: str):
    data, files = _merge_payload(
        _application_fields(0),
        _applicant_fields(0, "birth_certificate"),
        _applicant_fields(1, "nid", "front"),
    )
    call_count = 0
    original = ProposalStorageService.persist_upload

    def flaky_persist(self, upload, proposal_id):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise ValueError("simulated storage failure")
        return original(self, upload, proposal_id)

    with patch.object(ProposalStorageService, "persist_upload", flaky_persist):
        r = _post_create(client, agent_token, data, files, fa_number="FA-ROLLBACK")
    assert r.status_code == 400
    assert "simulated" in r.json()["message"]


def test_missing_application_section(client: TestClient, agent_token: str):
    data, files = _applicant_fields(0, "birth_certificate")
    r = _post_create(client, agent_token, data, files, fa_number="FA-NO-APP")
    assert r.status_code == 400
    assert "application" in r.json()["message"].lower()


def test_missing_applicant_section(client: TestClient, agent_token: str):
    data, files = _application_fields(0)
    r = _post_create(client, agent_token, data, files, fa_number="FA-NO-APPLICANT")
    assert r.status_code == 400
    assert "applicant" in r.json()["message"].lower()


def test_cursor_params_must_pair(client: TestClient, agent_token: str):
    r = client.get("/api/agent/proposals", headers=_auth_headers(agent_token), params={"cursor_id": 1})
    assert r.status_code == 422


def test_non_agent_forbidden(client: TestClient):
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
    data, files = _minimal_valid_payload()
    r = _post_create(client, token, data, files)
    assert r.status_code == 403
