"""Cumulative-window rules.

Covers:
- KCAR-P8-CUMUL-DUTY-7D
- KCAR-P8-CUMUL-DUTY-28D
- KCAR-P8-CUMUL-DUTY-365D
- KCAR-P8-CUMUL-BLOCK-28D
- KCAR-P8-CUMUL-BLOCK-365D
"""

from __future__ import annotations

import pytest

from app.models.ftl import LegalityState
from app.services.ftl_engine import (
    rule_cumulative_block_28d,
    rule_cumulative_block_365d,
    rule_cumulative_duty_7d,
    rule_cumulative_duty_28d,
    rule_cumulative_duty_365d,
)
from tests.ftl._factories import fdp, history_entry


def _with_history(days: list[tuple[int, float]], duty_h: float = 0.0, flight_h: float = 0.0):
    """Build an FdpInput at report=09:00 local with the given history.

    ``days`` is a list of (days_ago, hours) where the hours value is used for
    both duty and block on each history entry.
    """
    ref = fdp(report_local_hour=9, duty_h=duty_h, flight_h=flight_h)
    history = tuple(
        history_entry(
            days_ago=d,
            duty_h=h,
            flight_h=h,
            reference=ref.report_time,
        )
        for d, h in days
    )
    return ref.__class__(**{**ref.__dict__, "history": history})


# --- 7-day duty -------------------------------------------------------------


def test_duty_7d_far_below_limit_is_legal() -> None:
    fdp_in = _with_history([(1, 8), (2, 8), (3, 8)], duty_h=8.0)
    v = rule_cumulative_duty_7d(fdp_in)
    assert v.legality_state == LegalityState.LEGAL
    assert v.metadata["actual_h"] == pytest.approx(32.0)


def test_duty_7d_at_limit_is_at_limit() -> None:
    # 6 days × 9h + current 6h = 60h
    fdp_in = _with_history([(d, 9) for d in range(1, 7)], duty_h=6.0)
    v = rule_cumulative_duty_7d(fdp_in)
    assert v.legality_state == LegalityState.AT_LIMIT


def test_duty_7d_just_over_limit_is_derogation() -> None:
    fdp_in = _with_history([(d, 9) for d in range(1, 7)], duty_h=7.0)  # 61h
    v = rule_cumulative_duty_7d(fdp_in)
    assert v.legality_state == LegalityState.REQUIRES_FRMS_DEROGATION


def test_duty_7d_far_over_limit_is_illegal() -> None:
    fdp_in = _with_history([(d, 10) for d in range(1, 7)], duty_h=10.0)  # 70h
    v = rule_cumulative_duty_7d(fdp_in)
    assert v.legality_state == LegalityState.ILLEGAL


def test_duty_7d_excludes_history_outside_window() -> None:
    # 30 days ago does not count.
    fdp_in = _with_history([(30, 1000.0)], duty_h=8.0)
    v = rule_cumulative_duty_7d(fdp_in)
    assert v.legality_state == LegalityState.LEGAL


# --- 28-day duty ------------------------------------------------------------


def test_duty_28d_at_limit() -> None:
    # Spread 184h over 28 days + 6h current = 190h.
    days = [(i, 8.0) for i in range(1, 24)]  # 23 days × 8h = 184h
    fdp_in = _with_history(days, duty_h=6.0)
    v = rule_cumulative_duty_28d(fdp_in)
    assert v.legality_state == LegalityState.AT_LIMIT
    assert v.metadata["limit_h"] == 190.0


def test_duty_28d_legal_default() -> None:
    fdp_in = _with_history([(d, 5.0) for d in range(1, 10)], duty_h=8.0)
    v = rule_cumulative_duty_28d(fdp_in)
    assert v.legality_state == LegalityState.LEGAL


def test_duty_28d_overshoot_illegal() -> None:
    fdp_in = _with_history([(d, 9.0) for d in range(1, 28)], duty_h=10.0)
    v = rule_cumulative_duty_28d(fdp_in)
    assert v.legality_state == LegalityState.ILLEGAL


# --- 365-day duty -----------------------------------------------------------


def test_duty_365d_legal_under_2000() -> None:
    fdp_in = _with_history([(d * 10, 30.0) for d in range(1, 30)], duty_h=8.0)
    v = rule_cumulative_duty_365d(fdp_in)
    # 29 × 30 + 8 = 878h, well under 2000h
    assert v.legality_state == LegalityState.LEGAL


def test_duty_365d_overshoot() -> None:
    # 100 entries × 25h = 2500h
    fdp_in = _with_history([(d * 3, 25.0) for d in range(1, 101)], duty_h=5.0)
    v = rule_cumulative_duty_365d(fdp_in)
    assert v.legality_state == LegalityState.ILLEGAL


# --- 28-day block -----------------------------------------------------------


def test_block_28d_at_limit() -> None:
    # 95h in history + 5h current = 100h limit
    fdp_in = _with_history([(d, 5.0) for d in range(1, 20)], flight_h=5.0)
    v = rule_cumulative_block_28d(fdp_in)
    assert v.legality_state == LegalityState.AT_LIMIT


def test_block_28d_legal() -> None:
    fdp_in = _with_history([(d, 3.0) for d in range(1, 10)], flight_h=6.0)
    v = rule_cumulative_block_28d(fdp_in)
    assert v.legality_state == LegalityState.LEGAL


def test_block_28d_illegal() -> None:
    fdp_in = _with_history([(d, 8.0) for d in range(1, 20)], flight_h=8.0)
    v = rule_cumulative_block_28d(fdp_in)
    assert v.legality_state == LegalityState.ILLEGAL


# --- 365-day block ----------------------------------------------------------


def test_block_365d_legal() -> None:
    fdp_in = _with_history([(d * 5, 6.0) for d in range(1, 50)], flight_h=6.0)
    v = rule_cumulative_block_365d(fdp_in)
    assert v.legality_state == LegalityState.LEGAL


def test_block_365d_illegal() -> None:
    fdp_in = _with_history([(d * 3, 15.0) for d in range(1, 100)], flight_h=10.0)
    v = rule_cumulative_block_365d(fdp_in)
    assert v.legality_state == LegalityState.ILLEGAL
