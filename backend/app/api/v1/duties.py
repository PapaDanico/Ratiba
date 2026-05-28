"""Non-flight duty endpoints — standby and days off.

Flight duties come from the roster (sectors → publish). This surface lets a
Crewing Officer roster the *other* duty kinds — standby (short/long call)
and OFF days — which then appear in the crew PDF, iCal feed and payroll.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import Crew, FlightDutyPeriod, User
from app.schemas.duty import DutyIn, DutyOut
from app.services import duty_service

router = APIRouter()


def _to_out(fdp: FlightDutyPeriod, crew: Crew | None) -> DutyOut:
    duration = round((fdp.off_duty_time - fdp.report_time).total_seconds() / 3600.0, 2)
    return DutyOut(
        id=fdp.id,
        crew_id=fdp.crew_id,
        employee_no=crew.employee_no if crew else "—",
        crew_name=f"{crew.first_name} {crew.last_name}" if crew else "—",
        date=fdp.date,
        type=fdp.type.value,
        start=fdp.report_time,
        end=fdp.off_duty_time,
        duration_h=duration,
        legality_state=fdp.legality_state.value if fdp.legality_state else None,
    )


@router.get("", response_model=list[DutyOut])
def list_duties(
    date_from: date = Query(...),
    date_to: date = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[DutyOut]:
    return [
        _to_out(fdp, crew)
        for fdp, crew in duty_service.list_duties(
            session, operator_id=user.operator_id, date_from=date_from, date_to=date_to
        )
    ]


@router.post("", response_model=DutyOut, status_code=status.HTTP_201_CREATED)
def assign_duty(
    payload: DutyIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> DutyOut:
    try:
        fdp = duty_service.assign_duty(
            session,
            user=user,
            crew_id=payload.crew_id,
            day=payload.date,
            duty_type=payload.duty_type,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
    except duty_service.DutyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    crew = session.get(Crew, fdp.crew_id)
    return _to_out(fdp, crew)


@router.delete("/{duty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_duty(
    duty_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    try:
        duty_service.delete_duty(session, user=user, duty_id=duty_id)
    except duty_service.DutyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
