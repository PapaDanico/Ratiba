"""Split duty rule. Covers KCAR-P8-SPLIT-DUTY."""

from __future__ import annotations

import pytest

from app.models.ftl import LegalityState
from app.services.ftl_engine import rule_split_duty
from tests.ftl._factories import fdp


def test_break_below_threshold_no_extension() -> None:
    v = rule_split_duty(fdp(split_break_h=2.0, duty_h=10.0))
    assert v.legality_state == LegalityState.LEGAL
    assert v.metadata["applicable"] is False


def test_qualifying_break_extends_fdp() -> None:
    # 4h break → extension min(4*0.5, 2) = 2h; basic limit 13h → effective 15h
    v = rule_split_duty(fdp(split_break_h=4.0, duty_h=14.0, sectors=2, report_local_hour=9))
    assert v.legality_state == LegalityState.LEGAL
    assert v.metadata["extension_h"] == pytest.approx(2.0)
    assert v.metadata["effective_limit_h"] == pytest.approx(15.0)


def test_break_at_threshold_extends_half_break() -> None:
    # 3h break → extension 1.5h; basic 13h → effective 14.5h
    v = rule_split_duty(fdp(split_break_h=3.0, duty_h=14.0, sectors=2, report_local_hour=9))
    assert v.metadata["extension_h"] == pytest.approx(1.5)


def test_qualifying_break_but_duty_exceeds_effective_limit() -> None:
    # 4h break → 15h effective; duty 16h → derogation
    v = rule_split_duty(fdp(split_break_h=4.0, duty_h=16.0, sectors=2, report_local_hour=9))
    assert v.legality_state == LegalityState.REQUIRES_FRMS_DEROGATION
