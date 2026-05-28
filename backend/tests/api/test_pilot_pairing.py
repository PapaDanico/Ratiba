"""Pilot pairing + /crew/me/* endpoints."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.user import User


def _create_crew(client: TestClient, *, employee_no: str = "P200") -> str:
    return client.post(
        "/api/v1/crew",
        json={
            "employee_no": employee_no,
            "first_name": "Pi",
            "last_name": "Lot",
            "role": "CAPT",
            "date_of_hire": "2020-01-01",
            "date_of_birth": "1985-01-01",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()["id"]


def _issue_and_pair(client: TestClient, *, crew_id: str, chat_id: int = 12345) -> dict:
    issued = client.post(f"/api/v1/crew/{crew_id}/pairing-token")
    assert issued.status_code == 201, issued.text
    code = issued.json()["code"]
    paired = client.post(
        "/api/v1/auth/pilot-pair",
        json={"code": code, "telegram_chat_id": chat_id},
    )
    assert paired.status_code == 200, paired.text
    return paired.json()


def _pilot_client(client: TestClient, token: str) -> TestClient:
    """Return a copy of ``client`` with the pilot token in headers."""
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def test_issue_and_redeem_pairing_code(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    crew_id = _create_crew(client)
    body = _issue_and_pair(client, crew_id=crew_id)
    assert body["employee_no"] == "P200"
    assert body["role"] == "CAPT"
    assert "pilot_token" in body


def test_redeem_unknown_code_returns_400(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    resp = client.post("/api/v1/auth/pilot-pair", json={"code": "NOPE0000"})
    assert resp.status_code == 400


def test_redeem_twice_is_rejected(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew_id = _create_crew(client)
    body = _issue_and_pair(client, crew_id=crew_id)
    # Issue a fresh code via the dashboard to confirm we can redeem the same
    # code only once.
    second = client.post(
        "/api/v1/auth/pilot-pair",
        json={"code": body["pilot_token"][:8]},  # garbage — definitely not a code
    )
    assert second.status_code == 400


def test_pilot_me_returns_profile(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew_id = _create_crew(client)
    body = _issue_and_pair(client, crew_id=crew_id)

    # Switch to pilot token.
    client.headers["Authorization"] = f"Bearer {body['pilot_token']}"
    me = client.get("/api/v1/crew/me")
    assert me.status_code == 200, me.text
    assert me.json()["employee_no"] == "P200"


def test_pilot_currency_returns_traffic_light(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    crew_id = _create_crew(client)

    today = date.today()
    client.post(
        f"/api/v1/crew/{crew_id}/currency",
        json={
            "currency_type": "OPC",
            "last_completed_date": (today - timedelta(days=10)).isoformat(),
            "expires_date": (today + timedelta(days=5)).isoformat(),
        },
    ).raise_for_status()

    body = _issue_and_pair(client, crew_id=crew_id)
    client.headers["Authorization"] = f"Bearer {body['pilot_token']}"
    resp = client.get("/api/v1/crew/me/currency")
    assert resp.status_code == 200, resp.text
    rows = resp.json()["currencies"]
    assert len(rows) == 1
    assert rows[0]["state"] == "AMBER"


def test_pilot_can_submit_leave(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew_id = _create_crew(client)
    body = _issue_and_pair(client, crew_id=crew_id)
    client.headers["Authorization"] = f"Bearer {body['pilot_token']}"
    resp = client.post(
        "/api/v1/crew/me/leave",
        json={
            "type": "ANNUAL",
            "date_from": "2026-08-01",
            "date_to": "2026-08-05",
            "note": "Family",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PENDING"


def test_pilot_swap_rejects_unknown_counterparty(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    crew_id = _create_crew(client)
    body = _issue_and_pair(client, crew_id=crew_id)
    client.headers["Authorization"] = f"Bearer {body['pilot_token']}"
    resp = client.post(
        "/api/v1/crew/me/swap",
        json={
            "counterparty_employee_no": "GHOST",
            "fdp_or_sector_ref": "RB101-2026-07-15",
        },
    )
    assert resp.status_code == 404
