"""Integration tests for notification delivery and notification APIs."""

from datetime import date
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_agent_proposals_api import _minimal_valid_payload, _post_create


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _create_user_token(client: TestClient, role_slug: str, *, name: str | None = None) -> tuple[dict, str]:
    email = f"{role_slug}_{uuid.uuid4().hex[:10]}@example.com"
    display_name = name or role_slug.title()
    register = client.post(
        "/api/auth/register",
        json={
            "name": display_name,
            "email": email,
            "password": "testpass12",
            "role_slug": role_slug,
        },
    )
    assert register.status_code == 201, register.text
    user = register.json()["data"]["user"]

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "testpass12", "remember_me": False},
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["access_token"]
    return user, token


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _list_notifications(client: TestClient, token: str, **params):
    return client.get("/api/notifications", headers=_auth_headers(token), params=params)


def test_agent_create_notifies_all_underwriters(client: TestClient):
    agent, agent_token = _create_user_token(client, "agent", name="Agent One")
    _, underwriter_one_token = _create_user_token(client, "underwriter", name="Underwriter One")
    _, underwriter_two_token = _create_user_token(client, "underwriter", name="Underwriter Two")

    data, files = _minimal_valid_payload()
    created = _post_create(
        client,
        agent_token,
        data,
        files,
        fa_number="FA-NOTIFY-CREATE-1",
        submission_date="2026-09-01",
    )
    assert created.status_code == 201, created.text
    proposal = created.json()["data"]["proposal"]

    unread_one = client.get("/api/notifications/unread-count", headers=_auth_headers(underwriter_one_token))
    unread_two = client.get("/api/notifications/unread-count", headers=_auth_headers(underwriter_two_token))
    assert unread_one.status_code == 200, unread_one.text
    assert unread_two.status_code == 200, unread_two.text
    assert unread_one.json()["data"]["count"] >= 1
    assert unread_two.json()["data"]["count"] >= 1

    notifications = _list_notifications(client, underwriter_one_token, unread=True, type="proposal_created")
    assert notifications.status_code == 200, notifications.text
    items = notifications.json()["data"]["items"]
    matched = next(item for item in items if item["reference_id"] == proposal["id"])
    assert matched["type"] == "proposal_created"
    assert matched["data"]["proposal_id"] == proposal["id"]
    assert matched["data"]["fa_number"] == "FA-NOTIFY-CREATE-1"
    assert matched["data"]["actor_name"] == agent["name"]


def test_underwriter_approve_notifies_creator_and_mark_read(client: TestClient):
    _, agent_token = _create_user_token(client, "agent", name="Creator Agent")
    _, underwriter_token = _create_user_token(client, "underwriter", name="Approver")

    data, files = _minimal_valid_payload()
    created = _post_create(
        client,
        agent_token,
        data,
        files,
        fa_number="FA-NOTIFY-APPROVE-1",
        submission_date="2026-09-02",
    )
    assert created.status_code == 201, created.text
    proposal_id = created.json()["data"]["proposal"]["id"]

    approve = client.post(
        f"/api/underwriter/proposals/{proposal_id}/approve",
        headers=_auth_headers(underwriter_token),
    )
    assert approve.status_code == 200, approve.text

    unread = client.get("/api/notifications/unread-count", headers=_auth_headers(agent_token))
    assert unread.status_code == 200, unread.text
    assert unread.json()["data"]["count"] >= 1

    notifications = _list_notifications(client, agent_token, unread=True, type="proposal_approved")
    assert notifications.status_code == 200, notifications.text
    item = next(item for item in notifications.json()["data"]["items"] if item["reference_id"] == proposal_id)
    assert item["type"] == "proposal_approved"
    assert item["is_read"] is False
    assert item["data"]["decision"] == "approved"

    marked = client.patch(
        f"/api/notifications/{item['id']}/read",
        headers=_auth_headers(agent_token),
    )
    assert marked.status_code == 200, marked.text
    assert marked.json()["data"]["notification"]["is_read"] is True


def test_underwriter_reject_notifies_creator_and_supports_filters(client: TestClient):
    _, agent_token = _create_user_token(client, "agent", name="Reject Target")
    _, underwriter_token = _create_user_token(client, "underwriter", name="Rejector")

    data, files = _minimal_valid_payload()
    created = _post_create(
        client,
        agent_token,
        data,
        files,
        fa_number="FA-NOTIFY-REJECT-1",
        submission_date="2026-09-03",
    )
    assert created.status_code == 201, created.text
    proposal_id = created.json()["data"]["proposal"]["id"]

    rejected = client.post(
        f"/api/underwriter/proposals/{proposal_id}/reject",
        headers=_auth_headers(underwriter_token),
        json={"reason": "Incomplete documentation", "notes": "Missing mandatory medical report."},
    )
    assert rejected.status_code == 200, rejected.text
    proposal = rejected.json()["data"]["proposal"]
    assert proposal["underwriter_status"] == "rejected"
    assert proposal["final_status"] == "closed_rejected"

    filtered = _list_notifications(
        client,
        agent_token,
        unread=True,
        type="proposal_rejected",
        created_from=str(date.today()),
        created_to=str(date.today()),
    )
    assert filtered.status_code == 200, filtered.text
    item = next(item for item in filtered.json()["data"]["items"] if item["reference_id"] == proposal_id)
    assert item["type"] == "proposal_rejected"
    assert item["data"]["decision"] == "rejected"
    assert item["data"]["reason"] == "Incomplete documentation"
    assert item["data"]["notes"] == "Missing mandatory medical report."


def test_notification_pagination_and_mark_all_read(client: TestClient):
    _, agent_token = _create_user_token(client, "agent", name="Paged Agent")
    _, underwriter_token = _create_user_token(client, "underwriter", name="Paged Underwriter")

    for index in range(2):
        data, files = _minimal_valid_payload()
        created = _post_create(
            client,
            agent_token,
            data,
            files,
            fa_number=f"FA-NOTIFY-PAGE-{index}",
            submission_date=f"2026-09-0{index + 4}",
        )
        assert created.status_code == 201, created.text
        proposal_id = created.json()["data"]["proposal"]["id"]
        approve = client.post(
            f"/api/underwriter/proposals/{proposal_id}/approve",
            headers=_auth_headers(underwriter_token),
        )
        assert approve.status_code == 200, approve.text

    first_page = _list_notifications(client, agent_token, limit=1)
    assert first_page.status_code == 200, first_page.text
    page_data = first_page.json()["data"]
    assert len(page_data["items"]) == 1
    assert page_data["has_more"] is True
    assert page_data["next_cursor_created_at"] is not None
    assert page_data["next_cursor_id"] is not None

    second_page = _list_notifications(
        client,
        agent_token,
        limit=1,
        cursor_created_at=page_data["next_cursor_created_at"],
        cursor_id=page_data["next_cursor_id"],
    )
    assert second_page.status_code == 200, second_page.text
    assert len(second_page.json()["data"]["items"]) == 1

    mark_all = client.patch("/api/notifications/read-all", headers=_auth_headers(agent_token))
    assert mark_all.status_code == 200, mark_all.text
    assert mark_all.json()["data"]["marked_count"] >= 2

    unread = client.get("/api/notifications/unread-count", headers=_auth_headers(agent_token))
    assert unread.status_code == 200, unread.text
    assert unread.json()["data"]["count"] == 0
