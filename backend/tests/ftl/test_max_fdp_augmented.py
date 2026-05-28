"""KCAR-P8-FDP-MAX-AUG — augmented-crew maximum FDP extension."""

from __future__ import annotations

import pytest

from app.models.ftl import LegalityState
from app.services.ftl_engine import rule_max_fdp_augmented
from tests.ftl._factories import fdp


def test_not_augmented_returns_legal_with_inapplicable() -> None:
    verdict = rule_max_fdp_augmented(
        fdp(report_local_hour=9, duty_h=12.0, augmented=False, pilots=2)
    )
    assert verdict.legality_state == LegalityState.LEGAL
    assert verdict.metadata["applicable"] is False


def test_augmented_3_pilot_class_1_extends_by_3h() -> None:
    # Basic limit DAY_PEAK = 13h; 3p class 1 = +3h → 16h
    verdict = rule_max_fdp_augmented(
        fdp(
            report_local_hour=9,
            duty_h=15.5,  # within 0.5h of 16h
            augmented=True,
            pilots=3,
            rest_class=1,
        )
    )
    assert verdict.legality_state == LegalityState.AT_LIMIT
    assert verdict.metadata["limit_h"] == pytest.approx(16.0)
    assert verdict.metadata["extension_h"] == pytest.approx(3.0)


def test_augmented_3_pilot_class_3_extends_by_1h() -> None:
    # 13h + 1h = 14h; 13.0h actual leaves a full 1h margin → LEGAL
    verdict = rule_max_fdp_augmented(
        fdp(
            report_local_hour=9,
            duty_h=13.0,
            augmented=True,
            pilots=3,
            rest_class=3,
        )
    )
    assert verdict.legality_state == LegalityState.LEGAL
    assert verdict.metadata["limit_h"] == pytest.approx(14.0)


def test_augmented_4_pilot_class_1_extends_by_4h_capped_at_18h() -> None:
    # Basic 13h + 4h = 17h, under the 18h absolute cap
    verdict = rule_max_fdp_augmented(
        fdp(
            report_local_hour=9,
            duty_h=17.0,
            augmented=True,
            pilots=4,
            rest_class=1,
        )
    )
    assert verdict.legality_state == LegalityState.AT_LIMIT
    assert verdict.metadata["limit_h"] == pytest.approx(17.0)


def test_augmented_without_rest_facility_falls_back_to_basic() -> None:
    verdict = rule_max_fdp_augmented(
        fdp(
            report_local_hour=9,
            duty_h=13.5,
            augmented=True,
            pilots=3,
            rest_class=0,
        )
    )
    assert verdict.metadata["applicable"] is False


def test_augmented_overshoot_is_illegal_or_derogation() -> None:
    # 3-pilot class 1 = 16h; 16.5h is within 2h derogation window
    derogation = rule_max_fdp_augmented(
        fdp(
            report_local_hour=9,
            duty_h=16.5,
            augmented=True,
            pilots=3,
            rest_class=1,
        )
    )
    assert derogation.legality_state == LegalityState.REQUIRES_FRMS_DEROGATION
    # 18.5h is beyond the derogation window
    illegal = rule_max_fdp_augmented(
        fdp(
            report_local_hour=9,
            duty_h=18.5,
            augmented=True,
            pilots=3,
            rest_class=1,
        )
    )
    assert illegal.legality_state == LegalityState.ILLEGAL
