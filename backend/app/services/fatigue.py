"""Fatigue scoring — an FRMS-aligned screening indicator.

Aligned to the *principles* of ICAO Doc 9966 (Fatigue Risk Management): each
duty is scored for likely fatigue from circadian timing (window of circadian
low), duty length, sector count, short prior rest, consecutive-duty streaks,
and recent cumulative duty.

This is a transparent, rule-based **screen** — NOT a validated biomathematical
model (e.g. SAFTE-FAST) — and is **advisory only**. The hard FTL limits in
``ftl_engine`` remain the legal gate; this surfaces *risk* the limits don't.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

# Window of circadian low (local clock) — the trough of alertness.
_WOCL_START_H = 2
_WOCL_END_H = 6

_ELEVATED = 30
_HIGH = 60


@dataclass(frozen=True)
class FatigueScore:
    score: int  # 0..100 (higher = more fatigue risk)
    band: str  # LOW | ELEVATED | HIGH
    drivers: list[str] = field(default_factory=list)


def _band(score: int) -> str:
    if score >= _HIGH:
        return "HIGH"
    if score >= _ELEVATED:
        return "ELEVATED"
    return "LOW"


def _overlaps_wocl(report_local: datetime, off_local: datetime) -> bool:
    """True if the duty [report, off] (local clock) intersects the daily window
    of circadian low — catches overnight duties that *span* it even when neither
    endpoint falls inside (e.g. a 01:00 report to 06:30 off-duty)."""
    tz = report_local.tzinfo
    day = report_local.date() - timedelta(days=1)
    last = off_local.date()
    while day <= last:
        w_start = datetime.combine(day, time(_WOCL_START_H), tzinfo=tz)
        w_end = datetime.combine(day, time(_WOCL_END_H), tzinfo=tz)
        if report_local < w_end and off_local > w_start:
            return True
        day += timedelta(days=1)
    return False


def score_fdp(
    *,
    report_time: datetime,
    off_duty_time: datetime,
    duty_hours: float,
    sectors_count: int,
    base_tz: str = "Africa/Nairobi",
    prior_rest_h: float | None = None,
    consecutive_days: int | None = None,
    cumulative_duty_28d_h: float | None = None,
) -> FatigueScore:
    """Score a single FDP for fatigue risk. Optional context (prior rest,
    consecutive days, cumulative duty) sharpens the score when available."""
    tz = ZoneInfo(base_tz)
    local_report = report_time.astimezone(tz)
    local_off = off_duty_time.astimezone(tz)
    score = 0
    drivers: list[str] = []

    # Circadian: operating through the window of circadian low.
    if _overlaps_wocl(local_report, local_off):
        score += 30
        drivers.append("operates through the window of circadian low (02:00–06:00)")
    elif local_report.hour >= 22 or local_report.hour < _WOCL_START_H:
        score += 15
        drivers.append("late-night report")

    if duty_hours > 12:
        score += 25
        drivers.append("very long duty (>12h)")
    elif duty_hours > 10:
        score += 15
        drivers.append("long duty (>10h)")
    elif duty_hours > 8:
        score += 5

    if sectors_count >= 4:
        score += 15
        drivers.append("high sector count (4+)")
    elif sectors_count >= 3:
        score += 8

    if prior_rest_h is not None:
        if prior_rest_h < 10:
            score += 20
            drivers.append("short prior rest (<10h)")
        elif prior_rest_h < 12:
            score += 10

    if consecutive_days is not None:
        if consecutive_days >= 6:
            score += 20
            drivers.append("6+ consecutive duty days")
        elif consecutive_days >= 4:
            score += 10

    if cumulative_duty_28d_h is not None:
        if cumulative_duty_28d_h > 170:
            score += 15
            drivers.append("high 28-day cumulative duty")
        elif cumulative_duty_28d_h > 150:
            score += 8

    score = min(score, 100)
    return FatigueScore(score=score, band=_band(score), drivers=drivers)


@dataclass(frozen=True)
class DutyFacts:
    """Minimal facts about one duty day needed for the fatigue summary."""

    date: date
    report_time: datetime
    off_duty_time: datetime
    duty_hours: float
    sectors_count: int


@dataclass(frozen=True)
class CrewFatigueSummary:
    fdp_count: int
    night_fdp_count: int
    night_pct: float  # 0..100
    max_consecutive_days: int
    elevated_count: int
    high_count: int
    peak_score: int


def _is_night(d: DutyFacts, tz: ZoneInfo) -> bool:
    return _overlaps_wocl(d.report_time.astimezone(tz), d.off_duty_time.astimezone(tz))


def summarise_duties(
    duties: list[DutyFacts], *, base_tz: str = "Africa/Nairobi"
) -> CrewFatigueSummary:
    """Aggregate a crew member's duties into fatigue indicators, threading prior
    rest, consecutive-day streaks and 28-day cumulative duty into each score."""
    tz = ZoneInfo(base_tz)
    ordered = sorted(duties, key=lambda d: d.report_time)
    if not ordered:
        return CrewFatigueSummary(0, 0, 0.0, 0, 0, 0, 0)

    night = 0
    elevated = 0
    high = 0
    peak = 0
    max_streak = 0
    streak = 0
    prev: DutyFacts | None = None

    for i, d in enumerate(ordered):
        # Consecutive-day streak (calendar days).
        if prev is not None and (d.date - prev.date).days == 1:
            streak += 1
        else:
            streak = 1
        max_streak = max(max_streak, streak)

        prior_rest_h: float | None = None
        if prev is not None:
            prior_rest_h = (d.report_time - prev.off_duty_time).total_seconds() / 3600.0

        window_start = d.report_time - timedelta(days=28)
        cumulative_28d = d.duty_hours + sum(
            e.duty_hours for e in ordered[:i] if window_start <= e.report_time < d.report_time
        )

        result = score_fdp(
            report_time=d.report_time,
            off_duty_time=d.off_duty_time,
            duty_hours=d.duty_hours,
            sectors_count=d.sectors_count,
            base_tz=base_tz,
            prior_rest_h=prior_rest_h,
            consecutive_days=streak,
            cumulative_duty_28d_h=cumulative_28d,
        )
        peak = max(peak, result.score)
        if result.band == "HIGH":
            high += 1
        elif result.band == "ELEVATED":
            elevated += 1
        if _is_night(d, tz):
            night += 1
        prev = d

    n = len(ordered)
    return CrewFatigueSummary(
        fdp_count=n,
        night_fdp_count=night,
        night_pct=round(100.0 * night / n, 1),
        max_consecutive_days=max_streak,
        elevated_count=elevated,
        high_count=high,
        peak_score=peak,
    )
