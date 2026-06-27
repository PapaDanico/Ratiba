"""Aircraft fleet-registry endpoints — Phase 7 (operator fleet)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_writer
from app.models import Aircraft, User
from app.schemas.aircraft import AircraftIn, AircraftOut, AircraftPatch
from app.services import aircraft_types, audit_log

router = APIRouter()


def _to_out(a: Aircraft) -> AircraftOut:
    out = AircraftOut.model_validate(a)
    out.aircraft_type_known = aircraft_types.is_known(a.aircraft_type)
    return out


@router.get("", response_model=list[AircraftOut])
def list_fleet(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    include_inactive: bool = Query(False, description="Include retired/inactive aircraft"),
) -> list[AircraftOut]:
    query = select(Aircraft).where(Aircraft.operator_id == user.operator_id)
    if not include_inactive:
        query = query.where(Aircraft.active.is_(True))
    rows = session.scalars(query.order_by(Aircraft.registration)).all()
    return [_to_out(a) for a in rows]


@router.post(
    "",
    response_model=AircraftOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_writer)],
)
def add_aircraft(
    payload: AircraftIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> AircraftOut:
    reg = payload.registration.strip().upper()
    existing = session.scalar(
        select(Aircraft)
        .where(Aircraft.operator_id == user.operator_id)
        .where(Aircraft.registration == reg)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"{reg} already registered")
    aircraft = Aircraft(
        operator_id=user.operator_id,
        created_by_user_id=user.id,
        registration=reg,
        aircraft_type=payload.aircraft_type.strip().upper(),
        active=payload.active,
    )
    session.add(aircraft)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="ADD_AIRCRAFT",
        entity_type="aircraft",
        entity_id=aircraft.id,
        before_state=None,
        after_state={"registration": reg, "aircraft_type": aircraft.aircraft_type},
    )
    session.commit()
    session.refresh(aircraft)
    return _to_out(aircraft)


@router.patch("/{aircraft_id}", response_model=AircraftOut, dependencies=[Depends(require_writer)])
def update_aircraft(
    aircraft_id: uuid.UUID,
    payload: AircraftPatch,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> AircraftOut:
    aircraft = session.scalar(
        select(Aircraft)
        .where(Aircraft.id == aircraft_id)
        .where(Aircraft.operator_id == user.operator_id)
    )
    if aircraft is None:
        raise HTTPException(status_code=404, detail="aircraft not found")
    before = {"aircraft_type": aircraft.aircraft_type, "active": aircraft.active}
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("aircraft_type"):
        aircraft.aircraft_type = updates["aircraft_type"].strip().upper()
    if "active" in updates and updates["active"] is not None:
        aircraft.active = updates["active"]
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="UPDATE_AIRCRAFT",
        entity_type="aircraft",
        entity_id=aircraft.id,
        before_state=before,
        after_state={"aircraft_type": aircraft.aircraft_type, "active": aircraft.active},
    )
    session.commit()
    session.refresh(aircraft)
    return _to_out(aircraft)


@router.delete("/{aircraft_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_writer)])
def retire_aircraft(
    aircraft_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    aircraft = session.scalar(
        select(Aircraft)
        .where(Aircraft.id == aircraft_id)
        .where(Aircraft.operator_id == user.operator_id)
    )
    if aircraft is None:
        raise HTTPException(status_code=404, detail="aircraft not found")
    before = {"active": aircraft.active}
    aircraft.active = False
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="RETIRE_AIRCRAFT",
        entity_type="aircraft",
        entity_id=aircraft.id,
        before_state=before,
        after_state={"active": False},
    )
    session.commit()
