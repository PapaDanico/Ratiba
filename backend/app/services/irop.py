"""Irregular-operations (IROP) assessment.

When a published duty is disrupted (e.g. a diversion adds block + ground time,
or a delay extends the duty), recompute the operating crew member's FDP
legality — threading their real duty history and posting away-base status — and
flag whether the disruption now breaches FTL and cascades into the next duty's
rest. Read-only: it answers "is this diversion still legal, and what breaks
next?" (brief Scenario D). It does not mutate the roster.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Crew,
    CrewCurrency,
    CrewTypeRating,
    FlightDutyPeriod,
    Posting,
    PostingAssignment,
)
from app.models.crew import CrewRole
from app.models.ftl import FdpType, LegalityState
from app.models.training import CurrencyType
from app.services import ftl_engine, ftl_limits
from app.services import postings as postings_service


class IropError(Exception):
    """Raised for IROP assessment failures (mapped to HTTP 404/422)."""


@dataclass(frozen=True)
class AltCrew:
    crew_id: uuid.UUID
    employee_no: str
    name: str
    role: str
    type_rated: bool
    landings_current: bool
    free: bool  # not already on a duty / posting that day
    available: bool  # type_rated and current and free


def suggest_alternatives(
    session: Session,
    *,
    operator_id: uuid.UUID,
    on_date: date,
    role: CrewRole,
    aircraft_type: str,
    exclude_crew_id: uuid.UUID | None = None,
) -> list[AltCrew]:
    """Relief crew for a duty on ``on_date``: same role, type-rated for the
    aircraft, 90-day landing-current, and free (not already on a duty or
    posting that day). Available candidates are returned first."""
    crew = session.scalars(
        select(Crew)
        .where(Crew.operator_id == operator_id)
        .where(Crew.active.is_(True))
        .where(Crew.role == role)
    ).all()
    rated_ids = set(
        session.scalars(
            select(CrewTypeRating.crew_id)
            .where(CrewTypeRating.operator_id == operator_id)
            .where(CrewTypeRating.aircraft_type == aircraft_type)
            .where(CrewTypeRating.valid_from <= on_date)
            .where(CrewTypeRating.valid_until >= on_date)
        ).all()
    )
    busy_ids = set(
        session.scalars(
            select(FlightDutyPeriod.crew_id)
            .where(FlightDutyPeriod.operator_id == operator_id)
            .where(FlightDutyPeriod.date == on_date)
        ).all()
    )
    posting_ids = set(
        session.scalars(
            select(PostingAssignment.crew_id)
            .join(Posting, Posting.id == PostingAssignment.posting_id)
            .where(Posting.operator_id == operator_id)
            .where(Posting.start_date <= on_date)
            .where(Posting.end_date >= on_date)
        ).all()
    )
    # A crew member may hold several LANDINGS_90D rows (renewals); the latest
    # expiry is the one that governs currency, so take the max per crew.
    landings: dict[uuid.UUID, date] = {
        row.crew_id: row.max_expires
        for row in session.execute(
            select(
                CrewCurrency.crew_id,
                func.max(CrewCurrency.expires_date).label("max_expires"),
            )
            .where(CrewCurrency.operator_id == operator_id)
            .where(CrewCurrency.currency_type == CurrencyType.LANDINGS_90D)
            .group_by(CrewCurrency.crew_id)
        ).all()
    }

    out: list[AltCrew] = []
    for c in crew:
        if exclude_crew_id is not None and c.id == exclude_crew_id:
            continue
        type_rated = c.id in rated_ids
        free = c.id not in busy_ids and c.id not in posting_ids
        exp = landings.get(c.id)
        current = exp is not None and exp >= on_date
        out.append(
            AltCrew(
                crew_id=c.id,
                employee_no=c.employee_no,
                name=f"{c.first_name} {c.last_name}",
                role=c.role.value,
                type_rated=type_rated,
                landings_current=current,
                free=free,
                available=type_rated and current and free,
            )
        )
    out.sort(key=lambda a: (not a.available, a.employee_no))
    return out


@dataclass(frozen=True)
class CascadeImpact:
    next_date: date | None
    new_rest_h: float | None
    rest_floor_h: float | None
    breached: bool


@dataclass(frozen=True)
class IropAssessment:
    crew_employee_no: str
    date: date
    away_from_base: bool
    original_flight_h: float
    original_duty_h: float
    original_legality: str
    disrupted_flight_h: float
    disrupted_duty_h: float
    disrupted_legality: str
    rules_breached: list[str]
    cascade: CascadeImpact


def _history(
    session: Session, *, operator_id: uuid.UUID, crew_id: uuid.UUID, exclude_date: date
) -> list[ftl_engine.FdpHistoryEntry]:
    rows = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.operator_id == operator_id)
        .where(FlightDutyPeriod.crew_id == crew_id)
        .where(FlightDutyPeriod.date != exclude_date)
    ).all()
    return [
        ftl_engine.FdpHistoryEntry(
            date_local=f.date.isoformat(),
            report_time=f.report_time,
            off_duty_time=f.off_duty_time,
            duty_hours=Decimal(str(f.duty_hours)),
            flight_hours=Decimal(str(f.flight_hours)),
            sectors_count=f.sectors_count,
            fdp_type=f.type,
            at_home_base=True,
        )
        for f in rows
    ]


def assess_diversion(
    session: Session,
    *,
    operator_id: uuid.UUID,
    crew_id: uuid.UUID,
    on_date: date,
    extra_flight_h: Decimal,
    extra_ground_h: Decimal,
    discretion_h: Decimal = Decimal("0"),
) -> IropAssessment:
    crew = session.scalar(
        select(Crew).where(Crew.id == crew_id).where(Crew.operator_id == operator_id)
    )
    if crew is None:
        raise IropError("crew not found")
    fdp = session.scalar(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.operator_id == operator_id)
        .where(FlightDutyPeriod.crew_id == crew_id)
        .where(FlightDutyPeriod.date == on_date)
        .where(FlightDutyPeriod.type == FdpType.FDP)
    )
    if fdp is None:
        raise IropError("no published flight duty for that crew on that date")

    report = fdp.report_time
    orig_off = fdp.off_duty_time
    orig_flight = float(fdp.flight_hours or 0)
    orig_duty = float(fdp.duty_hours or 0)

    added_h = float(extra_flight_h) + float(extra_ground_h)
    new_off = orig_off + timedelta(hours=added_h)
    new_flight = orig_flight + float(extra_flight_h)
    new_duty = (new_off - report).total_seconds() / 3600.0

    posting = postings_service.active_posting_for(
        session, operator_id=operator_id, crew_id=crew_id, on_date=on_date
    )
    at_home = posting is None
    base_tz = posting.base_tz if posting is not None else "Africa/Nairobi"

    history = _history(session, operator_id=operator_id, crew_id=crew_id, exclude_date=on_date)
    earlier = [h for h in history if h.report_time < report]
    prior_fdp = max(earlier, key=lambda h: h.report_time) if earlier else None

    def _verdicts(flight_h: float, duty_h: float, off: object) -> list[ftl_engine.FtlVerdict]:
        fdp_in = ftl_engine.FdpInput(
            report_time=report,
            off_duty_time=off,  # type: ignore[arg-type]
            sectors_count=fdp.sectors_count + (1 if extra_flight_h > 0 else 0),
            flight_hours=Decimal(str(round(flight_h, 2))),
            duty_hours=Decimal(str(round(duty_h, 2))),
            prior_fdp=prior_fdp,
            history=tuple(history),
            at_home_base=at_home,
            base_tz=base_tz,
            discretion_extension_h=discretion_h,
        )
        return ftl_limits.check_fdp_for_operator(fdp_in, operator_id, session)

    original = ftl_engine.aggregate_verdicts(_verdicts(orig_flight, orig_duty, orig_off))
    disrupted_verdicts = _verdicts(new_flight, new_duty, new_off)
    disrupted = ftl_engine.aggregate_verdicts(disrupted_verdicts)
    breached = [
        v.rule_id for v in disrupted_verdicts if v.legality_state is not LegalityState.LEGAL
    ]

    # Cascade onto the next published duty's rest.
    nxt = session.scalar(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.operator_id == operator_id)
        .where(FlightDutyPeriod.crew_id == crew_id)
        .where(FlightDutyPeriod.date > on_date)
        .where(FlightDutyPeriod.type == FdpType.FDP)
        .order_by(FlightDutyPeriod.date)
        .limit(1)
    )
    cascade = CascadeImpact(next_date=None, new_rest_h=None, rest_floor_h=None, breached=False)
    if nxt is not None:
        limits = ftl_limits.resolve_limits(operator_id, session)
        next_posting = postings_service.active_posting_for(
            session, operator_id=operator_id, crew_id=crew_id, on_date=nxt.date
        )
        floor_key = "rest_away_floor_h" if next_posting is not None else "rest_home_floor_h"
        floor = float(limits[floor_key])
        new_rest = (nxt.report_time - new_off).total_seconds() / 3600.0
        cascade = CascadeImpact(
            next_date=nxt.date,
            new_rest_h=round(new_rest, 1),
            rest_floor_h=floor,
            breached=new_rest < floor,
        )

    return IropAssessment(
        crew_employee_no=crew.employee_no,
        date=on_date,
        away_from_base=not at_home,
        original_flight_h=round(orig_flight, 2),
        original_duty_h=round(orig_duty, 2),
        original_legality=original.legality_state.value,
        disrupted_flight_h=round(new_flight, 2),
        disrupted_duty_h=round(new_duty, 2),
        disrupted_legality=disrupted.legality_state.value,
        rules_breached=breached,
        cascade=cascade,
    )
