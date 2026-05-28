"""Training endpoints: type-rating CRUD + recurrency tracking."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.user import User


def _create_crew(client: TestClient, *, employee_no: str = "T1") -> dict:
    return client.post(
        "/api/v1/crew",
        json={
            "employee_no": employee_no,
            "first_name": "Tena",
            "last_name": "Mwangi",
            "role": "CAPT",
            "date_of_hire": "2020-01-01",
            "date_of_birth": "1985-01-01",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()


def test_add_list_delete_type_rating(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew = _create_crew(client)
    today = date.today()
    created = client.post(
        f"/api/v1/training/crew/{crew['id']}/type-ratings",
        json={
            "aircraft_type": "c208",
            "valid_from": today.isoformat(),
            "valid_until": (today + timedelta(days=200)).isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["aircraft_type"] == "C208"  # uppercased
    assert body["crew_name"] == "Tena Mwangi"
    assert body["state"] == "GREEN"

    listed = client.get("/api/v1/training/type-ratings").json()
    assert any(r["aircraft_type"] == "C208" for r in listed)

    resp = client.delete(f"/api/v1/training/type-ratings/{body['id']}")
    assert resp.status_code == 204
    assert client.get("/api/v1/training/type-ratings").json() == []


def test_type_rating_rejects_reversed_validity(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew = _create_crew(client, employee_no="T2")
    today = date.today()
    resp = client.post(
        f"/api/v1/training/crew/{crew['id']}/type-ratings",
        json={
            "aircraft_type": "AT76",
            "valid_from": today.isoformat(),
            "valid_until": (today - timedelta(days=1)).isoformat(),
        },
    )
    assert resp.status_code == 422


def test_recurrency_lists_soon_to_expire(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew = _create_crew(client, employee_no="T3")
    today = date.today()

    # Expiring in 10 days → should appear; far-future → should not (within 90d).
    client.post(
        f"/api/v1/training/crew/{crew['id']}/type-ratings",
        json={
            "aircraft_type": "C208",
            "valid_from": (today - timedelta(days=365)).isoformat(),
            "valid_until": (today + timedelta(days=10)).isoformat(),
        },
    ).raise_for_status()
    client.post(
        f"/api/v1/crew/{crew['id']}/currency",
        json={
            "currency_type": "OPC",
            "last_completed_date": today.isoformat(),
            "expires_date": (today + timedelta(days=400)).isoformat(),
        },
    ).raise_for_status()

    items = client.get("/api/v1/training/recurrency", params={"within_days": 90}).json()
    labels = {i["label"] for i in items}
    assert "Type rating: C208" in labels
    assert "OPC" not in labels  # 400 days out — beyond the 90-day window
    # AMBER because it's within 30 days.
    tr = next(i for i in items if i["label"] == "Type rating: C208")
    assert tr["state"] == "AMBER"
    assert tr["crew_name"] == "Tena Mwangi"
