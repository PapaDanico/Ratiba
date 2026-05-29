"""Fatigue report endpoint."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Crew, FlightDutyPeriod, Operator, User
from app.models.crew import ContractType, CrewRole
from app.models.ftl import FdpType, LegalityState


def _mk_crew(db: Session, operator_id, employee_no: str) -> Crew:
    c = Crew(
        operator_id=operator_id,
        employee_no=employee_no,
        first_name="Night",
        last_name=employee_no,
        role=CrewRole.CAPT,
        date_of_hire=date(2020, 1, 1),
        date_of_birth=date(1985, 1, 1),
        base_station="HKJK",
        contract_type=ContractType.FULL_TIME,
        active=True,
        languages=[],
        faith_observance_flags={},
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_fatigue_report_flags_night_crew(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, user = auth_client
    crew = _mk_crew(db_session, user.operator_id, "NGT-1")
    # 3 consecutive night cargo FDPs: report 23:00 UTC (02:00 EAT) → WOCL.
    for i in range(3):
        d = date(2026, 6, 10) + timedelta(days=i)
        report = datetime(2026, 6, 9, 23, 0, tzinfo=UTC) + timedelta(days=i)
        db_session.add(
            FlightDutyPeriod(
                operator_id=user.operator_id,
                crew_id=crew.id,
                date=d,
                report_time=report,
                off_duty_time=report + timedelta(hours=7),
                sectors_count=3,
                flight_hours=5,
                duty_hours=7,
                type=FdpType.FDP,
                legality_state=LegalityState.LEGAL,
                ftl_rules_applied=[],
            )
        )
    db_session.commit()

    resp = client.get(
        "/api/v1/reports/fatigue",
        params={"date_from": "2026-06-01", "date_to": "2026-06-30"},
    )
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["employee_no"] == "NGT-1")
    assert row["fdp_count"] == 3
    assert row["night_fdp_count"] == 3
    assert row["night_pct"] == 100.0
    assert row["max_consecutive_days"] == 3
    assert row["peak_band"] in {"ELEVATED", "HIGH"}


def test_fatigue_report_uses_operator_timezone(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    """The same 23:00 UTC report is WOCL-night in Nairobi (02:00 EAT) but plain
    afternoon (13:00) in Honolulu — so the night flag must follow the operator's
    configured home timezone, not a hardcoded one."""
    client, user = auth_client
    operator = db_session.get(Operator, user.operator_id)
    assert operator is not None
    operator.timezone = "Pacific/Honolulu"
    db_session.commit()

    crew = _mk_crew(db_session, user.operator_id, "TZ-1")
    for i in range(3):
        d = date(2026, 6, 10) + timedelta(days=i)
        report = datetime(2026, 6, 9, 23, 0, tzinfo=UTC) + timedelta(days=i)
        db_session.add(
            FlightDutyPeriod(
                operator_id=user.operator_id,
                crew_id=crew.id,
                date=d,
                report_time=report,
                off_duty_time=report + timedelta(hours=7),
                sectors_count=3,
                flight_hours=5,
                duty_hours=7,
                type=FdpType.FDP,
                legality_state=LegalityState.LEGAL,
                ftl_rules_applied=[],
            )
        )
    db_session.commit()

    resp = client.get(
        "/api/v1/reports/fatigue",
        params={"date_from": "2026-06-01", "date_to": "2026-06-30"},
    )
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["employee_no"] == "TZ-1")
    assert row["fdp_count"] == 3
    assert row["night_fdp_count"] == 0
    assert row["night_pct"] == 0.0


def test_fatigue_report_rejects_reversed_dates(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.get(
        "/api/v1/reports/fatigue",
        params={"date_from": "2026-06-30", "date_to": "2026-06-01"},
    )
    assert resp.status_code == 422
