"""Flight routing (sector) CRUD — the schedule the auto-roster assigns to.

Sectors created here start as PLANNED. The auto-roster reads them, the
optimiser assigns crew, and publishing flips them to PUBLISHED. Times are
stored and returned in UTC.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_writer
from app.models import Sector, User
from app.models.roster import SectorStatus
from app.schemas.sector import (
    RecurringSectorIn,
    RecurringSectorResult,
    SectorIn,
    SectorOut,
)
from app.services import audit_log

router = APIRouter()

# Guard against runaway expansion (≈ one year of daily flights).
MAX_GENERATED_SECTORS = 366


def _block_hours(s: Sector) -> float:
    return round((s.sta - s.std).total_seconds() / 3600.0, 2)


def _to_out(s: Sector) -> SectorOut:
    return SectorOut(
        id=s.id,
        flight_no=s.flight_no,
        date=s.date,
        origin=s.origin,
        destination=s.destination,
        std=s.std,
        sta=s.sta,
        aircraft_reg=s.aircraft_reg,
        aircraft_type=s.aircraft_type,
        status=s.status.value,
        block_hours=_block_hours(s),
    )


@router.get("", response_model=list[SectorOut])
def list_sectors(
    date_from: date = Query(...),
    date_to: date = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[SectorOut]:
    rows = session.scalars(
        select(Sector)
        .where(Sector.operator_id == user.operator_id)
        .where(Sector.date >= date_from)
        .where(Sector.date <= date_to)
        .order_by(Sector.date, Sector.std)
    ).all()
    return [_to_out(s) for s in rows]


@router.post(
    "",
    response_model=SectorOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_writer)],
)
def create_sector(
    payload: SectorIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SectorOut:
    if payload.sta <= payload.std:
        raise HTTPException(status_code=422, detail="sta must be after std")
    sector = Sector(
        operator_id=user.operator_id,
        created_by_user_id=user.id,
        flight_no=payload.flight_no,
        date=payload.date,
        origin=payload.origin,
        destination=payload.destination,
        std=payload.std,
        sta=payload.sta,
        aircraft_reg=payload.aircraft_reg,
        aircraft_type=payload.aircraft_type,
        status=SectorStatus.PLANNED,
    )
    session.add(sector)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="CREATE_SECTOR",
        entity_type="sector",
        entity_id=sector.id,
        before_state=None,
        after_state=payload.model_dump(mode="json"),
    )
    session.commit()
    session.refresh(sector)
    return _to_out(sector)


@router.post(
    "/recurring",
    response_model=RecurringSectorResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_writer)],
)
def create_recurring_sectors(
    payload: RecurringSectorIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RecurringSectorResult:
    """Expand a recurrence into one PLANNED routing per matching date.

    Dedupes by (flight_no, date) so re-running the same pattern doesn't
    create duplicates — already-present dates are reported as skipped.
    """
    if payload.date_to < payload.date_from:
        raise HTTPException(status_code=422, detail="date_to before date_from")

    wanted = set(payload.days_of_week)  # empty → every day
    target_dates: list[date] = []
    d = payload.date_from
    while d <= payload.date_to:
        if not wanted or d.weekday() in wanted:
            target_dates.append(d)
        d += timedelta(days=1)

    if not target_dates:
        raise HTTPException(
            status_code=422, detail="no dates match the selected days of week in this range"
        )
    if len(target_dates) > MAX_GENERATED_SECTORS:
        raise HTTPException(
            status_code=422,
            detail=f"pattern would create {len(target_dates)} routings "
            f"(limit {MAX_GENERATED_SECTORS}); narrow the date range",
        )

    # Existing flight_no dates so we can skip duplicates.
    existing_dates = set(
        session.scalars(
            select(Sector.date)
            .where(Sector.operator_id == user.operator_id)
            .where(Sector.flight_no == payload.flight_no)
            .where(Sector.date >= payload.date_from)
            .where(Sector.date <= payload.date_to)
        ).all()
    )

    created: list[Sector] = []
    skipped = 0
    for day in target_dates:
        if day in existing_dates:
            skipped += 1
            continue
        std = datetime.combine(day, payload.std_time, tzinfo=UTC)
        sta = datetime.combine(day, payload.sta_time, tzinfo=UTC)
        if sta <= std:  # overnight sector
            sta += timedelta(days=1)
        sector = Sector(
            operator_id=user.operator_id,
            created_by_user_id=user.id,
            flight_no=payload.flight_no,
            date=day,
            origin=payload.origin,
            destination=payload.destination,
            std=std,
            sta=sta,
            aircraft_reg=payload.aircraft_reg,
            aircraft_type=payload.aircraft_type,
            status=SectorStatus.PLANNED,
        )
        session.add(sector)
        created.append(sector)

    if created:
        session.flush()
        audit_log.record(
            session,
            operator_id=user.operator_id,
            actor_user_id=user.id,
            action="CREATE_RECURRING_SECTORS",
            entity_type="sector",
            entity_id=None,
            before_state=None,
            after_state={
                "flight_no": payload.flight_no,
                "date_from": payload.date_from.isoformat(),
                "date_to": payload.date_to.isoformat(),
                "days_of_week": payload.days_of_week,
                "created": len(created),
                "skipped_existing": skipped,
            },
        )
        session.commit()
        for s in created:
            session.refresh(s)

    return RecurringSectorResult(
        created=len(created),
        skipped_existing=skipped,
        sectors=[_to_out(s) for s in created],
    )


@router.delete(
    "/{sector_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_writer)]
)
def delete_sector(
    sector_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    sector = session.scalar(
        select(Sector).where(Sector.id == sector_id).where(Sector.operator_id == user.operator_id)
    )
    if sector is None:
        raise HTTPException(status_code=404, detail="sector not found")
    if sector.status != SectorStatus.PLANNED:
        raise HTTPException(
            status_code=409,
            detail="only PLANNED sectors can be deleted; this one is already published",
        )
    session.delete(sector)
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="DELETE_SECTOR",
        entity_type="sector",
        entity_id=sector_id,
        before_state={"flight_no": sector.flight_no, "date": sector.date.isoformat()},
        after_state=None,
    )
    session.commit()
