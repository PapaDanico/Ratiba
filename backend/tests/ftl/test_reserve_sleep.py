"""Reserve sleep-opportunity rule — KCAR-P8-RESERVE-SLEEP (CAA-AC-OPS033 §4.6.8)."""

from __future__ import annotations

from app.models.ftl import LegalityState
from app.services.ftl_engine import rule_reserve_sleep_opportunity
from tests.ftl._factories import fdp


def test_not_applicable_when_not_on_standby() -> None:
    v = rule_reserve_sleep_opportunity(fdp(standby_type="NONE", reserve_sleep_h=2.0))
    assert v.legality_state == LegalityState.LEGAL
    assert v.metadata["applicable"] is False


def test_ample_sleep_opportunity_is_legal() -> None:
    v = rule_reserve_sleep_opportunity(fdp(standby_type="SHORT_CALL", reserve_sleep_h=10.0))
    assert v.legality_state == LegalityState.LEGAL
    assert v.rule_id == "KCAR-P8-RESERVE-SLEEP"


def test_exactly_at_floor_is_at_limit() -> None:
    # Floor is 8 h; exactly 8 h sits in the AT_LIMIT band.
    v = rule_reserve_sleep_opportunity(fdp(standby_type="LONG_CALL", reserve_sleep_h=8.0))
    assert v.legality_state == LegalityState.AT_LIMIT


def test_just_below_floor_requires_derogation() -> None:
    v = rule_reserve_sleep_opportunity(fdp(standby_type="SHORT_CALL", reserve_sleep_h=7.5))
    assert v.legality_state == LegalityState.REQUIRES_FRMS_DEROGATION


def test_well_below_floor_is_illegal() -> None:
    v = rule_reserve_sleep_opportunity(fdp(standby_type="SHORT_CALL", reserve_sleep_h=5.0))
    assert v.legality_state == LegalityState.ILLEGAL
    assert v.metadata["floor_h"] == 8.0
