"""Factories for optimiser test inputs.

Realistic but minimal: an operator with a couple of crew and a couple of
sectors per day, all in Africa/Nairobi time.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from app.models.crew import CrewRole
from app.services.optimiser import (
    CrewProfile,
    LeaveRequestInput,
    OptimiserInput,
    SectorInput,
)

BASE_TZ = "Africa/Nairobi"


def std_at(d: date, hour_local: int = 6) -> datetime:
    """STD as UTC for a given local hour (Nairobi is UTC+3)."""
    return datetime.combine(d, time(hour_local - 3, 0), tzinfo=UTC)


def make_sectors_for_day(
    *, day: date, aircraft_reg: str, aircraft_type: str, count: int = 2
) -> list[SectorInput]:
    """Build ``count`` consecutive sectors of 2h block + 1h turnaround."""
    sectors: list[SectorInput] = []
    current = std_at(day, hour_local=6)
    for i in range(count):
        std = current
        sta = std + timedelta(hours=2)
        sectors.append(
            SectorInput(
                sector_id=f"{aircraft_reg}-{day.isoformat()}-{i}",
                date_local=day,
                std=std,
                sta=sta,
                aircraft_reg=aircraft_reg,
                aircraft_type=aircraft_type,
                block_hours=Decimal("2.0"),
            )
        )
        current = sta + timedelta(hours=1)
    return sectors


def make_crew(
    *,
    crew_id: str,
    role: CrewRole,
    type_ratings: tuple[str, ...] = ("DH8D",),
    current: bool = True,
    sunday_protected: bool = False,
) -> CrewProfile:
    return CrewProfile(
        crew_id=crew_id,
        role=role,
        type_ratings=type_ratings,
        current=current,
        base_tz=BASE_TZ,
        faith_flags={"sunday_protected": sunday_protected},
    )


def small_scenario(
    *, horizon_days: int = 3, aircraft: int = 1, sectors_per_day: int = 2
) -> OptimiserInput:
    """A trivially-feasible scenario: 2 captains, 2 FOs, 1 aircraft."""
    horizon_from = date(2026, 6, 15)
    horizon_to = horizon_from + timedelta(days=horizon_days - 1)
    crew = (
        make_crew(crew_id="CAP-1", role=CrewRole.CAPT),
        make_crew(crew_id="CAP-2", role=CrewRole.CAPT),
        make_crew(crew_id="FO-1", role=CrewRole.FO),
        make_crew(crew_id="FO-2", role=CrewRole.FO),
    )
    sectors: list[SectorInput] = []
    for i in range(horizon_days):
        d = horizon_from + timedelta(days=i)
        for a in range(aircraft):
            reg = f"5Y-AAA{a + 1}"
            sectors.extend(
                make_sectors_for_day(
                    day=d,
                    aircraft_reg=reg,
                    aircraft_type="DH8D",
                    count=sectors_per_day,
                )
            )
    return OptimiserInput(
        horizon_from=horizon_from,
        horizon_to=horizon_to,
        crew=crew,
        sectors=tuple(sectors),
        base_tz=BASE_TZ,
        timeout_s=30.0,
    )


def medium_scenario() -> OptimiserInput:
    """5 aircraft × 7 days × 25 crew — a meaningful but tractable test."""
    horizon_from = date(2026, 6, 15)
    horizon_to = horizon_from + timedelta(days=6)
    crew_list: list[CrewProfile] = []
    for i in range(12):
        crew_list.append(make_crew(crew_id=f"CAP-{i + 1:02d}", role=CrewRole.CAPT))
    for i in range(13):
        crew_list.append(make_crew(crew_id=f"FO-{i + 1:02d}", role=CrewRole.FO))
    sectors: list[SectorInput] = []
    for d_off in range(7):
        d = horizon_from + timedelta(days=d_off)
        for a in range(5):
            reg = f"5Y-MED{a + 1}"
            sectors.extend(
                make_sectors_for_day(
                    day=d,
                    aircraft_reg=reg,
                    aircraft_type="DH8D",
                    count=2,
                )
            )
    return OptimiserInput(
        horizon_from=horizon_from,
        horizon_to=horizon_to,
        crew=tuple(crew_list),
        sectors=tuple(sectors),
        base_tz=BASE_TZ,
        timeout_s=60.0,
    )


def with_leave(input_: OptimiserInput, *, crew_id: str, day_offset: int) -> OptimiserInput:
    """Return a copy of ``input_`` with an approved leave for ``crew_id`` on day n."""
    leave = LeaveRequestInput(
        crew_id=crew_id,
        date_from=input_.horizon_from + timedelta(days=day_offset),
        date_to=input_.horizon_from + timedelta(days=day_offset),
        status="APPROVED",
    )
    return OptimiserInput(
        horizon_from=input_.horizon_from,
        horizon_to=input_.horizon_to,
        crew=input_.crew,
        sectors=input_.sectors,
        leave_requests=(*input_.leave_requests, leave),
        base_tz=input_.base_tz,
        weights=dict(input_.weights),
        timeout_s=input_.timeout_s,
    )
