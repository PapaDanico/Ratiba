"""Crew + currency endpoints — Phase 3."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import Crew, CrewCurrency, User
from app.schemas.crew import (
    CrewIn,
    CrewOut,
    CrewPatch,
    CurrencyIn,
    CurrencyOut,
    CurrencyStatus,
)
from app.schemas.pilot import IssuePairingResponse
from app.services import audit_log
from app.services import pairing as pairing_service

router = APIRouter()

AMBER_THRESHOLD_DAYS = 30


def _scoped(query: Select[Any], user: User) -> Select[Any]:
    return query.where(Crew.operator_id == user.operator_id)


# Specific routes first — declaration order matters for matching.


@router.get("/currency/dashboard", response_model=list[CurrencyStatus])
def currency_dashboard(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[CurrencyStatus]:
    """Single endpoint feeding the dashboard's traffic-light view."""
    rows = session.scalars(
        select(CrewCurrency).where(CrewCurrency.operator_id == user.operator_id)
    ).all()
    today = date.today()
    out: list[CurrencyStatus] = []
    for r in rows:
        delta = (r.expires_date - today).days
        if delta < 0:
            state = "RED"
        elif delta <= AMBER_THRESHOLD_DAYS:
            state = "AMBER"
        else:
            state = "GREEN"
        out.append(
            CurrencyStatus(
                crew_id=r.crew_id,
                currency_type=r.currency_type,
                expires_date=r.expires_date,
                days_remaining=delta,
                state=state,
            )
        )
    return out


@router.get("", response_model=list[CrewOut])
def list_crew(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[CrewOut]:
    rows = session.scalars(
        _scoped(select(Crew), user).order_by(Crew.last_name, Crew.first_name)
    ).all()
    return [CrewOut.model_validate(r) for r in rows]


@router.post("", response_model=CrewOut, status_code=status.HTTP_201_CREATED)
def create_crew(
    payload: CrewIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CrewOut:
    crew = Crew(operator_id=user.operator_id, created_by_user_id=user.id, **payload.model_dump())
    session.add(crew)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="CREATE_CREW",
        entity_type="crew",
        entity_id=crew.id,
        before_state=None,
        after_state=payload.model_dump(mode="json"),
    )
    session.commit()
    session.refresh(crew)
    return CrewOut.model_validate(crew)


@router.get("/{crew_id}", response_model=CrewOut)
def get_crew(
    crew_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CrewOut:
    crew = session.scalar(_scoped(select(Crew).where(Crew.id == crew_id), user))
    if crew is None:
        raise HTTPException(status_code=404, detail="crew not found")
    return CrewOut.model_validate(crew)


@router.patch("/{crew_id}", response_model=CrewOut)
def update_crew(
    crew_id: uuid.UUID,
    payload: CrewPatch,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CrewOut:
    crew = session.scalar(_scoped(select(Crew).where(Crew.id == crew_id), user))
    if crew is None:
        raise HTTPException(status_code=404, detail="crew not found")

    before = CrewOut.model_validate(crew).model_dump(mode="json")
    updates = payload.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(crew, k, v)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="UPDATE_CREW",
        entity_type="crew",
        entity_id=crew.id,
        before_state=before,
        after_state=CrewOut.model_validate(crew).model_dump(mode="json"),
    )
    session.commit()
    session.refresh(crew)
    return CrewOut.model_validate(crew)


@router.get("/{crew_id}/currency", response_model=list[CurrencyOut])
def list_currency(
    crew_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[CurrencyOut]:
    rows = session.scalars(
        select(CrewCurrency)
        .where(CrewCurrency.crew_id == crew_id)
        .where(CrewCurrency.operator_id == user.operator_id)
        .order_by(CrewCurrency.expires_date)
    ).all()
    return [CurrencyOut.model_validate(r) for r in rows]


@router.post(
    "/{crew_id}/currency",
    response_model=CurrencyOut,
    status_code=status.HTTP_201_CREATED,
)
def record_currency(
    crew_id: uuid.UUID,
    payload: CurrencyIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CurrencyOut:
    crew = session.scalar(_scoped(select(Crew).where(Crew.id == crew_id), user))
    if crew is None:
        raise HTTPException(status_code=404, detail="crew not found")
    row = CrewCurrency(
        operator_id=user.operator_id,
        created_by_user_id=user.id,
        crew_id=crew_id,
        **payload.model_dump(),
    )
    session.add(row)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="RECORD_CURRENCY",
        entity_type="crew_currency",
        entity_id=row.id,
        before_state=None,
        after_state=payload.model_dump(mode="json"),
    )
    session.commit()
    session.refresh(row)
    return CurrencyOut.model_validate(row)


@router.post(
    "/{crew_id}/pairing-token",
    response_model=IssuePairingResponse,
    status_code=status.HTTP_201_CREATED,
)
def issue_pairing_token(
    crew_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> IssuePairingResponse:
    """Issue a short-lived pairing code so a pilot can link the bot/web view."""
    try:
        token = pairing_service.issue_pairing_code(session, user=user, crew_id=crew_id)
    except pairing_service.PairingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return IssuePairingResponse(code=token.code, expires_at=token.expires_at)
