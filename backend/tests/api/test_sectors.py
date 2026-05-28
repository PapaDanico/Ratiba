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


def test_recurring_creates_one_per_weekday(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    # 2025-06-02 is a Monday; range Mon 6/2 .. Sun 6/8, weekdays only → 5.
    resp = client.post(
        "/api/v1/sectors/recurring",
        json={
            "flight_no": "KQ100",
            "origin": "HKJK",
            "destination": "HKMO",
            "std_time": "08:00",
            "sta_time": "10:00",
            "aircraft_reg": "5Y-REC",
            "aircraft_type": "C208",
            "date_from": "2025-06-02",
            "date_to": "2025-06-08",
            "days_of_week": [0, 1, 2, 3, 4],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["created"] == 5
    assert body["skipped_existing"] == 0
    assert {s["date"] for s in body["sectors"]} == {
        "2025-06-02",
        "2025-06-03",
        "2025-06-04",
        "2025-06-05",
        "2025-06-06",
    }
    assert all(s["block_hours"] == 2.0 for s in body["sectors"])


def test_recurring_dedupes_on_rerun(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    payload = {
        "flight_no": "KQ200",
        "origin": "HKJK",
        "destination": "HKMO",
        "std_time": "08:00",
        "sta_time": "10:00",
        "aircraft_reg": "5Y-REC",
        "aircraft_type": "C208",
        "date_from": "2025-07-01",
        "date_to": "2025-07-03",
        "days_of_week": [],  # every day → 3
    }
    first = client.post("/api/v1/sectors/recurring", json=payload).json()
    assert first["created"] == 3
    second = client.post("/api/v1/sectors/recurring", json=payload).json()
    assert second["created"] == 0
    assert second["skipped_existing"] == 3


def test_recurring_overnight_rolls_arrival(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.post(
        "/api/v1/sectors/recurring",
        json={
            "flight_no": "KQ300",
            "origin": "HKJK",
            "destination": "HRYR",
            "std_time": "23:00",
            "sta_time": "01:00",  # next day
            "aircraft_reg": "5Y-NGT",
            "aircraft_type": "AT76",
            "date_from": "2025-08-01",
            "date_to": "2025-08-01",
            "days_of_week": [],
        },
    )
    assert resp.status_code == 201
    s = resp.json()["sectors"][0]
    assert s["block_hours"] == 2.0  # 23:00 -> 01:00 next day


def test_recurring_rejects_reversed_range(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.post(
        "/api/v1/sectors/recurring",
        json={
            "flight_no": "KQ9",
            "origin": "HKJK",
            "destination": "HKMO",
            "std_time": "08:00",
            "sta_time": "10:00",
            "aircraft_reg": "5Y-ABC",
            "aircraft_type": "C208",
            "date_from": "2025-06-08",
            "date_to": "2025-06-02",
            "days_of_week": [],
        },
    )
    assert resp.status_code == 422
