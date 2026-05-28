"""Flight routing (sector) CRUD endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User


def _make_sector(client: TestClient, **overrides: object) -> dict:
    body = {
        "flight_no": "KQ410",
        "date": "2025-06-01",
        "origin": "HKJK",
        "destination": "HKMO",
        "std": "2025-06-01T08:00:00Z",
        "sta": "2025-06-01T10:00:00Z",
        "aircraft_reg": "5Y-ABC",
        "aircraft_type": "C208",
    }
    body.update(overrides)
    return client.post("/api/v1/sectors", json=body).json()


def test_create_and_list_sector(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    created = _make_sector(client)
    assert created["status"] == "PLANNED"
    assert created["origin"] == "HKJK"
    assert created["block_hours"] == 2.0

    listed = client.get(
        "/api/v1/sectors", params={"date_from": "2025-06-01", "date_to": "2025-06-30"}
    )
    assert listed.status_code == 200
    rows = listed.json()
    assert any(r["flight_no"] == "KQ410" for r in rows)


def test_inputs_are_uppercased(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    created = _make_sector(client, origin="hkjk", aircraft_reg="5y-xyz", flight_no="kq5")
    assert created["origin"] == "HKJK"
    assert created["aircraft_reg"] == "5Y-XYZ"
    assert created["flight_no"] == "KQ5"


def test_sta_before_std_rejected(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.post(
        "/api/v1/sectors",
        json={
            "flight_no": "KQ9",
            "date": "2025-06-01",
            "origin": "HKJK",
            "destination": "HKMO",
            "std": "2025-06-01T10:00:00Z",
            "sta": "2025-06-01T08:00:00Z",
            "aircraft_reg": "5Y-ABC",
            "aircraft_type": "C208",
        },
    )
    assert resp.status_code == 422


def test_delete_planned_sector(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    created = _make_sector(client, flight_no="KQ7")
    resp = client.delete(f"/api/v1/sectors/{created['id']}")
    assert resp.status_code == 204
    listed = client.get(
        "/api/v1/sectors", params={"date_from": "2025-06-01", "date_to": "2025-06-30"}
    ).json()
    assert not any(r["flight_no"] == "KQ7" for r in listed)


def test_delete_unknown_sector_404(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.delete("/api/v1/sectors/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
