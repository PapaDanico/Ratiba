"""Roster amendments + re-publish idempotency."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from app.models import AuditEvent, FlightDutyPeriod, SectorAssignment
from app.models.user import User


def _setup_two_crew(client: TestClient) -> tuple[str, str, str]:
    cap_a = client.post(
        "/api/v1/crew",
        json={
            "employee_no": "P-CAP-A",
            "first_name": "Mary",
            "last_name": "Wairimu",
            "role": "CAPT",
            "date_of_hire": "2018-06-01",
            "date_of_birth": "1980-02-12",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()
    cap_b = client.post(
        "/api/v1/crew",
        json={
            "employee_no": "P-CAP-B",
            "first_name": "Asha",
            "last_name": "Kamau",
            "role": "CAPT",
            "date_of_hire": "2019-01-01",
            "date_of_birth": "1983-05-21",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()
    fo = client.post(
        "/api/v1/crew",
        json={
            "employee_no": "P-FO-A",
            "first_name": "Peter",
            "last_name": "Onyango",
            "role": "FO",
            "date_of_hire": "2022-01-15",
            "date_of_birth": "1993-11-04",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()
    return cap_a["employee_no"], cap_b["employee_no"], fo["employee_no"]


def _single_day_payload(*, day: date, cap: str, fo: str) -> dict:
    std = datetime(day.year, day.month, day.day, 6, 0, tzinfo=UTC)
    return {
        "horizon_from": day.isoformat(),
        "horizon_to": day.isoformat(),
        "sectors": [
            {
                "sector_id": f"RB-{day.isoformat()}",
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
                "sector_ids": [f"RB-{day.isoformat()}"],
                "captain_id": cap,
                "fo_id": fo,
            }
        ],
    }


def test_republish_is_idempotent(auth_client: tuple[TestClient, User], db_session) -> None:
    client, _ = auth_client
    cap_a, _cap_b, fo = _setup_two_crew(client)
    day = date(2026, 7, 1)
    payload = _single_day_payload(day=day, cap=cap_a, fo=fo)

    client.post("/api/v1/roster/publish", json=payload).raise_for_status()
    # Republish exactly the same payload — should not double-count.
    client.post("/api/v1/roster/publish", json=payload).raise_for_status()

    db_session.expire_all()
    assert db_session.query(SectorAssignment).count() == 2
    assert db_session.query(FlightDutyPeriod).count() == 2


def test_amend_swaps_captain_and_records_audit(
    auth_client: tuple[TestClient, User], db_session
) -> None:
    client, _ = auth_client
    cap_a, cap_b, fo = _setup_two_crew(client)
    day = date(2026, 7, 1)
    payload = _single_day_payload(day=day, cap=cap_a, fo=fo)
    client.post("/api/v1/roster/publish", json=payload).raise_for_status()

    resp = client.post(
        "/api/v1/roster/amend",
        json={
            "duty_day_key": f"5Y-AAA|{day.isoformat()}",
            "new_captain_employee_no": cap_b,
            "new_fo_employee_no": fo,
            "reason": "Cap A sick — swapping to Cap B",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["legality_state"] in ("LEGAL", "AT_LIMIT")

    db_session.expire_all()
    # Still 2 SectorAssignments + 2 FDPs after the swap — not duplicated.
    assert db_session.query(SectorAssignment).count() == 2
    assert db_session.query(FlightDutyPeriod).count() == 2

    actions = {e.action for e in db_session.query(AuditEvent).all()}
    assert "AMEND_ROSTER" in actions

    # Roster GET reflects the new captain.
    listed = client.get(
        "/api/v1/roster",
        params={"date_from": day.isoformat(), "date_to": day.isoformat()},
    ).json()
    assert listed[0]["captain_id"] == cap_b


def test_amend_unknown_duty_day_returns_422(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    cap_a, _cap_b, fo = _setup_two_crew(client)
    resp = client.post(
        "/api/v1/roster/amend",
        json={
            "duty_day_key": "5Y-NONE|2099-01-01",
            "new_captain_employee_no": cap_a,
            "new_fo_employee_no": fo,
            "reason": "test",
        },
    )
    assert resp.status_code == 422


def test_get_roster_returns_legality_state(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    cap_a, _cap_b, fo = _setup_two_crew(client)
    day = date(2026, 7, 1)
    payload = _single_day_payload(day=day, cap=cap_a, fo=fo)
    client.post("/api/v1/roster/publish", json=payload).raise_for_status()

    listed = client.get(
        "/api/v1/roster",
        params={"date_from": day.isoformat(), "date_to": day.isoformat()},
    ).json()
    assert listed[0]["legality_state"] in ("LEGAL", "AT_LIMIT")


def test_amend_cascades_legality_to_later_days(
    auth_client: tuple[TestClient, User], db_session
) -> None:
    """Amending one day re-evaluates the affected crew's *later* days.

    A captain flies a late duty on day 1, then an early duty on day 2 — too
    little rest between, so day 2 is illegal. Each day has a different FO so the
    only continuously-rostered crew is the captain. Amending day 1 onto another
    captain removes day 1 from the original captain's history, so the cascade
    must recompute day 2 back to LEGAL.
    """
    from app.models import Crew

    client, _ = auth_client
    cap_a, cap_b, fo1 = _setup_two_crew(client)
    fo2 = client.post(
        "/api/v1/crew",
        json={
            "employee_no": "P-FO-B",
            "first_name": "Grace",
            "last_name": "Achieng",
            "role": "FO",
            "date_of_hire": "2021-03-01",
            "date_of_birth": "1994-07-09",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()["employee_no"]

    d1 = date(2026, 8, 1)
    d2 = date(2026, 8, 2)

    def _sector(day: date, std_h: int, dur_h: int) -> dict:
        std = datetime(day.year, day.month, day.day, std_h, 0, tzinfo=UTC)
        return {
            "sector_id": f"RB-{day.isoformat()}",
            "date_local": day.isoformat(),
            "std": std.isoformat(),
            "sta": (std + timedelta(hours=dur_h)).isoformat(),
            "aircraft_reg": "5Y-AAA",
            "aircraft_type": "DH8D",
            "block_hours": str(float(dur_h)),
        }

    def _assignment(day: date, cap: str, fo: str) -> dict:
        return {
            "duty_day_key": f"5Y-AAA|{day.isoformat()}",
            "date_local": day.isoformat(),
            "aircraft_reg": "5Y-AAA",
            "aircraft_type": "DH8D",
            "sector_ids": [f"RB-{day.isoformat()}"],
            "captain_id": cap,
            "fo_id": fo,
        }

    payload = {
        "horizon_from": d1.isoformat(),
        "horizon_to": d2.isoformat(),
        # Day 1 ends 21:30; day 2 reports 05:00 → ~7.5 h rest (< 12 h floor).
        "sectors": [_sector(d1, 12, 9), _sector(d2, 6, 3)],
        "assignments": [_assignment(d1, cap_a, fo1), _assignment(d2, cap_a, fo2)],
    }
    client.post("/api/v1/roster/publish", json=payload).raise_for_status()

    def _legality(emp_no: str, day: date) -> str:
        db_session.expire_all()
        row = (
            db_session.query(FlightDutyPeriod)
            .join(Crew, Crew.id == FlightDutyPeriod.crew_id)
            .filter(Crew.employee_no == emp_no, FlightDutyPeriod.date == day)
            .one()
        )
        return row.legality_state.value

    # Day 2 starts out illegal for the captain (insufficient rest after day 1).
    assert _legality(cap_a, d2) in ("REQUIRES_FRMS_DEROGATION", "ILLEGAL")

    # Amend day 1 onto a different captain — day 1 leaves cap_a's history.
    client.post(
        "/api/v1/roster/amend",
        json={
            "duty_day_key": f"5Y-AAA|{d1.isoformat()}",
            "new_captain_employee_no": cap_b,
            "new_fo_employee_no": fo1,
            "reason": "cascade test",
        },
    ).raise_for_status()

    # The cascade recomputed cap_a's day 2: with no prior duty it is now LEGAL.
    assert _legality(cap_a, d2) == "LEGAL"
