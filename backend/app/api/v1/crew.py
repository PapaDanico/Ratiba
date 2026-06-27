"""Crew + currency endpoints — Phase 3."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_writer
from app.core.security import create_ical_token, decode_token
from app.models import Crew, CrewCurrency, User
from app.models.crew import CrewCategory
from app.schemas.crew import (
    CrewIn,
    CrewOut,
    CrewPatch,
    CrossOperatorFtlOut,
    CrossOperatorWindowOut,
    CurrencyIn,
    CurrencyOut,
    CurrencyStatus,
)
from app.schemas.pilot import IssuePairingResponse
from app.services import audit_log, cross_operator, ical_feed
from app.services import pairing as pairing_service

router = APIRouter()

AMBER_THRESHOLD_DAYS = 30


class CalendarFeedOut(BaseModel):
    crew_id: uuid.UUID
    token: str
    path: str  # relative feed path; client prefixes its own origin


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
    category: CrewCategory | None = Query(default=None),
    include_inactive: bool = Query(False, description="Include retired/inactive crew"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[CrewOut]:
    query = _scoped(select(Crew), user).order_by(Crew.last_name, Crew.first_name)
    if not include_inactive:
        query = query.where(Crew.active.is_(True))
    rows = session.scalars(query).all()
    if category is not None:
        rows = [r for r in rows if r.crew_category == category]
    return [CrewOut.model_validate(r) for r in rows]


@router.post(
    "",
    response_model=CrewOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_writer)],
)
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


@router.patch("/{crew_id}", response_model=CrewOut, dependencies=[Depends(require_writer)])
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


@router.delete("/{crew_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_writer)])
def retire_crew(
    crew_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    crew = session.scalar(_scoped(select(Crew).where(Crew.id == crew_id), user))
    if crew is None:
        raise HTTPException(status_code=404, detail="crew not found")
    before = {"active": crew.active}
    crew.active = False
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="RETIRE_CREW",
        entity_type="crew",
        entity_id=crew.id,
        before_state=before,
        after_state={"active": False},
    )
    session.commit()


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
    dependencies=[Depends(require_writer)],
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
    dependencies=[Depends(require_writer)],
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


@router.post(
    "/{crew_id}/calendar-feed",
    response_model=CalendarFeedOut,
    dependencies=[Depends(require_writer)],
)
def issue_calendar_feed(
    crew_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CalendarFeedOut:
    """Mint a subscribe URL for the crew member's roster calendar feed."""
    crew = session.scalar(_scoped(select(Crew).where(Crew.id == crew_id), user))
    if crew is None:
        raise HTTPException(status_code=404, detail="crew not found")
    token = create_ical_token(str(crew_id))
    return CalendarFeedOut(
        crew_id=crew_id,
        token=token,
        path=f"/api/v1/crew/{crew_id}/roster.ics?token={token}",
    )


@router.get("/{crew_id}/roster.ics")
def crew_roster_ics(
    crew_id: uuid.UUID,
    token: str,
    session: Session = Depends(get_db),
) -> Response:
    """Public iCalendar feed for one crew member, authorised by the URL token.

    No bearer auth — calendar clients can't send headers — so the
    capability token in the query string is the credential.
    """
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="invalid feed token") from exc
    if payload.get("type") != "ical" or payload.get("sub") != f"ical:{crew_id}":
        raise HTTPException(status_code=401, detail="feed token does not match this crew")

    crew = ical_feed.crew_for_feed(session, crew_id=crew_id)
    if crew is None:
        raise HTTPException(status_code=404, detail="crew not found")

    body = ical_feed.build_feed(session, crew=crew)
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'inline; filename="ratiba-{crew_id}.ics"'},
    )


@router.get(
    "/{crew_id}/cross-operator-ftl",
    response_model=CrossOperatorFtlOut,
    summary="Cumulative FTL totals across every operator this person flies for",
)
def cross_operator_ftl(
    crew_id: uuid.UUID,
    as_of: date = Query(default_factory=date.today),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CrossOperatorFtlOut:
    """Privacy-preserving aggregate: when the crew member shares a person_ref
    with crew in other operators, their duty/block totals over the rolling FTL
    windows reflect all of it — without exposing other operators' duty detail."""
    try:
        summary = cross_operator.cross_operator_ftl_summary(
            session, operator_id=user.operator_id, crew_id=crew_id, as_of=as_of
        )
    except cross_operator.CrossOperatorError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CrossOperatorFtlOut(
        crew_employee_no=summary.crew_employee_no,
        person_ref=summary.person_ref,
        linked=summary.linked,
        operator_count=summary.operator_count,
        as_of=summary.as_of,
        windows=[CrossOperatorWindowOut(**vars(w)) for w in summary.windows],
    )
