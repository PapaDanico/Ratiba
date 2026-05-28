"""Roster publish endpoint — persistence + audit trail."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from app.models import FlightDutyPeriod, Sector, SectorAssignment
from app.models.user import User


def _create_two_crew(client: TestClient) -> tuple[str, str]:
    cap = client.post(
        "/api/v1/crew",
        json={
            "employee_no": "P-CAP-1",
            "first_name": "Mary",
            "last_name": "Wairimu",
            "role": "CAPT",
            "date_of_hire": "2018-06-01",
            "date_of_birth": "1980-02-12",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()
    fo = client.post(
        "/api/v1/crew",
        json={
            "employee_no": "P-FO-1",
            "first_name": "Peter",
            "last_name": "Onyango",
            "role": "FO",
            "date_of_hire": "2022-01-15",
            "date_of_birth": "1993-11-04",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()
    return cap["employee_no"], fo["employee_no"]


def test_publish_creates_sectors_assignments_and_fdps(
    auth_client: tuple[TestClient, User],
    db_session,
) -> None:
    client, _ = auth_client
    cap_emp, fo_emp = _create_two_crew(client)

    day = date(2026, 7, 1)
    std = datetime(2026, 7, 1, 6, 0, tzinfo=UTC)
    sta = std + timedelta(hours=3)

    payload = {
        "horizon_from": day.isoformat(),
        "horizon_to": day.isoformat(),
        "sectors": [
            {
                "sector_id": "RB101",
                "date_local": day.isoformat(),
                "std": std.isoformat(),
                "sta": sta.isoformat(),
                "aircraft_reg": "5Y-AAA",
                "aircraft_type": "DH8D",
                "block_hours": "3.0",
            }
        ],
        "assignments": [
            {
                "duty_day_key": f"5Y-AAA|{day.isoformat()}",
                "date_local": day.isoformat(),
                "aircraft_reg": "5Y-AAA",
                "aircraft_type": "DH8D",
                "sector_ids": ["RB101"],
                "captain_id": cap_emp,
                "fo_id": fo_emp,
            }
        ],
    }
    resp = client.post("/api/v1/roster/publish", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sector_assignments_created"] == 2  # CAPT + FO
    assert body["flight_duty_periods_created"] == 2

    db_session.expire_all()
    assert db_session.query(Sector).count() == 1
    assert db_session.query(SectorAssignment).count() == 2
    assert db_session.query(FlightDutyPeriod).count() == 2


def test_get_roster_lists_published_assignments(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    cap_emp, fo_emp = _create_two_crew(client)

    day = date(2026, 7, 1)
    std = datetime(2026, 7, 1, 6, 0, tzinfo=UTC)
    payload = {
        "horizon_from": day.isoformat(),
        "horizon_to": day.isoformat(),
        "sectors": [
            {
                "sector_id": "RB101",
                "date_local": day.isoformat(),
                "std": std.isoformat(),
                "sta": (std + timedelta(hours=3)).isoformat(),
                "aircraft_reg": "5Y-AAA",
                "aircraft_type": "DH8D",
                "block_hours": "3.0",
            }
        ],
        "assignments": [
            {
                "duty_day_key": f"5Y-AAA|{day.isoformat()}",
                "date_local": day.isoformat(),
                "aircraft_reg": "5Y-AAA",
                "aircraft_type": "DH8D",
                "sector_ids": ["RB101"],
                "captain_id": cap_emp,
                "fo_id": fo_emp,
            }
        ],
    }
    client.post("/api/v1/roster/publish", json=payload).raise_for_status()

    resp = client.get(
        "/api/v1/roster",
        params={"date_from": day.isoformat(), "date_to": day.isoformat()},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) == 1
    assert items[0]["captain_id"] == cap_emp
    assert items[0]["fo_id"] == fo_emp


def test_publish_rejects_unknown_crew(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    day = date(2026, 7, 1)
    std = datetime(2026, 7, 1, 6, 0, tzinfo=UTC)
    payload = {
        "horizon_from": day.isoformat(),
        "horizon_to": day.isoformat(),
        "sectors": [
            {
                "sector_id": "RB101",
                "date_local": day.isoformat(),
                "std": std.isoformat(),
                "sta": (std + timedelta(hours=3)).isoformat(),
                "aircraft_reg": "5Y-AAA",
                "aircraft_type": "DH8D",
                "block_hours": "3.0",
            }
        ],
        "assignments": [
            {
                "duty_day_key": f"5Y-AAA|{day.isoformat()}",
                "date_local": day.isoformat(),
                "aircraft_reg": "5Y-AAA",
                "aircraft_type": "DH8D",
                "sector_ids": ["RB101"],
                "captain_id": "GHOST",
                "fo_id": "GHOST",
            }
        ],
    }
    resp = client.post("/api/v1/roster/publish", json=payload)
    assert resp.status_code == 422
