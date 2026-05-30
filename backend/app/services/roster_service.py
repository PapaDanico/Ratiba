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
from app.services import audit_log, ftl_engine, ftl_limits
from app.services import postings as postings_service


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


def _fdp_to_history(fdp: FlightDutyPeriod) -> ftl_engine.FdpHistoryEntry:
    """Convert a persisted FDP into a history entry for cumulative/rest rules."""
    return ftl_engine.FdpHistoryEntry(
        date_local=fdp.date.isoformat(),
        report_time=fdp.report_time,
        off_duty_time=fdp.off_duty_time,
        duty_hours=Decimal(str(fdp.duty_hours)),
        flight_hours=Decimal(str(fdp.flight_hours)),
        sectors_count=fdp.sectors_count,
        fdp_type=fdp.type,
        at_home_base=True,
    )


def _compute_fdp_legality(
    sectors: list[SectorInputIn],
    crew_id: uuid.UUID,
    date_local: date,
    *,
    session: Session,
    operator_id: uuid.UUID,
    history: tuple[ftl_engine.FdpHistoryEntry, ...] = (),
) -> tuple[datetime, datetime, int, Decimal, Decimal, LegalityState, list[str]]:
    """Group ``sectors`` filtered to ``date_local`` and run them through the FTL engine.

    Uses the operator's *resolved* limits (their latest ACCEPTED constraint
    set merged over the baseline) so a published roster's legality reflects
    the operator's own Authority-approved Flight & Duty Time scheme, not just
    the generic baseline.

    ``history`` carries the crew member's prior FDPs (earlier roster days plus
    persisted/imported duties) so the cumulative-hours and rest-minimum rules
    fire — without it each duty day is judged in isolation. If the crew member
    is on a posting covering ``date_local`` the duty is away-from-base, so the
    away rest floor (not the home floor) applies and the posting timezone drives
    band-based rules.
    """
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

    # The immediately preceding duty (latest report strictly before this one)
    # drives the rest-minimum rule.
    earlier = [h for h in history if h.report_time < report]
    prior_fdp = max(earlier, key=lambda h: h.report_time) if earlier else None

    # On a posting → away from base: away rest floor + posting timezone.
    posting = postings_service.active_posting_for(
        session, operator_id=operator_id, crew_id=crew_id, on_date=date_local
    )

    fdp_in = ftl_engine.FdpInput(
        report_time=report,
        off_duty_time=off,
        sectors_count=len(day_sectors),
        flight_hours=flight_h,
        duty_hours=duty_h,
        prior_fdp=prior_fdp,
        history=history,
        at_home_base=posting is None,
        base_tz=posting.base_tz if posting is not None else "Africa/Nairobi",
    )
    verdicts = ftl_limits.check_fdp_for_operator(fdp_in, operator_id, session)
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

    Idempotent: re-publishing onto the same horizon replaces existing
    ``SectorAssignment`` + ``FlightDutyPeriod`` rows for the touched
    sectors/dates instead of duplicating them. Crewing-officer-driven
    surgical edits go through :func:`amend_roster` (with a reason) so
    the audit trail distinguishes a full re-publish from a single swap.
    """
    sector_by_id: dict[str, SectorInputIn] = {s.sector_id: s for s in payload.sectors}
    sectors_persisted: dict[str, Sector] = {}
    for s in payload.sectors:
        sectors_persisted[s.sector_id] = _ensure_sector(
            session, operator_id=user.operator_id, user_id=user.id, s=s
        )

    # Drop any prior SectorAssignment / FlightDutyPeriod rows that this
    # republish supersedes so re-runs are idempotent. We delete-and-rewrite
    # rather than upsert because (sector_id, role) is the natural key but
    # the row's identity (UUID) is fresh on every publish.
    touched_sector_ids = [sectors_persisted[sid].id for sid in sectors_persisted]
    touched_dates = {a.date_local for a in payload.assignments}
    if touched_sector_ids:
        existing_assignments = session.scalars(
            select(SectorAssignment).where(SectorAssignment.sector_id.in_(touched_sector_ids))
        ).all()
        for sa in existing_assignments:
            session.delete(sa)
    crew_in_payload = {a.captain_id for a in payload.assignments} | {
        a.fo_id for a in payload.assignments
    }
    if crew_in_payload and touched_dates:
        crew_ids = [
            c.id
            for c in session.scalars(
                select(Crew)
                .where(Crew.operator_id == user.operator_id)
                .where(Crew.employee_no.in_(crew_in_payload))
            ).all()
        ]
        if crew_ids:
            existing_fdps = session.scalars(
                select(FlightDutyPeriod)
                .where(FlightDutyPeriod.crew_id.in_(crew_ids))
                .where(FlightDutyPeriod.date.in_(touched_dates))
            ).all()
            for fdp in existing_fdps:
                session.delete(fdp)
    session.flush()

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

    # Seed each touched crew's history with persisted FDPs that this publish is
    # NOT replacing (historical imports + other-horizon publishes), so the
    # cumulative-hours and rest-minimum rules see real prior duty. The replaced
    # rows for touched (crew, date) pairs were already deleted + flushed above.
    touched_crew_ids = {cid for (cid, _d) in crew_day_sectors}
    history_by_crew: dict[uuid.UUID, list[ftl_engine.FdpHistoryEntry]] = defaultdict(list)
    if crew_day_sectors:
        window_start = min(d for (_c, d) in crew_day_sectors) - timedelta(days=365)
        prior_fdps = session.scalars(
            select(FlightDutyPeriod)
            .where(FlightDutyPeriod.crew_id.in_(touched_crew_ids))
            .where(FlightDutyPeriod.date >= window_start)
        ).all()
        for f in prior_fdps:
            history_by_crew[f.crew_id].append(_fdp_to_history(f))

    # Process each crew's duty days in chronological order, accumulating each
    # computed day into that crew's history for the days that follow.
    days_by_crew: dict[uuid.UUID, list[date]] = defaultdict(list)
    for crew_id, day in crew_day_sectors:
        days_by_crew[crew_id].append(day)

    for crew_id, days in days_by_crew.items():
        accumulated = history_by_crew[crew_id]
        for day in sorted(days):
            day_sectors = crew_day_sectors[(crew_id, day)]
            (
                report,
                off,
                sectors_count,
                flight_h,
                duty_h,
                legality,
                rules_applied,
            ) = _compute_fdp_legality(
                day_sectors,
                crew_id,
                day,
                session=session,
                operator_id=user.operator_id,
                history=tuple(accumulated),
            )
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
            accumulated.append(
                ftl_engine.FdpHistoryEntry(
                    date_local=day.isoformat(),
                    report_time=report,
                    off_duty_time=off,
                    duty_hours=duty_h,
                    flight_hours=flight_h,
                    sectors_count=sectors_count,
                    fdp_type=FdpType.FDP,
                    at_home_base=True,
                )
            )
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

    # Index FlightDutyPeriod rows so we can stamp legality on each duty day.
    fdps = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.operator_id == operator_id)
        .where(FlightDutyPeriod.crew_id.in_(crew_ids))
        .where(FlightDutyPeriod.date >= date_from)
        .where(FlightDutyPeriod.date <= date_to)
    ).all()
    fdp_legality: dict[tuple[uuid.UUID, date], LegalityState] = {
        (f.crew_id, f.date): f.legality_state for f in fdps
    }

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
            bucket.setdefault(f"{sa.role_on_sector}_id", crew.id)

    out: list[AssignmentOut] = []
    for (reg, day), bucket in sorted(by_dd.items()):
        sector_ids_set = bucket["sector_ids"]  # type: ignore[assignment]
        capt = bucket["CAPT"]
        fo = bucket["FO"]
        if capt and fo:
            # Worst-state-wins across the two crew members' FDPs for the day.
            crew_id_capt = bucket.get("CAPT_id")
            crew_id_fo = bucket.get("FO_id")
            states = [
                fdp_legality.get((cid, day))
                for cid in (crew_id_capt, crew_id_fo)
                if isinstance(cid, uuid.UUID)
            ]
            worst = _worst_state([s for s in states if s is not None])
            out.append(
                AssignmentOut(
                    duty_day_key=f"{reg}|{day.isoformat()}",
                    date_local=day,
                    aircraft_reg=reg,
                    aircraft_type=str(bucket["aircraft_type"]),
                    sector_ids=sorted(sector_ids_set),
                    captain_id=str(capt),
                    fo_id=str(fo),
                    legality_state=worst.value if worst is not None else None,
                )
            )
    return out


_STATE_PRECEDENCE = (
    LegalityState.LEGAL,
    LegalityState.AT_LIMIT,
    LegalityState.REQUIRES_FRMS_DEROGATION,
    LegalityState.ILLEGAL,
)


def _worst_state(states: list[LegalityState]) -> LegalityState | None:
    if not states:
        return None
    return max(states, key=_STATE_PRECEDENCE.index)


# -----------------------------------------------------------------------------
# Amendments — post-publication targeted edits
# -----------------------------------------------------------------------------


def _sector_to_input(s: Sector) -> SectorInputIn:
    return SectorInputIn(
        sector_id=s.flight_no,
        date_local=s.date,
        std=s.std,
        sta=s.sta,
        aircraft_reg=s.aircraft_reg,
        aircraft_type=s.aircraft_type,
        block_hours=Decimal(str((s.sta - s.std).total_seconds() / 3600.0)),
    )


def _recompute_crew_legality(
    session: Session,
    *,
    user: User,
    crew_ids: set[uuid.UUID],
    from_date: date,
) -> LegalityState:
    """Recompute + persist FTL legality for each crew's published duty days on or
    after ``from_date``, upserting their ``FlightDutyPeriod`` rows.

    The cumulative-hours, rest-minimum and weekly-rest rules are backward-looking,
    so changing one day's crew affects that day **and every later day** within the
    window. We therefore replay each affected crew forward from ``from_date``,
    seeding history from their FDPs in the prior 365 days and accumulating each
    recomputed day. Returns the worst legality on ``from_date`` (the amended day).
    """
    # Reconstruct each affected crew's duty days from the (current) published
    # sector assignments — the caller has already applied the swap.
    sa_rows = session.scalars(
        select(SectorAssignment).where(SectorAssignment.crew_id.in_(crew_ids))
    ).all()
    sector_ids = {sa.sector_id for sa in sa_rows}
    sectors = (
        session.scalars(
            select(Sector)
            .where(Sector.id.in_(sector_ids))
            .where(Sector.operator_id == user.operator_id)
            .where(Sector.status == SectorStatus.PUBLISHED)
            .where(Sector.date >= from_date)
        ).all()
        if sector_ids
        else []
    )
    sector_by_id = {s.id: s for s in sectors}
    crew_day_sectors: dict[tuple[uuid.UUID, date], list[SectorInputIn]] = defaultdict(list)
    for sa in sa_rows:
        sector = sector_by_id.get(sa.sector_id)
        if sector is not None:
            crew_day_sectors[(sa.crew_id, sector.date)].append(_sector_to_input(sector))

    # Seed history from each crew's persisted FDPs in the year before from_date.
    window_start = from_date - timedelta(days=365)
    history_by_crew: dict[uuid.UUID, list[ftl_engine.FdpHistoryEntry]] = defaultdict(list)
    prior_fdps = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.crew_id.in_(crew_ids))
        .where(FlightDutyPeriod.date >= window_start)
        .where(FlightDutyPeriod.date < from_date)
    ).all()
    for f in prior_fdps:
        history_by_crew[f.crew_id].append(_fdp_to_history(f))

    days_by_crew: dict[uuid.UUID, list[date]] = defaultdict(list)
    for crew_id, day in crew_day_sectors:
        days_by_crew[crew_id].append(day)

    worst_on_from_date: LegalityState = LegalityState.LEGAL
    for crew_id, days in days_by_crew.items():
        accumulated = history_by_crew[crew_id]
        for day in sorted(days):
            inputs = crew_day_sectors[(crew_id, day)]
            (report, off, sectors_count, flight_h, duty_h, legality, rules_applied) = (
                _compute_fdp_legality(
                    inputs,
                    crew_id,
                    day,
                    session=session,
                    operator_id=user.operator_id,
                    history=tuple(accumulated),
                )
            )
            existing = session.scalar(
                select(FlightDutyPeriod)
                .where(FlightDutyPeriod.crew_id == crew_id)
                .where(FlightDutyPeriod.date == day)
            )
            if existing is not None:
                existing.report_time = report
                existing.off_duty_time = off
                existing.sectors_count = sectors_count
                existing.flight_hours = float(flight_h)
                existing.duty_hours = float(duty_h)
                existing.legality_state = legality
                existing.ftl_rules_applied = rules_applied
            else:
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
            accumulated.append(
                ftl_engine.FdpHistoryEntry(
                    date_local=day.isoformat(),
                    report_time=report,
                    off_duty_time=off,
                    duty_hours=duty_h,
                    flight_hours=flight_h,
                    sectors_count=sectors_count,
                    fdp_type=FdpType.FDP,
                    at_home_base=True,
                )
            )
            if day == from_date and _STATE_PRECEDENCE.index(legality) > _STATE_PRECEDENCE.index(
                worst_on_from_date
            ):
                worst_on_from_date = legality
    session.flush()
    return worst_on_from_date


def amend_roster(
    session: Session,
    *,
    user: User,
    duty_day_key: str,
    new_captain_employee_no: str,
    new_fo_employee_no: str,
    reason: str,
) -> tuple[uuid.UUID, uuid.UUID, LegalityState]:
    """Swap (CAPT, FO) on a single published duty day.

    Returns (captain_id, fo_id, recomputed_legality). The before/after
    state is captured in an ``AMEND_ROSTER`` audit event so the audit
    pack can reconstruct the full change history.
    """
    try:
        aircraft_reg, day_iso = duty_day_key.split("|", 1)
        day = date.fromisoformat(day_iso)
    except ValueError as exc:
        raise RosterPersistenceError(f"malformed duty_day_key: {duty_day_key!r}") from exc

    sectors = session.scalars(
        select(Sector)
        .where(Sector.operator_id == user.operator_id)
        .where(Sector.aircraft_reg == aircraft_reg)
        .where(Sector.date == day)
        .where(Sector.status == SectorStatus.PUBLISHED)
    ).all()
    if not sectors:
        raise RosterPersistenceError(f"no published sectors found for {duty_day_key!r}")

    new_captain = _crew_lookup(session, user.operator_id, new_captain_employee_no)
    new_fo = _crew_lookup(session, user.operator_id, new_fo_employee_no)
    if new_captain.id == new_fo.id:
        raise RosterPersistenceError("captain and FO must be different crew")

    # Snapshot current assignments for the audit event.
    sector_ids = [s.id for s in sectors]
    existing = session.scalars(
        select(SectorAssignment).where(SectorAssignment.sector_id.in_(sector_ids))
    ).all()
    old_crew_ids = {sa.crew_id for sa in existing}
    before_state = {
        "assignments": [
            {
                "sector_id": str(sa.sector_id),
                "crew_id": str(sa.crew_id),
                "role_on_sector": sa.role_on_sector,
            }
            for sa in existing
        ]
    }
    for sa in existing:
        session.delete(sa)
    session.flush()

    # Recreate the assignment with the new pair.
    for sector in sectors:
        for crew, role in ((new_captain, "CAPT"), (new_fo, "FO")):
            session.add(
                SectorAssignment(
                    operator_id=user.operator_id,
                    created_by_user_id=user.id,
                    sector_id=sector.id,
                    crew_id=crew.id,
                    role_on_sector=role,
                )
            )

    # Delete the amended day's FDP rows for every crew whose involvement changed
    # (old + new); the cascade helper recreates them and recomputes legality for
    # this day *and every later day* of those crew (cumulative/rest/weekly rules
    # are backward-looking, so the change ripples forward).
    affected_crew = old_crew_ids | {new_captain.id, new_fo.id}
    old_fdps = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.crew_id.in_(affected_crew))
        .where(FlightDutyPeriod.date == day)
    ).all()
    for fdp in old_fdps:
        session.delete(fdp)
    session.flush()

    aggregated = _recompute_crew_legality(session, user=user, crew_ids=affected_crew, from_date=day)

    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="AMEND_ROSTER",
        entity_type="roster",
        entity_id=None,
        before_state=before_state,
        after_state={
            "duty_day_key": duty_day_key,
            "captain_employee_no": new_captain_employee_no,
            "fo_employee_no": new_fo_employee_no,
            "reason": reason,
            "recomputed_legality": aggregated.value,
        },
    )
    session.commit()
    return new_captain.id, new_fo.id, aggregated
