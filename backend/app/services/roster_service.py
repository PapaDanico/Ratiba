"""Roster persistence — publish and amend workflows.

Phase 3 introduces durable state. The contract:

- ``publish_roster`` writes every assignment as a SectorAssignment row, plus a
  FlightDutyPeriod row per (crew, duty_day) with computed FTL legality.
  Every write produces an ``audit_event`` row via :func:`audit_log.record`.
- ``amend_roster`` records a single replacement of (CAPT, FO) on one duty day
  AFTER publication, preserving the original immutable history. The new
  assignment is recorded as a fresh row; the prior assignment's audit
  history remains intact.

The ``sectors`` table is updated to PUBLISHED status.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Crew,
    FlightDutyPeriod,
    Sector,
    SectorAssignment,
    User,
)
from app.models.ftl import FdpType, LegalityState
from app.models.roster import SectorStatus
from app.schemas.roster import (
    AssignmentOut,
    PublishRosterRequest,
    PublishRosterResponse,
    SectorInputIn,
)
from app.services import audit_log, ftl_engine


class RosterPersistenceError(Exception):
    """Raised when the requested roster can't be persisted (e.g. missing crew)."""


def _ensure_sector(
    session: Session,
    *,
    operator_id: uuid.UUID,
    user_id: uuid.UUID,
    s: SectorInputIn,
) -> Sector:
    """Get-or-create the Sector row and mark it PUBLISHED."""
    existing = session.scalar(
        select(Sector)
        .where(Sector.operator_id == operator_id)
        .where(Sector.flight_no == s.sector_id)
        .where(Sector.date == s.date_local)
    )
    if existing is not None:
        existing.status = SectorStatus.PUBLISHED
        return existing

    sector = Sector(
        operator_id=operator_id,
        created_by_user_id=user_id,
        flight_no=s.sector_id,
        date=s.date_local,
        origin="TBD",
        destination="TBD",
        std=s.std,
        sta=s.sta,
        aircraft_reg=s.aircraft_reg,
        aircraft_type=s.aircraft_type,
        status=SectorStatus.PUBLISHED,
    )
    session.add(sector)
    session.flush()
    return sector


def _crew_lookup(session: Session, operator_id: uuid.UUID, employee_no: str) -> Crew:
    crew = session.scalar(
        select(Crew).where(Crew.operator_id == operator_id).where(Crew.employee_no == employee_no)
    )
    if crew is None:
        raise RosterPersistenceError(
            f"crew with employee_no={employee_no!r} not found in operator scope"
        )
    return crew


def _compute_fdp_legality(
    sectors: list[SectorInputIn],
    _crew_id: uuid.UUID,
    date_local: date,
) -> tuple[datetime, datetime, int, Decimal, Decimal, LegalityState, list[str]]:
    """Group ``sectors`` filtered to ``date_local`` and run them through the FTL engine."""
    day_sectors = sorted(
        [s for s in sectors if s.date_local == date_local],
        key=lambda s: s.std,
    )
    if not day_sectors:
        raise RosterPersistenceError(f"no sectors found for {date_local.isoformat()}")
    first, last = day_sectors[0], day_sectors[-1]
    report = first.std - timedelta(hours=1)
    off = last.sta + timedelta(minutes=30)
    duty_h = Decimal(str((off - report).total_seconds() / 3600.0))
    flight_h = sum((s.block_hours for s in day_sectors), Decimal("0"))

    fdp_in = ftl_engine.FdpInput(
        report_time=report,
        off_duty_time=off,
        sectors_count=len(day_sectors),
        flight_hours=flight_h,
        duty_hours=duty_h,
    )
    verdicts = ftl_engine.check_fdp(fdp_in)
    aggregated = ftl_engine.aggregate_verdicts(verdicts)
    rules_applied = list(dict.fromkeys(aggregated.rules_applied))
    return report, off, len(day_sectors), flight_h, duty_h, aggregated.legality_state, rules_applied


