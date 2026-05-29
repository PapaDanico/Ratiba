"""Operational exports — payroll CSV (more report formats land here later)."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import Crew, FlightDutyPeriod, Operator, Posting, PostingAssignment, User
from app.models.ftl import FdpType
from app.services import fatigue, payroll

router = APIRouter()


class FatigueRowOut(BaseModel):
    employee_no: str
    name: str
    role: str
    fdp_count: int
    night_fdp_count: int
    night_pct: float
    max_consecutive_days: int
    elevated_count: int
    high_count: int
    peak_score: int
    peak_band: str


@router.get(
    "/payroll.csv",
    summary="Per-crew duty + block hours for a pay period (CSV)",
    response_class=StreamingResponse,
)
def payroll_csv(
    date_from: date = Query(...),
    date_to: date = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> StreamingResponse:
    if date_to < date_from:
        raise HTTPException(status_code=422, detail="date_to before date_from")
    rows = payroll.build_rows(
        session,
        operator_id=user.operator_id,
        date_from=date_from,
        date_to=date_to,
    )
    body = payroll.to_csv(rows)
    filename = f"payroll_{date_from.isoformat()}_{date_to.isoformat()}.csv"
    return StreamingResponse(
        iter([body]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/fatigue",
    response_model=list[FatigueRowOut],
    summary="Per-crew fatigue indicators (FRMS-aligned screen) for a period",
)
def fatigue_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[FatigueRowOut]:
    """Advisory fatigue screen per crew over the period — not a legal verdict.
    Crew with no duties in the window are omitted; most-fatigued first."""
    if date_to < date_from:
        raise HTTPException(status_code=422, detail="date_to before date_from")

    operator = session.scalar(select(Operator).where(Operator.id == user.operator_id))
    base_tz = operator.timezone if operator is not None else "Africa/Nairobi"

    crew = {
        c.id: c
        for c in session.scalars(select(Crew).where(Crew.operator_id == user.operator_id)).all()
    }
    fdps = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.operator_id == user.operator_id)
        .where(FlightDutyPeriod.date >= date_from)
        .where(FlightDutyPeriod.date <= date_to)
        .where(FlightDutyPeriod.type == FdpType.FDP)
    ).all()

    # Per-duty timezone: a duty flown while on an outstation posting is
    # acclimatised to that posting's base; otherwise the operator home tz.
    posting_spans: dict[uuid.UUID, list[tuple[date, date, str]]] = {}
    for r in session.execute(
        select(
            PostingAssignment.crew_id.label("p_crew"),
            Posting.start_date.label("p_start"),
            Posting.end_date.label("p_end"),
            Posting.base_tz.label("p_tz"),
        )
        .join(Posting, Posting.id == PostingAssignment.posting_id)
        .where(Posting.operator_id == user.operator_id)
        .where(Posting.start_date <= date_to)
        .where(Posting.end_date >= date_from)
    ).all():
        posting_spans.setdefault(r.p_crew, []).append((r.p_start, r.p_end, r.p_tz))

    def tz_for(crew_id: uuid.UUID, on_date: date) -> str:
        for start, end, tz in posting_spans.get(crew_id, ()):
            if start <= on_date <= end:
                return tz
        return base_tz

    duties_by_crew: dict[uuid.UUID, list[fatigue.DutyFacts]] = {}
    for f in fdps:
        duties_by_crew.setdefault(f.crew_id, []).append(
            fatigue.DutyFacts(
                date=f.date,
                report_time=f.report_time,
                off_duty_time=f.off_duty_time,
                duty_hours=float(f.duty_hours or 0),
                sectors_count=f.sectors_count,
                tz=tz_for(f.crew_id, f.date),
            )
        )

    rows: list[FatigueRowOut] = []
    for crew_id, duties in duties_by_crew.items():
        c = crew.get(crew_id)
        if c is None:
            continue
        s = fatigue.summarise_duties(duties, base_tz=base_tz)
        rows.append(
            FatigueRowOut(
                employee_no=c.employee_no,
                name=f"{c.first_name} {c.last_name}",
                role=c.role.value,
                fdp_count=s.fdp_count,
                night_fdp_count=s.night_fdp_count,
                night_pct=s.night_pct,
                max_consecutive_days=s.max_consecutive_days,
                elevated_count=s.elevated_count,
                high_count=s.high_count,
                peak_score=s.peak_score,
                peak_band="HIGH"
                if s.peak_score >= 60
                else "ELEVATED"
                if s.peak_score >= 30
                else "LOW",
            )
        )
    rows.sort(key=lambda r: r.peak_score, reverse=True)
    return rows
