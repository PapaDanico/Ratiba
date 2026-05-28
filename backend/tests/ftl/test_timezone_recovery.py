"""Time-zone crossing recovery rule. Covers KCAR-P8-TZ-RECOVERY."""

from __future__ import annotations

from datetime import timedelta

from app.models.ftl import LegalityState
from app.services.ftl_engine import rule_timezone_recovery
from tests.ftl._factories import fdp, prior_fdp_just_off


def _with_prior_tz(*, hours_rest: float, zones_crossed: int):
    base = fdp(report_local_hour=9)
    prior_off = base.report_time - timedelta(hours=hours_rest)
    return base.__class__(
        **{
            **base.__dict__,
            "prior_fdp": prior_fdp_just_off(
                off_duty=prior_off, duty_h=10.0, tz_crossed=zones_crossed
            ),
        }
    )


def test_no_prior_tz_is_inapplicable() -> None:
    v = rule_timezone_recovery(fdp(report_local_hour=9))
    assert v.metadata["applicable"] is False


def test_under_4_zones_is_inapplicable() -> None:
    v = rule_timezone_recovery(_with_prior_tz(hours_rest=24, zones_crossed=3))
    assert v.metadata["applicable"] is False


def test_4_zones_36h_floor_legal() -> None:
    v = rule_timezone_recovery(_with_prior_tz(hours_rest=40, zones_crossed=4))
    assert v.legality_state == LegalityState.LEGAL
    assert v.metadata["floor_h"] == 36.0


def test_4_zones_under_floor_illegal() -> None:
    v = rule_timezone_recovery(_with_prior_tz(hours_rest=24, zones_crossed=4))
    assert v.legality_state == LegalityState.ILLEGAL


def test_6_zones_uses_48h_floor() -> None:
    v = rule_timezone_recovery(_with_prior_tz(hours_rest=50, zones_crossed=6))
    assert v.metadata["floor_h"] == 48.0
    assert v.legality_state == LegalityState.LEGAL


def test_8_zones_uses_72h_floor_and_under_is_illegal() -> None:
    v = rule_timezone_recovery(_with_prior_tz(hours_rest=60, zones_crossed=8))
    assert v.metadata["floor_h"] == 72.0
    assert v.legality_state == LegalityState.ILLEGAL
