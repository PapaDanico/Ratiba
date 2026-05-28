"""KCAR-P8-REST-MIN — minimum rest before next FDP."""

from __future__ import annotations

from datetime import timedelta

from app.models.ftl import LegalityState
from app.services.ftl_engine import rule_min_rest
from tests.ftl._factories import fdp, prior_fdp_just_off


def test_no_prior_fdp_is_inapplicable() -> None:
    verdict = rule_min_rest(fdp(report_local_hour=9))
    assert verdict.legality_state == LegalityState.LEGAL
    assert verdict.metadata["applicable"] is False


def test_home_base_12h_rest_at_floor_is_at_limit() -> None:
    candidate = fdp(report_local_hour=9, at_home=True)
    prior_off = candidate.report_time - timedelta(hours=12)
    candidate = candidate.__class__(
        **{**candidate.__dict__, "prior_fdp": prior_fdp_just_off(off_duty=prior_off, duty_h=8.0)}
    )
    verdict = rule_min_rest(candidate)
    assert verdict.legality_state == LegalityState.AT_LIMIT
    assert verdict.metadata["floor_h"] == 12.0


def test_home_base_13h_rest_is_legal() -> None:
    candidate = fdp(report_local_hour=9, at_home=True)
    prior_off = candidate.report_time - timedelta(hours=13)
    candidate = candidate.__class__(
        **{**candidate.__dict__, "prior_fdp": prior_fdp_just_off(off_duty=prior_off, duty_h=8.0)}
    )
    verdict = rule_min_rest(candidate)
    assert verdict.legality_state == LegalityState.LEGAL


def test_home_base_under_floor_within_derogation() -> None:
    candidate = fdp(report_local_hour=9, at_home=True)
    prior_off = candidate.report_time - timedelta(hours=11, minutes=30)
    candidate = candidate.__class__(
        **{**candidate.__dict__, "prior_fdp": prior_fdp_just_off(off_duty=prior_off, duty_h=8.0)}
    )
    verdict = rule_min_rest(candidate)
    assert verdict.legality_state == LegalityState.REQUIRES_FRMS_DEROGATION


def test_home_base_far_under_floor_is_illegal() -> None:
    candidate = fdp(report_local_hour=9, at_home=True)
    prior_off = candidate.report_time - timedelta(hours=9)
    candidate = candidate.__class__(
        **{**candidate.__dict__, "prior_fdp": prior_fdp_just_off(off_duty=prior_off, duty_h=8.0)}
    )
    verdict = rule_min_rest(candidate)
    assert verdict.legality_state == LegalityState.ILLEGAL


def test_away_base_10h_floor() -> None:
    candidate = fdp(report_local_hour=9, at_home=False)
    prior_off = candidate.report_time - timedelta(hours=10)
    candidate = candidate.__class__(
        **{**candidate.__dict__, "prior_fdp": prior_fdp_just_off(off_duty=prior_off, duty_h=8.0)}
    )
    verdict = rule_min_rest(candidate)
    assert verdict.legality_state == LegalityState.AT_LIMIT
    assert verdict.metadata["floor_h"] == 10.0


def test_floor_lifted_by_long_preceding_duty() -> None:
    # If the prior duty was 14h, the floor is max(12h, 14h) = 14h.
    candidate = fdp(report_local_hour=9, at_home=True)
    prior_off = candidate.report_time - timedelta(hours=12)
    candidate = candidate.__class__(
        **{**candidate.__dict__, "prior_fdp": prior_fdp_just_off(off_duty=prior_off, duty_h=14.0)}
    )
    verdict = rule_min_rest(candidate)
    assert verdict.metadata["floor_h"] == 14.0
    assert verdict.legality_state == LegalityState.ILLEGAL
