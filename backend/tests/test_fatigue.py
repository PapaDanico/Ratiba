"""Fatigue scoring model — unit tests (no DB)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.services import fatigue

EAT = ZoneInfo("Africa/Nairobi")


def test_daytime_short_duty_is_low() -> None:
    s = fatigue.score_fdp(
        report_time=datetime(2026, 6, 1, 8, 0, tzinfo=EAT),
        off_duty_time=datetime(2026, 6, 1, 12, 0, tzinfo=EAT),
        duty_hours=4.0,
        sectors_count=1,
    )
    assert s.band == "LOW"


def test_wocl_long_multisector_is_high() -> None:
    s = fatigue.score_fdp(
        report_time=datetime(2026, 6, 1, 2, 0, tzinfo=EAT),  # window of circadian low
        off_duty_time=datetime(2026, 6, 1, 11, 0, tzinfo=EAT),
        duty_hours=10.5,
        sectors_count=4,
        prior_rest_h=9.0,
        consecutive_days=6,
    )
    assert s.band == "HIGH"
    assert any("circadian" in d for d in s.drivers)


def test_summarise_counts_night_streak_and_peak() -> None:
    duties = [
        fatigue.DutyFacts(
            date=date(2026, 6, 1) + timedelta(days=i),
            report_time=datetime(2026, 6, 1, 2, 0, tzinfo=EAT) + timedelta(days=i),
            off_duty_time=datetime(2026, 6, 1, 12, 30, tzinfo=EAT) + timedelta(days=i),
            duty_hours=10.5,
            sectors_count=4,
        )
        for i in range(6)
    ]
    summary = fatigue.summarise_duties(duties)
    assert summary.fdp_count == 6
    assert summary.night_fdp_count == 6
    assert summary.night_pct == 100.0
    assert summary.max_consecutive_days == 6
    assert summary.peak_score >= 60  # WOCL + long + 4 sectors + 6-day streak → HIGH
    assert summary.high_count >= 1


def test_summarise_per_duty_tz_overrides_base() -> None:
    # 02:00 EAT report is the window of circadian low at home (Nairobi), but the
    # same instant is 13:00 in Honolulu — so a duty tagged to that posting tz
    # must NOT be counted as a night duty.
    duty = fatigue.DutyFacts(
        date=date(2026, 6, 1),
        report_time=datetime(2026, 6, 1, 2, 0, tzinfo=EAT),
        off_duty_time=datetime(2026, 6, 1, 12, 30, tzinfo=EAT),
        duty_hours=10.5,
        sectors_count=4,
        tz="Pacific/Honolulu",
    )
    assert fatigue.summarise_duties([duty]).night_fdp_count == 0
    # Without the per-duty tz it falls back to base (Nairobi) and is a night duty.
    home = fatigue.DutyFacts(
        date=duty.date,
        report_time=duty.report_time,
        off_duty_time=duty.off_duty_time,
        duty_hours=duty.duty_hours,
        sectors_count=duty.sectors_count,
    )
    assert fatigue.summarise_duties([home]).night_fdp_count == 1


def test_summarise_empty() -> None:
    summary = fatigue.summarise_duties([])
    assert summary.fdp_count == 0
    assert summary.peak_score == 0
