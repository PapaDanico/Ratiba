"""Weekly recovery-rest rule — KCAR-P8-WEEKLY-REST (CAA-AC-OPS033 §4.6.2).

The current FDP reports at 09:00 Nairobi (06:00 UTC). History entries are
placed relative to that report so the rolling 7-day window is exercised
precisely.
"""

from __future__ import annotations

from app.models.ftl import LegalityState
from app.services.ftl_engine import rule_weekly_rest
from tests.ftl._factories import at, fdp, history_entry

REF = at(6)  # current FDP report, UTC (= 09:00 Africa/Nairobi)


def test_not_applicable_without_enough_history() -> None:
    v = rule_weekly_rest(fdp(report_local_hour=9, duty_h=8.0))
    assert v.legality_state == LegalityState.LEGAL
    assert v.metadata["applicable"] is False


def test_dense_week_with_no_long_break_is_illegal() -> None:
    # A duty every day for 7 days, each 8 h → longest rest is ~16 h, far under
    # the 36 h weekly-recovery floor.
    hist = tuple(history_entry(days_ago=d, duty_h=8.0, reference=REF) for d in range(1, 8))
    v = rule_weekly_rest(fdp(report_local_hour=9, duty_h=8.0, history=hist))
    assert v.legality_state == LegalityState.ILLEGAL
    assert v.metadata["longest_rest_h"] < 36.0


def test_week_with_a_long_break_is_legal() -> None:
    # Duties only early in the window, then a multi-day break before today.
    hist = tuple(history_entry(days_ago=d, duty_h=8.0, reference=REF) for d in (7, 6, 5))
    v = rule_weekly_rest(fdp(report_local_hour=9, duty_h=8.0, history=hist))
    assert v.legality_state == LegalityState.LEGAL
    assert v.metadata["longest_rest_h"] >= 36.0


def test_longest_break_just_below_floor_requires_derogation() -> None:
    # Dense cover of the window, but the most recent rest is 35.5 h: a
    # days-ago-2 duty of 12.5 h ends 35.5 h before today's report.
    hist = (
        *(history_entry(days_ago=d, duty_h=8.0, reference=REF) for d in (7, 6, 5, 4, 3)),
        history_entry(days_ago=2, duty_h=12.5, reference=REF),
    )
    v = rule_weekly_rest(fdp(report_local_hour=9, duty_h=8.0, history=hist))
    assert v.legality_state == LegalityState.REQUIRES_FRMS_DEROGATION
    assert v.metadata["longest_rest_h"] == 35.5
