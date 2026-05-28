"""Crew + currency endpoints."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.user import User


def _crew_payload(employee_no: str = "P001") -> dict:
    return {
        "employee_no": employee_no,
        "first_name": "Amani",
        "last_name": "Otieno",
        "role": "CAPT",
        "date_of_hire": "2020-01-15",
        "date_of_birth": "1985-03-22",
        "base_station": "HKJK",
        "contract_type": "FULL_TIME",
        "active": True,
        "languages": ["en", "sw"],
        "faith_observance_flags": {},
    }


def test_create_and_list_crew(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.post("/api/v1/crew", json=_crew_payload())
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["employee_no"] == "P001"
    assert created["role"] == "CAPT"

    resp = client.get("/api/v1/crew")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["employee_no"] == "P001"


def test_get_and_patch_crew(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    created = client.post("/api/v1/crew", json=_crew_payload()).json()
    crew_id = created["id"]

    fetched = client.get(f"/api/v1/crew/{crew_id}")
    assert fetched.status_code == 200

    patch = client.patch(
        f"/api/v1/crew/{crew_id}",
        json={"base_station": "HKWJ"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["base_station"] == "HKWJ"


def test_currency_dashboard_returns_traffic_light(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    created = client.post("/api/v1/crew", json=_crew_payload()).json()
    crew_id = created["id"]

    today = date.today()
    # GREEN, AMBER, RED currencies.
    for label, expires in (
        ("GREEN", today + timedelta(days=200)),
        ("AMBER", today + timedelta(days=15)),
        ("RED", today - timedelta(days=5)),
    ):
        resp = client.post(
            f"/api/v1/crew/{crew_id}/currency",
            json={
                "currency_type": "OPC",
                "last_completed_date": (today - timedelta(days=30)).isoformat(),
                "expires_date": expires.isoformat(),
                "evidence_ref": label,
            },
        )
        assert resp.status_code == 201, resp.text

    resp = client.get("/api/v1/crew/currency/dashboard")
    assert resp.status_code == 200, resp.text
    states = sorted(r["state"] for r in resp.json())
    assert states == ["AMBER", "GREEN", "RED"]


def test_crew_create_writes_audit_event(auth_client: tuple[TestClient, User], db_session) -> None:
    client, _user = auth_client
    client.post("/api/v1/crew", json=_crew_payload()).raise_for_status()

    from app.models import AuditEvent  # local import to avoid module-level DB

    db_session.expire_all()
    events = db_session.query(AuditEvent).filter_by(action="CREATE_CREW").all()
    assert len(events) == 1
    assert events[0].entity_type == "crew"