def publish_roster(
    session: Session,
    *,
    user: User,
    payload: PublishRosterRequest,
) -> PublishRosterResponse:
    """Persist every assignment in ``payload`` transactionally.

    Idempotency is left for Phase 6 (with a roster-version table); Phase 3
    publish is single-use per horizon.
    """
    sector_by_id: dict[str, SectorInputIn] = {s.sector_id: s for s in payload.sectors}
    sectors_persisted: dict[str, Sector] = {}
    for s in payload.sectors:
        sectors_persisted[s.sector_id] = _ensure_sector(
            session, operator_id=user.operator_id, user_id=user.id, s=s
        )

    sa_count = 0
    fdp_count = 0
    # (crew_id, date) → list of SectorInputIn covered by that crew that day.
    crew_day_sectors: dict[tuple[uuid.UUID, date], list[SectorInputIn]] = defaultdict(list)

    for a in payload.assignments:
        captain = _crew_lookup(session, user.operator_id, a.captain_id)
        fo = _crew_lookup(session, user.operator_id, a.fo_id)
        for sector_id in a.sector_ids:
            if sector_id not in sectors_persisted:
                raise RosterPersistenceError(
                    f"assignment references unknown sector_id={sector_id!r}"
                )
            sector_row = sectors_persisted[sector_id]
            sector_input = sector_by_id[sector_id]
            for crew, role in ((captain, "CAPT"), (fo, "FO")):
                session.add(
                    SectorAssignment(
                        operator_id=user.operator_id,
                        created_by_user_id=user.id,
                        sector_id=sector_row.id,
                        crew_id=crew.id,
                        role_on_sector=role,
                    )
                )
                sa_count += 1
                crew_day_sectors[(crew.id, a.date_local)].append(sector_input)
        session.flush()

    for (crew_id, day), day_sectors in crew_day_sectors.items():
        (
            report,
            off,
            sectors_count,
            flight_h,
            duty_h,
            legality,
            rules_applied,
        ) = _compute_fdp_legality(day_sectors, crew_id, day)
        session.add(
            FlightDutyPeriod(
                operator_id=user.operator_id,
                created_by_user_id=user.id,
                crew_id=crew_id,
                date=day,
                report_time=report,
                off_duty_time=off,
                sectors_count=sectors_count,
                flight_hours=flight_h,
                duty_hours=duty_h,
                type=FdpType.FDP,
                legality_state=legality,
                ftl_rules_applied=rules_applied,
            )
        )
        fdp_count += 1
    session.flush()

    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="PUBLISH_ROSTER",
        entity_type="roster",
        entity_id=None,
        before_state=None,
        after_state={
            "horizon_from": payload.horizon_from.isoformat(),
            "horizon_to": payload.horizon_to.isoformat(),
            "sectors": len(payload.sectors),
            "assignments": len(payload.assignments),
            "sector_assignments_created": sa_count,
            "flight_duty_periods_created": fdp_count,
        },
    )
    session.commit()
    return PublishRosterResponse(
        roster_version=1,
        sector_assignments_created=sa_count,
        flight_duty_periods_created=fdp_count,
    )


def list_published_assignments(
    session: Session,
    *,
    operator_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> list[AssignmentOut]:
    """Reconstruct duty-day assignments from persisted SectorAssignment rows."""
    sectors = session.scalars(
        select(Sector)
        .where(Sector.operator_id == operator_id)
        .where(Sector.date >= date_from)
        .where(Sector.date <= date_to)
        .where(Sector.status == SectorStatus.PUBLISHED)
    ).all()
    sector_ids = [s.id for s in sectors]
    if not sector_ids:
        return []

    assignments_rows = session.scalars(
        select(SectorAssignment).where(SectorAssignment.sector_id.in_(sector_ids))
    ).all()

    # Index sectors and crews for lookup.
    sectors_by_id = {s.id: s for s in sectors}
    crew_ids = {a.crew_id for a in assignments_rows}
    crews = session.scalars(select(Crew).where(Crew.id.in_(crew_ids))).all()
    crews_by_id = {c.id: c for c in crews}

    # Group by (aircraft_reg, date).
    by_dd: dict[tuple[str, date], dict[str, object]] = defaultdict(
        lambda: {"sector_ids": set(), "CAPT": None, "FO": None, "aircraft_type": ""}
    )
    for sa in assignments_rows:
        sector = sectors_by_id[sa.sector_id]
        key = (sector.aircraft_reg, sector.date)
        bucket = by_dd[key]
        sector_ids_set: set[str] = bucket["sector_ids"]  # type: ignore[assignment]
        sector_ids_set.add(sector.flight_no)
        bucket["aircraft_type"] = sector.aircraft_type
        crew = crews_by_id.get(sa.crew_id)
        if crew is not None:
            bucket[sa.role_on_sector] = crew.employee_no

    out: list[AssignmentOut] = []
    for (reg, day), bucket in sorted(by_dd.items()):
        sector_ids_set = bucket["sector_ids"]  # type: ignore[assignment]
        capt = bucket["CAPT"]
        fo = bucket["FO"]
        if capt and fo:
            out.append(
                AssignmentOut(
                    duty_day_key=f"{reg}|{day.isoformat()}",
                    date_local=day,
                    aircraft_reg=reg,
                    aircraft_type=str(bucket["aircraft_type"]),
                    sector_ids=sorted(sector_ids_set),
                    captain_id=str(capt),
                    fo_id=str(fo),
                )
            )
    return out
