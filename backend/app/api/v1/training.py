"""Training endpoints: type-rating management + recurrency tracking.

Type ratings and recurrent currencies are what gate a crew member onto a
duty. This surface lets the Crewing Officer add/withdraw type ratings and
see — in one urgency-sorted list — every qualification about to lapse, so
nothing expires unnoticed. The auto-roster reads the same data.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import Crew, CrewCurrency, CrewTypeRating, User
from app.schemas.training import RecurrencyItem, TypeRatingIn, TypeRatingOut
from app.services import audit_log

router = APIRouter()

AMBER_THRESHOLD_DAYS = 30


def _state(days_remaining: int) -> str:
    if days_remaining < 0:
        return "RED"
    if days_remaining <= AMBER_THRESHOLD_DAYS:
        return "AMBER"
    return "GREEN"


def _crew_map(session: Session, operator_id: uuid.UUID) -> dict[uuid.UUID, Crew]:
    crew = session.scalars(select(Crew).where(Crew.operator_id == operator_id)).all()
    return {c.id: c for c in crew}


@router.get("/type-ratings", response_model=list[TypeRatingOut])
def list_type_ratings(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[TypeRatingOut]:
    today = date.today()
    crew_by_id = _crew_map(session, user.operator_id)
    rows = session.scalars(
        select(CrewTypeRating)
        .where(CrewTypeRating.operator_id == user.operator_id)
        .order_by(CrewTypeRating.valid_until)
    ).all()
    out: list[TypeRatingOut] = []
    for r in rows:
        c = crew_by_id.get(r.crew_id)
        days = (r.valid_until - today).days
        out.append(
            TypeRatingOut(
                id=r.id,
                crew_id=r.crew_id,
                employee_no=c.employee_no if c else "—",
                crew_name=f"{c.first_name} {c.last_name}" if c else "—",
                aircraft_type=r.aircraft_type,
                valid_from=r.valid_from,
                valid_until=r.valid_until,
                evidence_ref=r.evidence_ref,
                days_remaining=days,
                state=_state(days),
            )
        )
    return out


@router.post(
    "/crew/{crew_id}/type-ratings",
    response_model=TypeRatingOut,
    status_code=status.HTTP_201_CREATED,
)
def add_type_rating(
    crew_id: uuid.UUID,
    payload: TypeRatingIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> TypeRatingOut:
    if payload.valid_until < payload.valid_from:
        raise HTTPException(status_code=422, detail="valid_until before valid_from")
    crew = session.scalar(
        select(Crew).where(Crew.id == crew_id).where(Crew.operator_id == user.operator_id)
    )
    if crew is None:
        raise HTTPException(status_code=404, detail="crew not found")
    rating = CrewTypeRating(
        operator_id=user.operator_id,
        created_by_user_id=user.id,
        crew_id=crew_id,
        aircraft_type=payload.aircraft_type.strip().upper(),
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        evidence_ref=payload.evidence_ref,
    )
    session.add(rating)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="ADD_TYPE_RATING",
        entity_type="crew_type_rating",
        entity_id=rating.id,
        before_state=None,
        after_state=payload.model_dump(mode="json"),
    )
    session.commit()
    session.refresh(rating)
    today = date.today()
    days = (rating.valid_until - today).days
    return TypeRatingOut(
        id=rating.id,
        crew_id=crew_id,
        employee_no=crew.employee_no,
        crew_name=f"{crew.first_name} {crew.last_name}",
        aircraft_type=rating.aircraft_type,
        valid_from=rating.valid_from,
        valid_until=rating.valid_until,
        evidence_ref=rating.evidence_ref,
        days_remaining=days,
        state=_state(days),
    )


@router.delete("/type-ratings/{rating_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_type_rating(
    rating_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    rating = session.scalar(
        select(CrewTypeRating)
        .where(CrewTypeRating.id == rating_id)
        .where(CrewTypeRating.operator_id == user.operator_id)
    )
    if rating is None:
        raise HTTPException(status_code=404, detail="type rating not found")
    session.delete(rating)
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="DELETE_TYPE_RATING",
        entity_type="crew_type_rating",
        entity_id=rating_id,
        before_state={"aircraft_type": rating.aircraft_type, "crew_id": str(rating.crew_id)},
        after_state=None,
    )
    session.commit()


@router.get("/recurrency", response_model=list[RecurrencyItem])
def recurrency(
    within_days: int = Query(default=90, ge=1, le=365),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[RecurrencyItem]:
    """Every currency + type rating lapsing within ``within_days`` (plus all
    already-expired), urgency-sorted. The operator's single proactive view of
    what needs renewing."""
    today = date.today()
    horizon = today.toordinal() + within_days
    crew_by_id = _crew_map(session, user.operator_id)

    items: list[RecurrencyItem] = []

    currencies = session.scalars(
        select(CrewCurrency).where(CrewCurrency.operator_id == user.operator_id)
    ).all()
    for cur in currencies:
        days = (cur.expires_date - today).days
        if cur.expires_date.toordinal() > horizon:
            continue
        c = crew_by_id.get(cur.crew_id)
        items.append(
            RecurrencyItem(
                crew_id=cur.crew_id,
                employee_no=c.employee_no if c else "—",
                crew_name=f"{c.first_name} {c.last_name}" if c else "—",
                kind="currency",
                label=cur.currency_type.value,
                expires_date=cur.expires_date,
                days_remaining=days,
                state=_state(days),
            )
        )

    ratings = session.scalars(
        select(CrewTypeRating).where(CrewTypeRating.operator_id == user.operator_id)
    ).all()
    for r in ratings:
        days = (r.valid_until - today).days
        if r.valid_until.toordinal() > horizon:
            continue
        c = crew_by_id.get(r.crew_id)
        items.append(
            RecurrencyItem(
                crew_id=r.crew_id,
                employee_no=c.employee_no if c else "—",
                crew_name=f"{c.first_name} {c.last_name}" if c else "—",
                kind="type_rating",
                label=f"Type rating: {r.aircraft_type}",
                expires_date=r.valid_until,
                days_remaining=days,
                state=_state(days),
            )
        )

    items.sort(key=lambda i: i.days_remaining)
    return items
