"""Operator-resolved FTL limits govern published-roster legality.

Proves that an operator's latest ACCEPTED constraint set (their approved
Flight & Duty Time scheme) — not just the generic baseline — drives the
legality stamped on published FlightDutyPeriod rows.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FlightDutyPeriod, User
from app.models.constraint import (
    ConstraintReviewStatus,
    ConstraintRule,
    ConstraintSet,
    ConstraintSetStatus,
)
from app.models.ftl import LegalityState


def _crew(client: TestClient, *, emp: str, role: str, first: str) -> None:
    resp = client.post(
        "/api/v1/crew",
        json={
            "employee_no": emp,
            "first_name": first,
            "last_name": "Test",
            "role": role,
            "date_of_hire": "2020-01-01",
            "date_of_birth": "1985-01-01",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    )
    assert resp.status_code == 201, resp.text


def _publish(client: TestClient) -> None:
    # Single DAY_PEAK sector: report 07:00Z (10:00 Africa/Nairobi) → ~10.5 h duty.
    resp = client.post(
        "/api/v1/roster/publish",
        json={
            "horizon_from": "2025-06-02",
            "horizon_to": "2025-06-02",
            "sectors": [
                {
                    "sector_id": "KQ1",
                    "date_local": "2025-06-02",
                    "std": "2025-06-02T08:00:00Z",
                    "sta": "2025-06-02T17:00:00Z",
                    "aircraft_reg": "5Y-AB",
                    "aircraft_type": "C208",
                    "block_hours": 9.0,
                }
            ],
            "assignments": [
                {
                    "duty_day_key": "5Y-AB|2025-06-02",
                    "date_local": "2025-06-02",
                    "aircraft_reg": "5Y-AB",
                    "aircraft_type": "C208",
                    "sector_ids": ["KQ1"],
                    "captain_id": "C1",
                    "fo_id": "F1",
                }
            ],
        },
    )
    assert resp.status_code == 200, resp.text


def _stored_states(session: Session, operator_id: uuid.UUID) -> set[LegalityState]:
    rows = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.operator_id == operator_id)
        .where(FlightDutyPeriod.date == date(2025, 6, 2))
    ).all()
    return {r.legality_state for r in rows}


def test_baseline_publish_is_legal(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, user = auth_client
    _crew(client, emp="C1", role="CAPT", first="Ada")
    _crew(client, emp="F1", role="FO", first="Ben")
    _publish(client)
    # ~10.5 h duty in DAY_PEAK is well under the 13 h baseline → LEGAL.
    assert _stored_states(db_session, user.operator_id) == {LegalityState.LEGAL}


def test_accepted_scheme_tightens_published_legality(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, user = auth_client
    _crew(client, emp="C1", role="CAPT", first="Ada")
    _crew(client, emp="F1", role="FO", first="Ben")

    # Operator's accepted scheme caps DAY_PEAK FDP at 6 h.
    cset = ConstraintSet(
        operator_id=user.operator_id,
        om_a_revision="OM-A rev 3",
        status=ConstraintSetStatus.ACCEPTED,
        rule_count=1,
        accepted_at=datetime.now(UTC),
    )
    db_session.add(cset)
    db_session.flush()
    db_session.add(
        ConstraintRule(
            constraint_set_id=cset.id,
            rule_key="fdp_max_basic_by_band.DAY_PEAK",
            final_value=6.0,
            review_status=ConstraintReviewStatus.EDITED,
        )
    )
    db_session.commit()

    _publish(client)
    # The 6 h override is clamped up to the 9 h sector floor; 10.5 h duty then
    # falls in the 9–11 h derogation band — so the operator's stricter scheme
    # flips this duty from LEGAL (baseline) to REQUIRES_FRMS_DEROGATION.
    states = _stored_states(db_session, user.operator_id)
    assert states == {LegalityState.REQUIRES_FRMS_DEROGATION}
    assert LegalityState.LEGAL not in states
