"""Outstation / ACMI posting endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_writer
from app.models import Crew, Posting, User
from app.models.crew import CrewCategory
from app.schemas.posting import PostingAssignIn, PostingCrewOut, PostingIn, PostingOut
from app.services import postings as postings_service

router = APIRouter()


def _to_out(session: Session, posting: Posting) -> PostingOut:
    crew_ids = postings_service.crew_ids_for_posting(session, posting_id=posting.id)
    crew = session.scalars(select(Crew).where(Crew.id.in_(crew_ids))).all() if crew_ids else []
    crew_sorted = sorted(crew, key=lambda c: (c.crew_category.value, c.role.value, c.employee_no))
    return PostingOut(
        id=posting.id,
        location_icao=posting.location_icao,
        country=posting.country,
        base_tz=posting.base_tz,
        type=posting.type,
        lessee_name=posting.lessee_name,
        start_date=posting.start_date,
        end_date=posting.end_date,
        duration_days=(posting.end_date - posting.start_date).days + 1,
        notes=posting.notes,
        crew=[PostingCrewOut.model_validate(c) for c in crew_sorted],
        engineer_cover=any(c.crew_category is CrewCategory.ENGINEERING for c in crew_sorted),
    )


@router.get("", response_model=list[PostingOut])
def list_postings(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[PostingOut]:
    postings = postings_service.list_postings(session, operator_id=user.operator_id)
    return [_to_out(session, p) for p in postings]


@router.post(
    "",
    response_model=PostingOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_writer)],
)
def create_posting(
    payload: PostingIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> PostingOut:
    try:
        posting = postings_service.create_posting(
            session,
            operator_id=user.operator_id,
            user_id=user.id,
            location_icao=payload.location_icao,
            country=payload.country,
            type=payload.type,
            start_date=payload.start_date,
            end_date=payload.end_date,
            base_tz=payload.base_tz,
            lessee_name=payload.lessee_name,
            notes=payload.notes,
        )
    except postings_service.PostingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session.commit()
    session.refresh(posting)
    return _to_out(session, posting)


@router.get("/{posting_id}", response_model=PostingOut)
def get_posting(
    posting_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> PostingOut:
    posting = session.scalar(
        select(Posting)
        .where(Posting.id == posting_id)
        .where(Posting.operator_id == user.operator_id)
    )
    if posting is None:
        raise HTTPException(status_code=404, detail="posting not found")
    return _to_out(session, posting)


@router.post(
    "/{posting_id}/assign",
    response_model=PostingOut,
    dependencies=[Depends(require_writer)],
)
def assign_crew(
    posting_id: uuid.UUID,
    payload: PostingAssignIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> PostingOut:
    try:
        postings_service.assign_crew(
            session,
            operator_id=user.operator_id,
            user_id=user.id,
            posting_id=posting_id,
            crew_id=payload.crew_id,
        )
    except postings_service.PostingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session.commit()
    posting = session.scalar(select(Posting).where(Posting.id == posting_id))
    assert posting is not None
    return _to_out(session, posting)
