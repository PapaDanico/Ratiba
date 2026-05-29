"""Cross-operator FTL aggregation (Phase B).

When a crew member flies for more than one operator — linked by a stable
``person_ref`` (e.g. licence number) — their cumulative FTL exposure must
reflect *all* flying, not one operator's slice. This module sums a person's
duty and block hours across every operator that shares the ref, over the
rolling FTL windows, and flags them against the requesting operator's limits.

Privacy: this is the one deliberate cross-tenant read in the app. It returns
**only aggregate totals + a legality flag** — never another operator's duty
detail, dates, routes, or identity. The caller may only request it for a crew
member in their own operator.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Crew, FlightDutyPeriod
from app.models.ftl import FdpType
from app.services import ftl_limits


class CrossOperatorError(Exception):
    """Raised when the crew member can't be found in the caller's operator."""


@dataclass(frozen=True)
class WindowRow:
    label: str
    metric: str  # "duty" | "block"
    days: int
    total_h: float
    limit_h: float
    state: str  # LEGAL | AT_LIMIT | OVER


@dataclass(frozen=True)
class CrossOperatorFtl:
    crew_employee_no: str
    person_ref: str | None
    linked: bool  # shares a person_ref with crew in >= 1 other operator
    operator_count: int
    as_of: date
    windows: list[WindowRow]


# (label, metric, window-days, limit-key)
_WINDOWS: tuple[tuple[str, str, int, str], ...] = (
    ("Duty — 7 days", "duty", 7, "cumul_duty_7d_h"),
    ("Duty — 28 days", "duty", 28, "cumul_duty_28d_h"),
    ("Duty — 12 months", "duty", 365, "cumul_duty_365d_h"),
    ("Block — 28 days", "block", 28, "cumul_block_28d_h"),
    ("Block — 12 months", "block", 365, "cumul_block_365d_h"),
)


def _state(total: float, limit: float) -> str:
    if total > limit:
        return "OVER"
    if total >= 0.9 * limit:
        return "AT_LIMIT"
    return "LEGAL"


def cross_operator_ftl_summary(
    session: Session,
    *,
    operator_id: uuid.UUID,
    crew_id: uuid.UUID,
    as_of: date,
) -> CrossOperatorFtl:
    crew = session.scalar(
        select(Crew).where(Crew.id == crew_id).where(Crew.operator_id == operator_id)
    )
    if crew is None:
        raise CrossOperatorError("crew not found")

    # All crew rows that are the same person (this operator's row always
    # included). Without a person_ref the person is only this operator's row.
    if crew.person_ref:
        person_crew = session.scalars(select(Crew).where(Crew.person_ref == crew.person_ref)).all()
    else:
        person_crew = [crew]
    crew_ids = [c.id for c in person_crew]
    operator_count = len({c.operator_id for c in person_crew})

    # Sum across the widest window once, then slice in memory.
    horizon = as_of - timedelta(days=364)
    rows = session.execute(
        select(FlightDutyPeriod.date, FlightDutyPeriod.duty_hours, FlightDutyPeriod.flight_hours)
        .where(FlightDutyPeriod.crew_id.in_(crew_ids))
        .where(FlightDutyPeriod.type == FdpType.FDP)
        .where(FlightDutyPeriod.date >= horizon)
        .where(FlightDutyPeriod.date <= as_of)
    ).all()

    limits = ftl_limits.resolve_limits(operator_id, session)

    windows: list[WindowRow] = []
    for label, metric, days, limit_key in _WINDOWS:
        start = as_of - timedelta(days=days - 1)
        total = sum(
            float((r.duty_hours if metric == "duty" else r.flight_hours) or 0)
            for r in rows
            if start <= r.date <= as_of
        )
        limit = float(limits[limit_key])
        windows.append(
            WindowRow(
                label=label,
                metric=metric,
                days=days,
                total_h=round(total, 1),
                limit_h=limit,
                state=_state(total, limit),
            )
        )

    return CrossOperatorFtl(
        crew_employee_no=crew.employee_no,
        person_ref=crew.person_ref,
        linked=operator_count > 1,
        operator_count=operator_count,
        as_of=as_of,
        windows=windows,
    )
