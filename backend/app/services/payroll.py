"""Payroll / duty-hours export.

Produces a per-crew summary of duty and block hours over a pay period as
CSV — the single most labour-intensive thing a Crewing Officer does by
hand each month. Local Kenyan/Ugandan/Tanzanian payroll systems mostly
lack APIs, so a clean CSV is the practical integration.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Crew, FlightDutyPeriod
from app.models.ftl import FdpType
from app.models.leave import LeaveRequest, LeaveStatus

_HEADERS = [
    "employee_no",
    "name",
    "role",
    "base",
    "fdp_count",
    "duty_hours",
    "block_hours",
    "standby_days",
    "leave_days",
    "sick_days",
]


def build_rows(
    session: Session,
    *,
    operator_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> list[dict[str, object]]:
    """One summary row per active crew member for the pay period."""
    crew = session.scalars(
        select(Crew)
        .where(Crew.operator_id == operator_id)
        .where(Crew.active.is_(True))
        .order_by(Crew.last_name, Crew.first_name)
    ).all()

    fdps = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.operator_id == operator_id)
        .where(FlightDutyPeriod.date >= date_from)
        .where(FlightDutyPeriod.date <= date_to)
    ).all()
    fdps_by_crew: dict[uuid.UUID, list[FlightDutyPeriod]] = {}
    for f in fdps:
        fdps_by_crew.setdefault(f.crew_id, []).append(f)

    # Approved leave overlapping the period, clipped to the window.
    leave = session.scalars(
        select(LeaveRequest)
        .where(LeaveRequest.operator_id == operator_id)
        .where(LeaveRequest.status == LeaveStatus.APPROVED)
        .where(LeaveRequest.date_to >= date_from)
        .where(LeaveRequest.date_from <= date_to)
    ).all()
    leave_days_by_crew: dict[uuid.UUID, int] = {}
    sick_days_by_crew: dict[uuid.UUID, int] = {}
    for lr in leave:
        start = max(lr.date_from, date_from)
        end = min(lr.date_to, date_to)
        days = (end - start).days + 1
        if days <= 0:
            continue
        if lr.type.value == "SICK":
            sick_days_by_crew[lr.crew_id] = sick_days_by_crew.get(lr.crew_id, 0) + days
        else:
            leave_days_by_crew[lr.crew_id] = leave_days_by_crew.get(lr.crew_id, 0) + days

    rows: list[dict[str, object]] = []
    for c in crew:
        crew_fdps = fdps_by_crew.get(c.id, [])
        # 0.0 start keeps the column a float even when a crew has no FDPs
        # (bare sum() of an empty generator returns int 0 → "0" not "0.0").
        duty_h = sum((float(f.duty_hours or 0) for f in crew_fdps if f.type == FdpType.FDP), 0.0)
        block_h = sum((float(f.flight_hours or 0) for f in crew_fdps if f.type == FdpType.FDP), 0.0)
        fdp_count = sum(1 for f in crew_fdps if f.type == FdpType.FDP)
        standby_days = sum(1 for f in crew_fdps if f.type == FdpType.STANDBY)
        rows.append(
            {
                "employee_no": c.employee_no,
                "name": f"{c.first_name} {c.last_name}",
                "role": c.role.value,
                "base": c.base_station,
                "fdp_count": fdp_count,
                "duty_hours": round(duty_h, 2),
                "block_hours": round(block_h, 2),
                "standby_days": standby_days,
                "leave_days": leave_days_by_crew.get(c.id, 0),
                "sick_days": sick_days_by_crew.get(c.id, 0),
            }
        )
    return rows


def to_csv(rows: list[dict[str, object]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_HEADERS)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()
