"""Standby rules.

Covers:
- KCAR-P8-STANDBY-SHORT-CALL
- KCAR-P8-STANDBY-LONG-CALL
"""

from __future__ import annotations

from app.models.ftl import LegalityState
from app.services.ftl_engine import rule_standby_long_call, rule_standby_short_call
from tests.ftl._factories import fdp


def test_short_call_not_applicable_when_not_on_standby() -> None:
    v = rule_standby_short_call(fdp(standby_type="NONE"))
    assert v.legality_state == LegalityState.LEGAL
    assert v.metadata["applicable"] is False


def test_short_call_within_limit_and_combined_under_fdp() -> None:
    # 4h standby + 8h duty = 12h, basic limit 13h → LEGAL (margin 1h)
    v = rule_standby_short_call(
        fdp(
            standby_type="SHORT_CALL",
            standby_h=4.0,
            duty_h=8.0,
            sectors=2,
            report_local_hour=9,
        )
    )
    assert v.legality_state == LegalityState.LEGAL


def test_short_call_combined_at_fdp_limit() -> None:
    # 4h standby + 9h duty = 13h, at the 13h DAY_PEAK limit
    v = rule_standby_short_call(
        fdp(
            standby_type="SHORT_CALL",
            standby_h=4.0,
            duty_h=9.0,
            sectors=2,
            report_local_hour=9,
        )
    )
    assert v.legality_state == LegalityState.AT_LIMIT


def test_short_call_max_standby_duration_exceeded() -> None:
    v = rule_standby_short_call(
        fdp(
            standby_type="SHORT_CALL",
            standby_h=13.0,  # over 12h max
            duty_h=2.0,
            sectors=2,
        )
    )
    assert v.legality_state == LegalityState.ILLEGAL


def test_long_call_not_applicable_when_not_on_standby() -> None:
    v = rule_standby_long_call(fdp(standby_type="NONE"))
    assert v.metadata["applicable"] is False


def test_long_call_within_24h_is_legal() -> None:
    v = rule_standby_long_call(fdp(standby_type="LONG_CALL", standby_h=20.0))
    assert v.legality_state == LegalityState.LEGAL


def test_long_call_overshoot_is_illegal() -> None:
    v = rule_standby_long_call(fdp(standby_type="LONG_CALL", standby_h=27.0))
    assert v.legality_state == LegalityState.ILLEGAL
