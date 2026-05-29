"""Irregular-operations (IROP) endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User
from app.models.crew import CrewRole
from app.schemas.irop import (
    AltCrewOut,
    CascadeImpactOut,
    IropAlternativesIn,
    IropAssessIn,
    IropAssessmentOut,
)
from app.services import irop as irop_service

router = APIRouter()


@router.post(
    "/assess",
    response_model=IropAssessmentOut,
    summary="Recompute a disrupted duty's FTL legality + cascade (read-only)",
)
def assess(
    payload: IropAssessIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> IropAssessmentOut:
    try:
        a = irop_service.assess_diversion(
            session,
            operator_id=user.operator_id,
            crew_id=payload.crew_id,
            on_date=payload.date,
            extra_flight_h=payload.extra_flight_h,
            extra_ground_h=payload.extra_ground_h,
            discretion_h=payload.discretion_h,
        )
    except irop_service.IropError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return IropAssessmentOut(
        crew_employee_no=a.crew_employee_no,
        date=a.date,
        away_from_base=a.away_from_base,
        original_flight_h=a.original_flight_h,
        original_duty_h=a.original_duty_h,
        original_legality=a.original_legality,
        disrupted_flight_h=a.disrupted_flight_h,
        disrupted_duty_h=a.disrupted_duty_h,
        disrupted_legality=a.disrupted_legality,
        rules_breached=a.rules_breached,
        cascade=CascadeImpactOut(
            next_date=a.cascade.next_date,
            new_rest_h=a.cascade.new_rest_h,
            rest_floor_h=a.cascade.rest_floor_h,
            breached=a.cascade.breached,
        ),
        duty_day_key=a.duty_day_key,
        aircraft_reg=a.aircraft_reg,
        captain_employee_no=a.captain_employee_no,
        fo_employee_no=a.fo_employee_no,
        crew_role_on_duty=a.crew_role_on_duty,
    )


@router.post(
    "/alternatives",
    response_model=list[AltCrewOut],
    summary="Relief crew who could legally take a duty (available first)",
)
def alternatives(
    payload: IropAlternativesIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[AltCrewOut]:
    try:
        role = CrewRole(payload.role.strip().upper())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"unknown role {payload.role!r}") from exc
    rows = irop_service.suggest_alternatives(
        session,
        operator_id=user.operator_id,
        on_date=payload.date,
        role=role,
        aircraft_type=payload.aircraft_type.strip().upper(),
        exclude_crew_id=payload.exclude_crew_id,
    )
    return [AltCrewOut(**vars(r)) for r in rows]
