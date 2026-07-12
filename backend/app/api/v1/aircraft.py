"""Aircraft fleet-registry endpoints — Phase 7 (operator fleet)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_writer
from app.models import Aircraft, Sector, User
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
) -> list[AircraftOut]:
    rows = session.scalars(
        select(Aircraft)
        .where(Aircraft.operator_id == user.operator_id)
        .order_by(Aircraft.registration)
    ).all()
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


@router.delete(
    "/{aircraft_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_writer)],
)
def delete_aircraft(
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
    sector_count = session.scalar(
        select(func.count())
        .select_from(Sector)
        .where(Sector.operator_id == user.operator_id)
        .where(Sector.aircraft_reg == aircraft.registration)
    )
    if sector_count:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{aircraft.registration} has {sector_count} flight sector(s) on "
                "record — deactivate it instead of deleting"
            ),
        )
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="DELETE_AIRCRAFT",
        entity_type="aircraft",
        entity_id=aircraft.id,
        before_state={"registration": aircraft.registration, "aircraft_type": aircraft.aircraft_type},
        after_state=None,
    )
    session.delete(aircraft)
    session.commit()


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
