"""Automatic roster builder — DB-sourced optimiser run + publish."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CrewTypeRating, User


def _create_crew(client: TestClient, *, employee_no: str, role: str, first: str) -> dict:
    return client.post(
        "/api/v1/crew",
        json={
            "employee_no": employee_no,
            "first_name": first,
            "last_name": "Test",
            "role": role,
            "date_of_hire": "2020-01-01",
            "date_of_birth": "1985-01-01",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()


def _rate(session: Session, *, operator_id, crew_id, user_id, ac_type: str) -> None:
    session.add(
        CrewTypeRating(
            operator_id=operator_id,
            created_by_user_id=user_id,
            crew_id=crew_id,
            aircraft_type=ac_type,
            valid_from=date(2020, 1, 1),
            valid_until=date(2030, 1, 1),
        )
    )
    session.commit()


def _add_sector(client: TestClient, *, flight_no: str, day: str) -> dict:
    return client.post(
        "/api/v1/sectors",
        json={
            "flight_no": flight_no,
            "date": day,
            "origin": "HKJK",
            "destination": "HKMO",
            "std": f"{day}T08:00:00Z",
            "sta": f"{day}T10:00:00Z",
            "aircraft_reg": "5Y-ABC",
            "aircraft_type": "C208",
        },
    ).json()


def test_auto_generate_assigns_and_publishes(
    auth_client: tuple[TestClient, User],
    db_session: Session,
) -> None:
    client, user = auth_client
    capt = _create_crew(client, employee_no="C1", role="CAPT", first="Ada")
    fo = _create_crew(client, employee_no="F1", role="FO", first="Ben")
    _rate(
        db_session,
        operator_id=user.operator_id,
        crew_id=uuid.UUID(capt["id"]),
        user_id=user.id,
        ac_type="C208",
    )
    _rate(
        db_session,
        operator_id=user.operator_id,
        crew_id=uuid.UUID(fo["id"]),
        user_id=user.id,
        ac_type="C208",
    )
    _add_sector(client, flight_no="KQ1", day="2025-06-02")

    resp = client.post(
        "/api/v1/roster/auto-generate",
        json={"horizon_from": "2025-06-01", "horizon_to": "2025-06-07"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["result"]["status"] in {"OPTIMAL", "FEASIBLE"}
    assert len(body["result"]["assignments"]) == 1
    a = body["result"]["assignments"][0]
    assert {a["captain_id"], a["fo_id"]} == {"C1", "F1"}

    # Publish the draft straight back.
    pub = client.post(
        "/api/v1/roster/publish",
        json={
            "horizon_from": "2025-06-01",
            "horizon_to": "2025-06-07",
            "sectors": body["sectors"],
            "assignments": body["result"]["assignments"],
        },
    )
    assert pub.status_code == 200, pub.text
    assert pub.json()["sector_assignments_created"] >= 1

    roster = client.get(
        "/api/v1/roster", params={"date_from": "2025-06-01", "date_to": "2025-06-07"}
    ).json()
    assert any(r["captain_id"] == "C1" for r in roster)


def test_auto_generate_no_sectors_is_infeasible(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    _create_crew(client, employee_no="C9", role="CAPT", first="Cy")
    resp = client.post(
        "/api/v1/roster/auto-generate",
        json={"horizon_from": "2025-07-01", "horizon_to": "2025-07-07"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["result"]["status"] == "INFEASIBLE"


def test_auto_generate_rejects_reversed_horizon(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    resp = client.post(
        "/api/v1/roster/auto-generate",
        json={"horizon_from": "2025-07-07", "horizon_to": "2025-07-01"},
    )
    assert resp.status_code == 422
