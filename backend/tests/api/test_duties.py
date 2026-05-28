"""Non-flight duty rostering — standby and days off."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User


def _crew(client: TestClient, *, emp: str = "S1") -> str:
    return client.post(
        "/api/v1/crew",
        json={
            "employee_no": emp,
            "first_name": "Sefu",
            "last_name": "Mwangi",
            "role": "CAPT",
            "date_of_hire": "2020-01-01",
            "date_of_birth": "1985-01-01",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()["id"]


def test_assign_short_call_standby(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew_id = _crew(client)
    resp = client.post(
        "/api/v1/duties",
        json={
            "crew_id": crew_id,
            "date": "2025-06-02",
            "duty_type": "STANDBY_SHORT",
            "start_time": "06:00",
            "end_time": "14:00",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["type"] == "STANDBY"
    assert body["duration_h"] == 8.0
    assert body["legality_state"] == "LEGAL"  # 8 h ≤ 12 h short-call cap

    listed = client.get(
        "/api/v1/duties", params={"date_from": "2025-06-01", "date_to": "2025-06-30"}
    ).json()
    assert any(d["id"] == body["id"] and d["crew_name"] == "Sefu Mwangi" for d in listed)


def test_long_call_standby_over_short_cap_is_legal(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew_id = _crew(client, emp="S2")
    # 20 h would bust the 12 h short-call cap, but is within the 24 h long-call cap.
    resp = client.post(
        "/api/v1/duties",
        json={
            "crew_id": crew_id,
            "date": "2025-06-03",
            "duty_type": "STANDBY_LONG",
            "start_time": "08:00",
            "end_time": "04:00",  # next day → 20 h
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["duration_h"] == 20.0
    assert body["legality_state"] == "LEGAL"


def test_assign_off_day(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew_id = _crew(client, emp="S3")
    resp = client.post(
        "/api/v1/duties",
        json={"crew_id": crew_id, "date": "2025-06-04", "duty_type": "OFF"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["type"] == "OFF"
    assert resp.json()["legality_state"] == "LEGAL"


def test_reassign_replaces_existing_duty(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew_id = _crew(client, emp="S4")
    base = {"crew_id": crew_id, "date": "2025-06-05"}
    client.post("/api/v1/duties", json={**base, "duty_type": "OFF"}).raise_for_status()
    client.post(
        "/api/v1/duties",
        json={**base, "duty_type": "STANDBY_SHORT", "start_time": "06:00", "end_time": "12:00"},
    ).raise_for_status()
    listed = client.get(
        "/api/v1/duties", params={"date_from": "2025-06-05", "date_to": "2025-06-05"}
    ).json()
    # The OFF was replaced by the standby — one duty for that crew/day.
    same_day = [d for d in listed if d["crew_id"] == crew_id]
    assert len(same_day) == 1
    assert same_day[0]["type"] == "STANDBY"


def test_delete_duty(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew_id = _crew(client, emp="S5")
    duty = client.post(
        "/api/v1/duties",
        json={"crew_id": crew_id, "date": "2025-06-06", "duty_type": "OFF"},
    ).json()
    assert client.delete(f"/api/v1/duties/{duty['id']}").status_code == 204
    listed = client.get(
        "/api/v1/duties", params={"date_from": "2025-06-06", "date_to": "2025-06-06"}
    ).json()
    assert listed == []


def test_standby_requires_times(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew_id = _crew(client, emp="S6")
    resp = client.post(
        "/api/v1/duties",
        json={"crew_id": crew_id, "date": "2025-06-07", "duty_type": "STANDBY_SHORT"},
    )
    assert resp.status_code == 422
