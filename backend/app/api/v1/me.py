"""Pilot-facing ``/crew/me`` endpoints — bot + mobile web view share this surface."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_pilot
from app.models import (
    Crew,
    CrewCurrency,
    FlightDutyPeriod,
    LeaveRequest,
    Sector,
    SectorAssignment,
    SwapRequest,
)
from app.models.leave import LeaveStatus
from app.models.swap import SwapStatus
from app.schemas.leave_swap import LeaveRequestOut, SwapRequestOut
from app.schemas.pilot import (
    PilotCurrencyOut,
    PilotCurrencyResponse,
    PilotDutyDay,
    PilotDutyTodayResponse,
    PilotLeaveRequestIn,
    PilotProfile,
    PilotRosterResponse,
    PilotSwapRequestIn,
)
from app.services import audit_log

router = APIRouter()

AMBER_THRESHOLD_DAYS = 30
DEFAULT_ROSTER_WINDOW_DAYS = 14


@router.get("", response_model=PilotProfile)
def me(crew: Crew = Depends(get_current_pilot)) -> PilotProfile:
    return PilotProfile.model_validate(crew)


def _duty_days_for_crew(
    session: Session, *, crew: Crew, date_from: date, date_to: date
) -> list[PilotDutyDay]:
    assignments = session.scalars(
        select(SectorAssignment).where(SectorAssignment.crew_id == crew.id)
    ).all()
    if not assignments:
        return []
    sector_ids = [a.sector_id for a in assignments]
    sectors = session.scalars(
        select(Sector)
        .where(Sector.id.in_(sector_ids))
        .where(Sector.date >= date_from)
        .where(Sector.date <= date_to)
    ).all()
    sectors_by_id = {s.id: s for s in sectors}
    fdps = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.crew_id == crew.id)
        .where(FlightDutyPeriod.date >= date_from)
        .where(FlightDutyPeriod.date <= date_to)
    ).all()
    fdp_by_date: dict[date, FlightDutyPeriod] = {f.date: f for f in fdps}

    # Group by (aircraft_reg, date).
    grouped: dict[tuple[str, date, str], list[str]] = {}
    role_for: dict[tuple[str, date], str] = {}
    types_for: dict[tuple[str, date], str] = {}
    for a in assignments:
        sector = sectors_by_id.get(a.sector_id)
        if sector is None:
            continue
        key = (sector.aircraft_reg, sector.date, a.role_on_sector)
        grouped.setdefault(key, []).append(sector.flight_no)
        role_for[(sector.aircraft_reg, sector.date)] = a.role_on_sector
        types_for[(sector.aircraft_reg, sector.date)] = sector.aircraft_type

    out: list[PilotDutyDay] = []
    for (reg, day, role), sector_ids_list in sorted(grouped.items()):
        fdp = fdp_by_date.get(day)
        out.append(
            PilotDutyDay(
                date_local=day,
                aircraft_reg=reg,
                aircraft_type=types_for[(reg, day)],
                sector_ids=sorted(sector_ids_list),
                role_on_duty=role,
                report_time=fdp.report_time if fdp else None,
                off_duty_time=fdp.off_duty_time if fdp else None,
                flight_hours=fdp.flight_hours if fdp else None,
                duty_hours=fdp.duty_hours if fdp else None,
                legality_state=fdp.legality_state if fdp else None,
            )
        )
    return out


@router.get("/roster", response_model=PilotRosterResponse)
def my_roster(
    session: Session = Depends(get_db),
    crew: Crew = Depends(get_current_pilot),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> PilotRosterResponse:
    today = date.today()
    df = date_from or today
    dt = date_to or today + timedelta(days=DEFAULT_ROSTER_WINDOW_DAYS - 1)
    if dt < df:
        raise HTTPException(status_code=400, detail="date_to before date_from")
    days = _duty_days_for_crew(session, crew=crew, date_from=df, date_to=dt)
    return PilotRosterResponse(date_from=df, date_to=dt, duty_days=days)


@router.get("/duty", response_model=PilotDutyTodayResponse)
def my_duty_today(
    session: Session = Depends(get_db),
    crew: Crew = Depends(get_current_pilot),
) -> PilotDutyTodayResponse:
    today = date.today()
    days = _duty_days_for_crew(session, crew=crew, date_from=today, date_to=today)
    if not days:
        return PilotDutyTodayResponse(has_duty=False)
    return PilotDutyTodayResponse(has_duty=True, duty_day=days[0])


@router.get("/currency", response_model=PilotCurrencyResponse)
def my_currency(
    session: Session = Depends(get_db),
    crew: Crew = Depends(get_current_pilot),
) -> PilotCurrencyResponse:
    rows = session.scalars(
        select(CrewCurrency)
        .where(CrewCurrency.crew_id == crew.id)
        .order_by(CrewCurrency.expires_date)
    ).all()
    today = date.today()
    out: list[PilotCurrencyOut] = []
    for r in rows:
        delta = (r.expires_date - today).days
        state = "RED" if delta < 0 else "AMBER" if delta <= AMBER_THRESHOLD_DAYS else "GREEN"
        out.append(
            PilotCurrencyOut(
                currency_type=r.currency_type.value,
                expires_date=r.expires_date,
                days_remaining=delta,
                state=state,
            )
        )
    return PilotCurrencyResponse(currencies=out)


@router.post("/leave", response_model=LeaveRequestOut)
def my_leave_submit(
    payload: PilotLeaveRequestIn,
    session: Session = Depends(get_db),
    crew: Crew = Depends(get_current_pilot),
) -> LeaveRequestOut:
    row = LeaveRequest(
        operator_id=crew.operator_id,
        crew_id=crew.id,
        type=payload.type,
        date_from=payload.date_from,
        date_to=payload.date_to,
        note=payload.note,
        status=LeaveStatus.PENDING,
    )
    session.add(row)
    session.flush()
    audit_log.record(
        session,
        operator_id=crew.operator_id,
        actor_user_id=None,
        action="PILOT_SUBMIT_LEAVE",
        entity_type="leave_request",
        entity_id=row.id,
        before_state=None,
        after_state={
            "crew_id": str(crew.id),
            "type": payload.type.value,
            "date_from": payload.date_from.isoformat(),
            "date_to": payload.date_to.isoformat(),
        },
    )
    session.commit()
    session.refresh(row)
    return LeaveRequestOut.model_validate(row)


@router.post("/swap", response_model=SwapRequestOut)
def my_swap_submit(
    payload: PilotSwapRequestIn,
    session: Session = Depends(get_db),
    crew: Crew = Depends(get_current_pilot),
) -> SwapRequestOut:
    counterparty = session.scalar(
        select(Crew)
        .where(Crew.operator_id == crew.operator_id)
        .where(Crew.employee_no == payload.counterparty_employee_no)
    )
    if counterparty is None:
        raise HTTPException(
            status_code=404,
            detail=f"counterparty {payload.counterparty_employee_no!r} not found",
        )
    row = SwapRequest(
        operator_id=crew.operator_id,
        crew_id_initiator=crew.id,
        crew_id_counterparty=counterparty.id,
        fdp_or_sector_ref=payload.fdp_or_sector_ref,
        reason=payload.reason,
        status=SwapStatus.PENDING,
    )
    session.add(row)
    session.flush()
    audit_log.record(
        session,
        operator_id=crew.operator_id,
        actor_user_id=None,
        action="PILOT_SUBMIT_SWAP",
        entity_type="swap_request",
        entity_id=row.id,
        before_state=None,
        after_state={
            "initiator": crew.employee_no,
            "counterparty": counterparty.employee_no,
            "ref": payload.fdp_or_sector_ref,
        },
    )
    session.commit()
    session.refresh(row)
    return SwapRequestOut.model_validate(row)
