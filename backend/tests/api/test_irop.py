"""IROP assessment endpoint."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Crew, User


def _two_crew(client: TestClient) -> tuple[str, str]:
    def mk(emp: str, role: str) -> str:
        return client.post(
            "/api/v1/crew",
            json={
                "employee_no": emp,
                "first_name": "I",
                "last_name": emp,
                "role": role,
                "date_of_hire": "2019-01-01",
                "date_of_birth": "1985-01-01",
                "base_station": "HKJK",
                "contract_type": "FULL_TIME",
            },
        ).json()["employee_no"]

    return mk("IR-CAP", "CAPT"), mk("IR-FO", "FO")


def _publish(client: TestClient, cap: str, fo: str, days: list[date]) -> None:
    sectors, assignments = [], []
    for i, d in enumerate(days):
        sid = f"IR{i}"
        sectors.append(
            {
                "sector_id": sid,
                "date_local": d.isoformat(),
                "std": datetime(d.year, d.month, d.day, 6, 0, tzinfo=UTC).isoformat(),
                "sta": datetime(d.year, d.month, d.day, 9, 0, tzinfo=UTC).isoformat(),
                "aircraft_reg": "5Y-IRP",
                "aircraft_type": "DH8D",
                "block_hours": "3.0",
            }
        )
        assignments.append(
            {
                "duty_day_key": f"5Y-IRP|{d.isoformat()}",
                "date_local": d.isoformat(),
                "aircraft_reg": "5Y-IRP",
                "aircraft_type": "DH8D",
                "sector_ids": [sid],
                "captain_id": cap,
                "fo_id": fo,
            }
        )
    resp = client.post(
        "/api/v1/roster/publish",
        json={
            "horizon_from": days[0].isoformat(),
            "horizon_to": days[-1].isoformat(),
            "sectors": sectors,
            "assignments": assignments,
        },
    )
    resp.raise_for_status()


def _crew_id(db: Session, emp: str) -> uuid.UUID:
    return db.query(Crew).filter(Crew.employee_no == emp).one().id


def test_diversion_pushes_fdp_illegal(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, _ = auth_client
    cap, fo = _two_crew(client)
    d = date(2026, 9, 10)
    _publish(client, cap, fo, [d])

    resp = client.post(
        "/api/v1/irop/assess",
        json={
            "crew_id": str(_crew_id(db_session, cap)),
            "date": d.isoformat(),
            "extra_flight_h": 10,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["original_legality"] == "LEGAL"
    assert body["disrupted_legality"] != "LEGAL"
    assert any("FDP-MAX" in r for r in body["rules_breached"])
    assert body["disrupted_flight_h"] == 13.0


def test_delay_cascades_into_next_rest(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, _ = auth_client
    cap, fo = _two_crew(client)
    d1 = date(2026, 9, 10)
    d2 = date(2026, 9, 11)
    _publish(client, cap, fo, [d1, d2])

    # 12h ground delay on day 1 → off-duty 21:30; day 2 reports 05:00 → 7.5h rest.
    resp = client.post(
        "/api/v1/irop/assess",
        json={
            "crew_id": str(_crew_id(db_session, cap)),
            "date": d1.isoformat(),
            "extra_ground_h": 12,
        },
    )
    assert resp.status_code == 200, resp.text
    cascade = resp.json()["cascade"]
    assert cascade["next_date"] == d2.isoformat()
    assert cascade["breached"] is True
    assert cascade["new_rest_h"] < cascade["rest_floor_h"]


def test_assess_unknown_duty_404(auth_client: tuple[TestClient, User], db_session: Session) -> None:
    client, _ = auth_client
    cap, _fo = _two_crew(client)
    resp = client.post(
        "/api/v1/irop/assess",
        json={"crew_id": str(_crew_id(db_session, cap)), "date": "2026-01-01", "extra_flight_h": 2},
    )
    assert resp.status_code == 404


def test_alternatives_ranks_available_crew_first(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    from app.models import CrewCurrency, CrewTypeRating
    from app.models.crew import ContractType, CrewRole
    from app.models.training import CurrencyType

    client, user = auth_client
    on_date = date(2026, 9, 20)

    def mk(emp: str) -> Crew:
        c = Crew(
            operator_id=user.operator_id,
            employee_no=emp,
            first_name="Alt",
            last_name=emp,
            role=CrewRole.CAPT,
            date_of_hire=date(2019, 1, 1),
            date_of_birth=date(1985, 1, 1),
            base_station="HKJK",
            contract_type=ContractType.FULL_TIME,
            active=True,
            languages=[],
            faith_observance_flags={},
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        return c

    ready = mk("ALT-READY")
    db_session.add(
        CrewTypeRating(
            operator_id=user.operator_id,
            crew_id=ready.id,
            aircraft_type="DH8D",
            valid_from=date(2024, 1, 1),
            valid_until=date(2027, 1, 1),
        )
    )
    db_session.add(
        CrewCurrency(
            operator_id=user.operator_id,
            crew_id=ready.id,
            currency_type=CurrencyType.LANDINGS_90D,
            last_completed_date=date(2026, 8, 1),
            expires_date=date(2026, 11, 1),
        )
    )
    mk("ALT-UNRATED")  # no type rating, no currency → not available
    db_session.commit()

    resp = client.post(
        "/api/v1/irop/alternatives",
        json={"date": on_date.isoformat(), "role": "CAPT", "aircraft_type": "DH8D"},
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    by_emp = {r["employee_no"]: r for r in rows}
    assert by_emp["ALT-READY"]["available"] is True
    assert by_emp["ALT-UNRATED"]["available"] is False
    # available crew sorted first
    assert rows[0]["available"] is True
