"""Automatic roster builder — one call, no hand-assembled payload.

The optimiser (:mod:`app.services.optimiser`) is database-free by design.
This service is the bridge: it reads the operator's crew, type ratings,
currency, scheduled sectors, and leave straight from the database, builds
the :class:`OptimiserInput`, runs the solver, and hands back both the
result and the sector list needed to publish it — so the Crewing Officer
gets a legal draft roster from a single button press.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Crew, CrewCurrency, CrewTypeRating, Sector
from app.models.crew import FLIGHT_DECK_ROLES
from app.models.leave import LeaveRequest, LeaveStatus
from app.schemas.roster import SectorInputIn
from app.services import ftl_limits, optimiser

# Recurrent checks whose expiry grounds a pilot. Other currencies
# (route familiarisation, first aid, etc.) don't block scheduling here.
_GROUNDING_CURRENCIES = {"OPC", "LPC", "LINE_CHECK"}


def _crew_profiles(
    session: Session,
    *,
    operator_id: uuid.UUID,
    horizon_from: date,
    horizon_to: date,
) -> list[optimiser.CrewProfile]:
    # Only flight-deck crew enter the pilot-pairing optimiser. Cabin and
    # engineering crew are tracked/qualified elsewhere; full crew-complement
    # rostering is a later phase.
    crew = session.scalars(
        select(Crew)
        .where(Crew.operator_id == operator_id)
        .where(Crew.active.is_(True))
        .where(Crew.role.in_(FLIGHT_DECK_ROLES))
    ).all()
    crew_by_id = {c.id: c for c in crew}

    # Type ratings valid at any point within the horizon.
    ratings = session.scalars(
        select(CrewTypeRating)
        .where(CrewTypeRating.operator_id == operator_id)
        .where(CrewTypeRating.valid_from <= horizon_to)
        .where(CrewTypeRating.valid_until >= horizon_from)
    ).all()
    ratings_by_crew: dict[uuid.UUID, set[str]] = {}
    for r in ratings:
        if r.crew_id in crew_by_id:
            ratings_by_crew.setdefault(r.crew_id, set()).add(r.aircraft_type)

    # A grounding-check currency expiring before the horizon starts marks
    # the crew member as not current.
    currencies = session.scalars(
        select(CrewCurrency).where(CrewCurrency.operator_id == operator_id)
    ).all()
    grounded: set[uuid.UUID] = set()
    for cur in currencies:
        if cur.currency_type.value in _GROUNDING_CURRENCIES and cur.expires_date < horizon_from:
            grounded.add(cur.crew_id)

    profiles: list[optimiser.CrewProfile] = []
    for c in crew:
        profiles.append(
            optimiser.CrewProfile(
                crew_id=c.employee_no,
                role=c.role,
                type_ratings=tuple(sorted(ratings_by_crew.get(c.id, set()))),
                current=c.id not in grounded,
                faith_flags={k: bool(v) for k, v in (c.faith_observance_flags or {}).items()},
            )
        )
    return profiles


def _sector_inputs(
    session: Session,
    *,
    operator_id: uuid.UUID,
    horizon_from: date,
    horizon_to: date,
) -> tuple[list[optimiser.SectorInput], list[SectorInputIn]]:
    rows = session.scalars(
        select(Sector)
        .where(Sector.operator_id == operator_id)
        .where(Sector.date >= horizon_from)
        .where(Sector.date <= horizon_to)
        .order_by(Sector.date, Sector.std)
    ).all()
    opt_sectors: list[optimiser.SectorInput] = []
    publish_sectors: list[SectorInputIn] = []
    for s in rows:
        block = Decimal(str(round((s.sta - s.std).total_seconds() / 3600.0, 2)))
        opt_sectors.append(
            optimiser.SectorInput(
                sector_id=s.flight_no,
                date_local=s.date,
                std=s.std,
                sta=s.sta,
                aircraft_reg=s.aircraft_reg,
                aircraft_type=s.aircraft_type,
                block_hours=block,
            )
        )
        publish_sectors.append(
            SectorInputIn(
                sector_id=s.flight_no,
                date_local=s.date,
                std=s.std,
                sta=s.sta,
                aircraft_reg=s.aircraft_reg,
                aircraft_type=s.aircraft_type,
                block_hours=block,
            )
        )
    return opt_sectors, publish_sectors


def _leave_inputs(
    session: Session,
    *,
    operator_id: uuid.UUID,
    horizon_from: date,
    horizon_to: date,
) -> list[optimiser.LeaveRequestInput]:
    crew = session.scalars(select(Crew).where(Crew.operator_id == operator_id)).all()
    emp_by_id = {c.id: c.employee_no for c in crew}
    rows = session.scalars(
        select(LeaveRequest)
        .where(LeaveRequest.operator_id == operator_id)
        .where(LeaveRequest.status.in_([LeaveStatus.APPROVED, LeaveStatus.PENDING]))
        .where(LeaveRequest.date_to >= horizon_from)
        .where(LeaveRequest.date_from <= horizon_to)
    ).all()
    out: list[optimiser.LeaveRequestInput] = []
    for r in rows:
        emp = emp_by_id.get(r.crew_id)
        if emp is None:
            continue
        out.append(
            optimiser.LeaveRequestInput(
                crew_id=emp,
                date_from=r.date_from,
                date_to=r.date_to,
                status=r.status.value,
            )
        )
    return out


def build_auto_roster(
    session: Session,
    *,
    operator_id: uuid.UUID,
    horizon_from: date,
    horizon_to: date,
    base_tz: str = "Africa/Nairobi",
    timeout_s: float = 30.0,
) -> tuple[optimiser.OptimiserResult, list[SectorInputIn]]:
    """Assemble inputs from the DB, solve, and return (result, sectors)."""
    crew = _crew_profiles(
        session, operator_id=operator_id, horizon_from=horizon_from, horizon_to=horizon_to
    )
    opt_sectors, publish_sectors = _sector_inputs(
        session, operator_id=operator_id, horizon_from=horizon_from, horizon_to=horizon_to
    )
    leave = _leave_inputs(
        session, operator_id=operator_id, horizon_from=horizon_from, horizon_to=horizon_to
    )

    if not crew:
        return (
            optimiser.OptimiserResult(
                status="INFEASIBLE",
                assignments=(),
                objective_value=None,
                unassigned_duty_days=(),
                diagnostics={"reason": "no active crew on record"},
                elapsed_s=0.0,
            ),
            publish_sectors,
        )
    if not opt_sectors:
        return (
            optimiser.OptimiserResult(
                status="INFEASIBLE",
                assignments=(),
                objective_value=None,
                unassigned_duty_days=(),
                diagnostics={"reason": "no scheduled sectors in horizon"},
                elapsed_s=0.0,
            ),
            publish_sectors,
        )

    # Judge the draft by the operator's resolved scheme so it matches publish.
    limits = ftl_limits.resolve_limits(operator_id, session)
    result = optimiser.solve(
        optimiser.OptimiserInput(
            horizon_from=horizon_from,
            horizon_to=horizon_to,
            crew=tuple(crew),
            sectors=tuple(opt_sectors),
            leave_requests=tuple(leave),
            base_tz=base_tz,
            timeout_s=timeout_s,
        ),
        limits=limits,
    )
    return result, publish_sectors
