"""Roster publish endpoint — persistence + audit trail."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.models import Crew, FlightDutyPeriod, Sector, SectorAssignment
from app.models.user import User
from app.services import notify


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


def test_roster_published_task_notifies_assigned_crew(
    auth_client: tuple[TestClient, User], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The enqueued notify task re-reads the published FDPs and messages each
    assigned crew member. Invoked directly so the assertion is independent of
    the queue backend (inline in-process locally vs. deferred rq in CI)."""
    from app.tasks.notifications import notify_roster_published

    client, user = auth_client
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
    assert client.post("/api/v1/roster/publish", json=payload).status_code == 200

    notified: list[str] = []
    monkeypatch.setattr(
        notify,
        "notify_crew_member",
        lambda session, *, crew_id, subject, body: notified.append(str(crew_id)) or 0,
    )
    result = notify_roster_published(
        {
            "operator_id": str(user.operator_id),
            "horizon_from": day.isoformat(),
            "horizon_to": day.isoformat(),
        }
    )
    assert result["crew_notified"] == 2
    assert len(notified) == 2


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


def test_published_roster_applies_rest_minimum_across_days(
    auth_client: tuple[TestClient, User],
    db_session,
) -> None:
    """Day 2's legality reflects the short rest after day 1 — proving prior-duty
    history now feeds roster FDP legality (each day was judged in isolation
    before, so the rest-minimum rule never fired)."""
    client, _ = auth_client
    cap_emp, fo_emp = _create_two_crew(client)
    d1 = date(2026, 8, 1)
    d2 = date(2026, 8, 2)

    def sector(sid: str, d: date, sh: int, eh: int, block: str) -> dict:
        return {
            "sector_id": sid,
            "date_local": d.isoformat(),
            "std": datetime(d.year, d.month, d.day, sh, 0, tzinfo=UTC).isoformat(),
            "sta": datetime(d.year, d.month, d.day, eh, 0, tzinfo=UTC).isoformat(),
            "aircraft_reg": "5Y-RST",
            "aircraft_type": "DH8D",
            "block_hours": block,
        }

    def assignment(d: date, sids: list[str]) -> dict:
        return {
            "duty_day_key": f"5Y-RST|{d.isoformat()}",
            "date_local": d.isoformat(),
            "aircraft_reg": "5Y-RST",
            "aircraft_type": "DH8D",
            "sector_ids": sids,
            "captain_id": cap_emp,
            "fo_id": fo_emp,
        }

    # Day 1 off-duty 18:30; day 2 report 05:00 → 10.5 h rest (< 12 h home floor).
    payload = {
        "horizon_from": d1.isoformat(),
        "horizon_to": d2.isoformat(),
        "sectors": [sector("RST1", d1, 12, 18, "6.0"), sector("RST2", d2, 6, 9, "3.0")],
        "assignments": [assignment(d1, ["RST1"]), assignment(d2, ["RST2"])],
    }
    resp = client.post("/api/v1/roster/publish", json=payload)
    assert resp.status_code == 200, resp.text

    cap = db_session.query(Crew).filter(Crew.employee_no == cap_emp).one()
    fdps = {
        f.date: f
        for f in db_session.query(FlightDutyPeriod).filter(FlightDutyPeriod.crew_id == cap.id).all()
    }
    # Day 1 has no prior duty → rest rule not applicable → legal.
    assert fdps[d1].legality_state.value == "LEGAL"
    # Day 2 sees day 1 as prior → rest-minimum rule fires and the day isn't legal.
    assert "KCAR-P8-REST-MIN" in fdps[d2].ftl_rules_applied
    assert fdps[d2].legality_state.value != "LEGAL"


def test_posting_applies_away_base_rest_floor(
    auth_client: tuple[TestClient, User],
    db_session,
) -> None:
    """Identical short-rest roster to the home-base case, but the crew is on a
    posting → away rest floor (10h) applies, so day 2's 10.5h rest is legal."""
    client, _ = auth_client
    cap_emp, fo_emp = _create_two_crew(client)
    d1 = date(2026, 9, 1)
    d2 = date(2026, 9, 2)

    # Domestic detachment covering both days; assign both crew.
    pid = client.post(
        "/api/v1/postings",
        json={
            "location_icao": "HKMO",
            "country": "Kenya",
            "type": "DETACHMENT",
            "start_date": d1.isoformat(),
            "end_date": (d1 + timedelta(days=10)).isoformat(),
        },
    ).json()["id"]
    crew_ids = {c["employee_no"]: c["id"] for c in client.get("/api/v1/crew").json()}
    for emp in (cap_emp, fo_emp):
        r = client.post(f"/api/v1/postings/{pid}/assign", json={"crew_id": crew_ids[emp]})
        assert r.status_code == 200, r.text

    def sector(sid: str, d: date, sh: int, eh: int, block: str) -> dict:
        return {
            "sector_id": sid,
            "date_local": d.isoformat(),
            "std": datetime(d.year, d.month, d.day, sh, 0, tzinfo=UTC).isoformat(),
            "sta": datetime(d.year, d.month, d.day, eh, 0, tzinfo=UTC).isoformat(),
            "aircraft_reg": "5Y-AWY",
            "aircraft_type": "DH8D",
            "block_hours": block,
        }

    def assignment(d: date, sids: list[str]) -> dict:
        return {
            "duty_day_key": f"5Y-AWY|{d.isoformat()}",
            "date_local": d.isoformat(),
            "aircraft_reg": "5Y-AWY",
            "aircraft_type": "DH8D",
            "sector_ids": sids,
            "captain_id": cap_emp,
            "fo_id": fo_emp,
        }

    payload = {
        "horizon_from": d1.isoformat(),
        "horizon_to": d2.isoformat(),
        # Day 1 off 18:30; day 2 report 06:00 → 11.5h rest: clears the 10h away
        # floor but would breach the 12h home floor.
        "sectors": [sector("AWY1", d1, 12, 18, "6.0"), sector("AWY2", d2, 7, 10, "3.0")],
        "assignments": [assignment(d1, ["AWY1"]), assignment(d2, ["AWY2"])],
    }
    resp = client.post("/api/v1/roster/publish", json=payload)
    assert resp.status_code == 200, resp.text

    cap = db_session.query(Crew).filter(Crew.employee_no == cap_emp).one()
    fdps = {
        f.date: f
        for f in db_session.query(FlightDutyPeriod).filter(FlightDutyPeriod.crew_id == cap.id).all()
    }
    # Rest rule still runs, but 11.5h clears the 10h away floor → legal.
    assert "KCAR-P8-REST-MIN" in fdps[d2].ftl_rules_applied
    assert fdps[d2].legality_state.value == "LEGAL"
