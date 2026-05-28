"""Test factories for FTL engine inputs.

Helpers that build :class:`FdpInput` instances with sensible defaults so
that each test only has to specify what the test is about.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.services.ftl_engine import (
    CrewClassification,
    FdpHistoryEntry,
    FdpInput,
    FdpType,
)


def at(hour: int, minute: int = 0, day: int = 15, month: int = 6, year: int = 2026) -> datetime:
    """Build an aware UTC datetime."""
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def fdp(
    *,
    report_local_hour: int = 9,
    duty_h: float = 10.0,
    flight_h: float = 8.0,
    sectors: int = 2,
    base_tz: str = "Africa/Nairobi",
    augmented: bool = False,
    pilots: int = 2,
    rest_class: int = 0,
    discretion_h: float = 0.0,
    split_break_h: float = 0.0,
    tz_crossed: int = 0,
    at_home: bool = True,
    standby_type: str = "NONE",
    standby_h: float = 0.0,
    prior: FdpHistoryEntry | None = None,
    history: tuple[FdpHistoryEntry, ...] = (),
    discretion_uses_90d: int = 0,
    fdp_type: FdpType = FdpType.FDP,
) -> FdpInput:
    """Build an FdpInput. ``report_local_hour`` is in Africa/Nairobi local."""
    # Nairobi is UTC+3 year-round.
    report_utc = at(report_local_hour - 3 if base_tz == "Africa/Nairobi" else report_local_hour)
    off_utc = report_utc + timedelta(hours=duty_h)
    return FdpInput(
        report_time=report_utc,
        off_duty_time=off_utc,
        sectors_count=sectors,
        flight_hours=Decimal(str(flight_h)),
        duty_hours=Decimal(str(duty_h)),
        base_tz=base_tz,
        fdp_type=fdp_type,
        crew_classification=CrewClassification(
            augmented=augmented,
            pilots_on_flight_deck=pilots,
            rest_facility_class=rest_class,
        ),
        discretion_extension_h=Decimal(str(discretion_h)),
        split_duty_break_h=Decimal(str(split_break_h)),
        timezones_crossed=tz_crossed,
        at_home_base=at_home,
        prior_fdp=prior,
        history=history,
        discretion_uses_last_90d=discretion_uses_90d,
        standby_hours_before_call=Decimal(str(standby_h)),
        standby_type=standby_type,
    )


def history_entry(
    *,
    days_ago: int,
    duty_h: float = 8.0,
    flight_h: float = 6.0,
    sectors: int = 2,
    at_home: bool = True,
    tz_crossed: int = 0,
    reference: datetime | None = None,
) -> FdpHistoryEntry:
    ref = reference or at(9)
    report_at = ref - timedelta(days=days_ago)
    return FdpHistoryEntry(
        date_local=report_at.date().isoformat(),
        report_time=report_at,
        off_duty_time=report_at + timedelta(hours=duty_h),
        duty_hours=Decimal(str(duty_h)),
        flight_hours=Decimal(str(flight_h)),
        sectors_count=sectors,
        fdp_type=FdpType.FDP,
        at_home_base=at_home,
        timezones_crossed=tz_crossed,
    )


def prior_fdp_just_off(
    *,
    off_duty: datetime,
    duty_h: float = 8.0,
    flight_h: float = 6.0,
    sectors: int = 2,
    at_home: bool = True,
    tz_crossed: int = 0,
) -> FdpHistoryEntry:
    """Prior FDP whose ``off_duty_time`` is the seed; report_time is duty_h earlier."""
    report = off_duty - timedelta(hours=duty_h)
    return FdpHistoryEntry(
        date_local=report.date().isoformat(),
        report_time=report,
        off_duty_time=off_duty,
        duty_hours=Decimal(str(duty_h)),
        flight_hours=Decimal(str(flight_h)),
        sectors_count=sectors,
        fdp_type=FdpType.FDP,
        at_home_base=at_home,
        timezones_crossed=tz_crossed,
    )
