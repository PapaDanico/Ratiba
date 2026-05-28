"""Non-flight duty assignment — standby and days off.

Lets a crewing officer place a crew member on STANDBY (short- or long-call)
or an OFF day for a date. Each writes a :class:`FlightDutyPeriod` of the
appropriate ``type`` so the duty flows automatically into the crew roster
PDF, the iCal feed and the payroll export. Standby legality is evaluated
against the operator's *resolved* FTL limits (their approved scheme merged
over the baseline), reading the relevant standby rule's verdict.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Crew, FlightDutyPeriod, User
from app.models.ftl import FdpType, LegalityState
from app.services import audit_log, ftl_engine, ftl_limits

DUTY_STANDBY_SHORT = "STANDBY_SHORT"
DUTY_STANDBY_LONG = "STANDBY_LONG"
DUTY_OFF = "OFF"
DUTY_TYPES = (DUTY_STANDBY_SHORT, DUTY_STANDBY_LONG, DUTY_OFF)

_STANDBY_RULE = {
    DUTY_STANDBY_SHORT: ("SHORT_CALL", "KCAR-P8-STANDBY-SHORT-CALL"),
    DUTY_STANDBY_LONG: ("LONG_CALL", "KCAR-P8-STANDBY-LONG-CALL"),
}


class DutyError(Exception):
    """Raised when a non-flight duty can't be assigned (bad input, missing crew)."""


def _crew(session: Session, operator_id: uuid.UUID, crew_id: uuid.UUID) -> Crew | None:
    return session.scalar(
        select(Crew).where(Crew.id == crew_id).where(Crew.operator_id == operator_id)
    )


def assign_duty(
    session: Session,
    *,
    user: User,
    crew_id: uuid.UUID,
    day: date,
    duty_type: str,
    start_time: time | None,
    end_time: time | None,
) -> FlightDutyPeriod:
    """Create (replacing any existing non-flight duty for the crew/day)."""
    if duty_type not in DUTY_TYPES:
        raise DutyError(f"unknown duty_type {duty_type!r}")
    crew = _crew(session, user.operator_id, crew_id)
    if crew is None:
        raise DutyError("crew not found")

    # Replace any existing non-flight duty for this crew on this date.
    existing = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.crew_id == crew_id)
        .where(FlightDutyPeriod.date == day)
        .where(FlightDutyPeriod.type != FdpType.FDP)
    ).all()
    for e in existing:
        session.delete(e)

    if duty_type == DUTY_OFF:
        start = datetime.combine(day, time(0, 0), tzinfo=UTC)
        fdp = FlightDutyPeriod(
            operator_id=user.operator_id,
            created_by_user_id=user.id,
            crew_id=crew_id,
            date=day,
            report_time=start,
            off_duty_time=start,
            sectors_count=0,
            flight_hours=Decimal("0"),
            duty_hours=Decimal("0"),
            type=FdpType.OFF,
            legality_state=LegalityState.LEGAL,
            ftl_rules_applied=[],
        )
    else:
        if start_time is None or end_time is None:
            raise DutyError("standby requires start_time and end_time")
        start = datetime.combine(day, start_time, tzinfo=UTC)
        end = datetime.combine(day, end_time, tzinfo=UTC)
        if end <= start:  # overnight standby window
            end += timedelta(days=1)
        hours = Decimal(str(round((end - start).total_seconds() / 3600.0, 2)))
        standby_type, rule_id = _STANDBY_RULE[duty_type]
        # duty_hours = 0 for the legality check: this is a standby assignment,
        # not a called-out flown duty. The window is carried in
        # standby_hours_before_call (and stored as the FDP's duty_hours below).
        fdp_in = ftl_engine.FdpInput(
            report_time=start,
            off_duty_time=end,
            sectors_count=0,
            flight_hours=Decimal("0"),
            duty_hours=Decimal("0"),
            standby_type=standby_type,
            standby_hours_before_call=hours,
        )
        verdicts = ftl_limits.check_fdp_for_operator(fdp_in, user.operator_id, session)
        verdict = next(v for v in verdicts if v.rule_id == rule_id)
        fdp = FlightDutyPeriod(
            operator_id=user.operator_id,
            created_by_user_id=user.id,
            crew_id=crew_id,
            date=day,
            report_time=start,
            off_duty_time=end,
            sectors_count=0,
            flight_hours=Decimal("0"),
            duty_hours=hours,
            type=FdpType.STANDBY,
            legality_state=verdict.legality_state,
            ftl_rules_applied=[rule_id],
        )

    session.add(fdp)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="ASSIGN_DUTY",
        entity_type="flight_duty_period",
        entity_id=fdp.id,
        before_state=None,
        after_state={
            "crew_id": str(crew_id),
            "date": day.isoformat(),
            "duty_type": duty_type,
            "type": fdp.type.value,
            "legality_state": fdp.legality_state.value,
        },
    )
    session.commit()
    session.refresh(fdp)
    return fdp


def list_duties(
    session: Session,
    *,
    operator_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> list[tuple[FlightDutyPeriod, Crew | None]]:
    """All non-flight duties (standby / off / etc.) in range, with crew."""
    rows = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.operator_id == operator_id)
        .where(FlightDutyPeriod.type != FdpType.FDP)
        .where(FlightDutyPeriod.date >= date_from)
        .where(FlightDutyPeriod.date <= date_to)
        .order_by(FlightDutyPeriod.date)
    ).all()
    crew_ids = {r.crew_id for r in rows}
    crew_by_id = {c.id: c for c in session.scalars(select(Crew).where(Crew.id.in_(crew_ids))).all()}
    return [(r, crew_by_id.get(r.crew_id)) for r in rows]


def delete_duty(session: Session, *, user: User, duty_id: uuid.UUID) -> None:
    fdp = session.scalar(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.id == duty_id)
        .where(FlightDutyPeriod.operator_id == user.operator_id)
    )
    if fdp is None:
        raise DutyError("duty not found")
    if fdp.type == FdpType.FDP:
        raise DutyError("flight duties are managed via the roster, not here")
    session.delete(fdp)
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="DELETE_DUTY",
        entity_type="flight_duty_period",
        entity_id=duty_id,
        before_state={"date": fdp.date.isoformat(), "type": fdp.type.value},
        after_state=None,
    )
    session.commit()
