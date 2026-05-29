"""Leave request endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models.user import User
from app.services import notify


def _create_crew(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/crew",
        json={
            "employee_no": "P010",
            "first_name": "Asha",
            "last_name": "Kamau",
            "role": "FO",
            "date_of_hire": "2021-04-01",
            "date_of_birth": "1992-07-10",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    )
    return resp.json()["id"]


def test_leave_decision_notifies_crew(
    auth_client: tuple[TestClient, User], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = auth_client
    crew_id = _create_crew(client)
    leave_id = client.post(
        "/api/v1/leave",
        json={
            "crew_id": crew_id,
            "type": "ANNUAL",
            "date_from": "2026-07-01",
            "date_to": "2026-07-07",
        },
    ).json()["id"]

    captured: list[dict] = []

    def _spy(session, *, crew_id, subject, body):  # type: ignore[no-untyped-def]
        captured.append({"crew_id": str(crew_id), "subject": subject, "body": body})
        return 0

    monkeypatch.setattr(notify, "notify_crew_member", _spy)

    resp = client.patch(f"/api/v1/leave/{leave_id}", json={"status": "APPROVED"})
    assert resp.status_code == 200, resp.text
    assert len(captured) == 1
    assert captured[0]["crew_id"] == crew_id
    assert "approved" in captured[0]["subject"].lower()


def test_submit_list_and_approve_leave(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew_id = _create_crew(client)

    resp = client.post(
        "/api/v1/leave",
        json={
            "crew_id": crew_id,
            "type": "ANNUAL",
            "date_from": "2026-07-01",
            "date_to": "2026-07-07",
            "note": "Family event",
        },
    )
    assert resp.status_code == 201, resp.text
    leave_id = resp.json()["id"]
    assert resp.json()["status"] == "PENDING"

    pending = client.get("/api/v1/leave", params={"status": "PENDING"}).json()
    assert len(pending) == 1

    decided = client.patch(
        f"/api/v1/leave/{leave_id}",
        json={"status": "APPROVED"},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "APPROVED"
    assert decided.json()["approver_id"] is not None


def test_leave_decision_writes_audit_event(
    auth_client: tuple[TestClient, User], db_session
) -> None:
    client, _ = auth_client
    crew_id = _create_crew(client)
    leave = client.post(
        "/api/v1/leave",
        json={
            "crew_id": crew_id,
            "type": "ANNUAL",
            "date_from": "2026-07-01",
            "date_to": "2026-07-07",
        },
    ).json()
    client.patch(f"/api/v1/leave/{leave['id']}", json={"status": "REJECTED"})

    from app.models import AuditEvent

    db_session.expire_all()
    actions = {e.action for e in db_session.query(AuditEvent).all()}
    assert "SUBMIT_LEAVE" in actions
    assert "LEAVE_REJECTED" in actions
