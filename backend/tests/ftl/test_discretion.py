"""Commander's discretion rule. Covers KCAR-P8-DISCRETION."""

from __future__ import annotations

from app.models.ftl import LegalityState
from app.services.ftl_engine import rule_discretion
from tests.ftl._factories import fdp


def test_no_discretion_applied_is_legal() -> None:
    v = rule_discretion(fdp(discretion_h=0.0, discretion_uses_90d=0))
    assert v.legality_state == LegalityState.LEGAL


def test_discretion_within_cap_requires_derogation() -> None:
    v = rule_discretion(fdp(discretion_h=1.5, discretion_uses_90d=0))
    assert v.legality_state == LegalityState.REQUIRES_FRMS_DEROGATION
    assert v.metadata["extension_h"] == 1.5


def test_discretion_at_cap_requires_derogation() -> None:
    v = rule_discretion(fdp(discretion_h=2.0, discretion_uses_90d=0))
    assert v.legality_state == LegalityState.REQUIRES_FRMS_DEROGATION


def test_discretion_over_cap_is_illegal() -> None:
    v = rule_discretion(fdp(discretion_h=2.5, discretion_uses_90d=0))
    assert v.legality_state == LegalityState.ILLEGAL


def test_repeated_use_flags_at_limit_even_without_discretion() -> None:
    v = rule_discretion(fdp(discretion_h=0.0, discretion_uses_90d=4))
    assert v.legality_state == LegalityState.AT_LIMIT


def test_repeated_use_below_threshold_remains_legal() -> None:
    v = rule_discretion(fdp(discretion_h=0.0, discretion_uses_90d=2))
    assert v.legality_state == LegalityState.LEGAL
