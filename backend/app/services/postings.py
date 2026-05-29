"""Outstation / ACMI posting service — create postings and assign crew.

Business rules enforced here:
- A posting may not exceed ``MAX_POSTING_DAYS`` (4 weeks) — longer rotations
  must be split so relief crew are rotated in.
- Crew assigned to an *international* posting must hold a valid (unexpired at
  the posting start) work permit or visa.
- A crew member cannot be on two overlapping postings.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Crew, Posting, PostingAssignment
from app.models.document import CrewDocument, DocumentType
from app.models.posting import MAX_POSTING_DAYS, PostingType

# Postings whose country is one of these are treated as domestic (no permit gate).
_HOME_COUNTRIES = {"kenya", "ke"}
_PERMIT_TYPES = (DocumentType.WORK_PERMIT, DocumentType.VISA)


class PostingError(Exception):
    """Raised for posting validation failures (mapped to HTTP 422)."""


def create_posting(
    session: Session,
    *,
    operator_id: uuid.UUID,
    user_id: uuid.UUID,
    location_icao: str,
    country: str,
    type: PostingType,
    start_date: date,
    end_date: date,
    base_tz: str = "Africa/Nairobi",
    lessee_name: str | None = None,
    notes: str | None = None,
) -> Posting:
    if end_date < start_date:
        raise PostingError("end_date is before start_date")
    duration_days = (end_date - start_date).days + 1
    if duration_days > MAX_POSTING_DAYS:
        raise PostingError(
            f"posting spans {duration_days} days — exceeds the {MAX_POSTING_DAYS}-day "
            "rotation limit; split it so relief crew are rotated in"
        )
    posting = Posting(
        operator_id=operator_id,
        created_by_user_id=user_id,
        location_icao=location_icao.strip().upper(),
        country=country.strip(),
        base_tz=base_tz,
        type=type,
        lessee_name=lessee_name,
        start_date=start_date,
        end_date=end_date,
        notes=notes,
    )
    session.add(posting)
    session.flush()
    return posting


def _is_international(country: str) -> bool:
    return country.strip().lower() not in _HOME_COUNTRIES


def _has_valid_permit(session: Session, *, crew_id: uuid.UUID, as_of: date) -> bool:
    doc = session.scalar(
        select(CrewDocument.id)
        .where(CrewDocument.crew_id == crew_id)
        .where(CrewDocument.doc_type.in_(_PERMIT_TYPES))
        .where(or_(CrewDocument.expiry_date.is_(None), CrewDocument.expiry_date >= as_of))
        .limit(1)
    )
    return doc is not None


def _overlaps_existing(
    session: Session, *, operator_id: uuid.UUID, crew_id: uuid.UUID, posting: Posting
) -> bool:
    rows = session.scalars(
        select(Posting)
        .join(PostingAssignment, PostingAssignment.posting_id == Posting.id)
        .where(PostingAssignment.crew_id == crew_id)
        .where(Posting.operator_id == operator_id)
        .where(Posting.id != posting.id)
        # Two ranges overlap iff each starts on/before the other ends.
        .where(Posting.start_date <= posting.end_date)
        .where(Posting.end_date >= posting.start_date)
    ).all()
    return len(rows) > 0


def assign_crew(
    session: Session,
    *,
    operator_id: uuid.UUID,
    user_id: uuid.UUID,
    posting_id: uuid.UUID,
    crew_id: uuid.UUID,
) -> PostingAssignment:
    posting = session.scalar(
        select(Posting).where(Posting.id == posting_id).where(Posting.operator_id == operator_id)
    )
    if posting is None:
        raise PostingError("posting not found")
    crew = session.scalar(
        select(Crew).where(Crew.id == crew_id).where(Crew.operator_id == operator_id)
    )
    if crew is None:
        raise PostingError("crew not found")

    if _is_international(posting.country) and not _has_valid_permit(
        session, crew_id=crew_id, as_of=posting.start_date
    ):
        raise PostingError(
            f"{crew.employee_no} has no valid work permit/visa for an international "
            f"posting to {posting.country} — record one under Documents first"
        )
    if _overlaps_existing(session, operator_id=operator_id, crew_id=crew_id, posting=posting):
        raise PostingError(
            f"{crew.employee_no} is already on an overlapping posting in this period"
        )

    existing = session.scalar(
        select(PostingAssignment)
        .where(PostingAssignment.posting_id == posting_id)
        .where(PostingAssignment.crew_id == crew_id)
    )
    if existing is not None:
        return existing
    pa = PostingAssignment(
        operator_id=operator_id,
        created_by_user_id=user_id,
        posting_id=posting_id,
        crew_id=crew_id,
    )
    session.add(pa)
    session.flush()
    return pa


def list_postings(session: Session, *, operator_id: uuid.UUID) -> list[Posting]:
    return list(
        session.scalars(
            select(Posting)
            .where(Posting.operator_id == operator_id)
            .order_by(Posting.start_date.desc())
        ).all()
    )


def active_posting_for(
    session: Session, *, operator_id: uuid.UUID, crew_id: uuid.UUID, on_date: date
) -> Posting | None:
    """The posting (if any) this crew member is deployed on for ``on_date`` —
    used to flag duties as away-from-base for FTL rest rules."""
    return session.scalar(
        select(Posting)
        .join(PostingAssignment, PostingAssignment.posting_id == Posting.id)
        .where(Posting.operator_id == operator_id)
        .where(PostingAssignment.crew_id == crew_id)
        .where(Posting.start_date <= on_date)
        .where(Posting.end_date >= on_date)
        .limit(1)
    )


def crew_ids_for_posting(session: Session, *, posting_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        session.scalars(
            select(PostingAssignment.crew_id).where(PostingAssignment.posting_id == posting_id)
        ).all()
    )
