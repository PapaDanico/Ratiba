"""Cross-operator FTL aggregation (Phase B)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Crew, FlightDutyPeriod, Operator, User
from app.models.crew import ContractType, CrewRole
from app.models.ftl import FdpType, LegalityState
from app.models.operator import OperatorTier


def _crew(db: Session, operator_id, emp: str, person_ref: str | None) -> Crew:
    c = Crew(
        operator_id=operator_id,
        employee_no=emp,
        first_name="X",
        last_name=emp,
        role=CrewRole.CAPT,
        date_of_hire=date(2020, 1, 1),
        date_of_birth=date(1985, 1, 1),
        base_station="HKJK",
        contract_type=ContractType.FULL_TIME,
        active=True,
        languages=[],
        faith_observance_flags={},
        person_ref=person_ref,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _fdp(db: Session, operator_id, crew_id, d: date, duty_h: float, flight_h: float) -> None:
    db.add(
        FlightDutyPeriod(
            operator_id=operator_id,
            crew_id=crew_id,
            date=d,
            report_time=datetime(d.year, d.month, d.day, 6, 0, tzinfo=UTC),
            off_duty_time=datetime(d.year, d.month, d.day, 12, 0, tzinfo=UTC),
            sectors_count=2,
            flight_hours=flight_h,
            duty_hours=duty_h,
            type=FdpType.FDP,
            legality_state=LegalityState.LEGAL,
            ftl_rules_applied=[],
        )
    )
    db.commit()


def test_cross_operator_totals_sum_across_operators(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, user = auth_client
    as_of = date(2026, 6, 10)

    # This operator's crew, linked by licence number.
    home = _crew(db_session, user.operator_id, "XOP-HOME", "LIC-777")
    _fdp(db_session, user.operator_id, home.id, as_of, duty_h=8.0, flight_h=5.0)

    # A second operator with the SAME person flying more hours that week.
    other_op = Operator(
        aoc_number="XOP-OTHER",
        name="Other Air",
        base="HKJK",
        contact_email="ops@other.example",
        tier=OperatorTier.ENTRY,
    )
    db_session.add(other_op)
    db_session.commit()
    db_session.refresh(other_op)
    away = _crew(db_session, other_op.id, "XOP-AWAY", "LIC-777")
    _fdp(db_session, other_op.id, away.id, as_of - timedelta(days=1), duty_h=10.0, flight_h=7.0)

    resp = client.get(
        f"/api/v1/crew/{home.id}/cross-operator-ftl", params={"as_of": as_of.isoformat()}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["linked"] is True
    assert body["operator_count"] == 2

    wins = {w["label"]: w for w in body["windows"]}
    # 7-day duty = 8 (home) + 10 (other) = 18; block = 5 + 7 = 12.
    assert wins["Duty — 7 days"]["total_h"] == 18.0
    assert wins["Block — 28 days"]["total_h"] == 12.0
    assert wins["Duty — 7 days"]["limit_h"] == 60.0
    assert wins["Duty — 7 days"]["state"] == "LEGAL"

    # Privacy: only aggregates surface — never the other operator's identity/detail.
    assert "Other Air" not in resp.text
    assert "XOP-OTHER" not in resp.text
    assert "XOP-AWAY" not in resp.text


def test_unlinked_crew_reports_single_operator(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, user = auth_client
    solo = _crew(db_session, user.operator_id, "XOP-SOLO", None)
    _fdp(db_session, user.operator_id, solo.id, date(2026, 6, 10), duty_h=6.0, flight_h=4.0)

    resp = client.get(f"/api/v1/crew/{solo.id}/cross-operator-ftl", params={"as_of": "2026-06-10"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["linked"] is False
    assert body["operator_count"] == 1
    assert {w["label"]: w["total_h"] for w in body["windows"]}["Duty — 7 days"] == 6.0


def test_cross_operator_unknown_crew_404(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.get("/api/v1/crew/00000000-0000-0000-0000-000000000000/cross-operator-ftl")
    assert resp.status_code == 404
