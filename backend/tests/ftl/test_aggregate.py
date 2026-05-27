"""check_fdp() and aggregate_verdicts() orchestration."""

from __future__ import annotations

import pytest

from app.models.ftl import LegalityState
from app.services.ftl_engine import (
    FtlVerdict,
    aggregate_verdicts,
    all_rule_ids,
    check_fdp,
    validate_fdp,
)
from tests.ftl._factories import fdp


def test_check_fdp_runs_every_rule_in_stable_order() -> None:
    verdicts = check_fdp(fdp(report_local_hour=9, duty_h=10.0))
    assert [v.rule_id for v in verdicts] == all_rule_ids()


def test_aggregate_picks_worst_state() -> None:
    verdicts = [
        FtlVerdict(LegalityState.LEGAL, "R1", "ok", "ref", ["R1"]),
        FtlVerdict(LegalityState.AT_LIMIT, "R2", "tight", "ref", ["R2"]),
        FtlVerdict(LegalityState.ILLEGAL, "R3", "over", "ref", ["R3"]),
        FtlVerdict(LegalityState.LEGAL, "R4", "ok", "ref", ["R4"]),
    ]
    agg = aggregate_verdicts(verdicts)
    assert agg.legality_state == LegalityState.ILLEGAL
    assert agg.rule_id == "R3"
    assert set(agg.rules_applied) == {"R1", "R2", "R3", "R4"}


def test_aggregate_requires_at_least_one_verdict() -> None:
    with pytest.raises(ValueError):
        aggregate_verdicts([])


def test_validate_fdp_returns_both_aggregated_and_trace() -> None:
    aggregated, trace = validate_fdp(fdp(report_local_hour=9, duty_h=10.0))
    assert aggregated.legality_state == LegalityState.LEGAL
    assert len(trace) == len(all_rule_ids())


def test_clean_legal_fdp_aggregates_to_legal() -> None:
    aggregated, _ = validate_fdp(fdp(report_local_hour=9, duty_h=9.0, flight_h=7.0, sectors=2))
    assert aggregated.legality_state == LegalityState.LEGAL


def test_egregious_fdp_aggregates_to_illegal() -> None:
    aggregated, _ = validate_fdp(fdp(report_local_hour=9, duty_h=20.0, flight_h=18.0, sectors=10))
    assert aggregated.legality_state == LegalityState.ILLEGAL


def test_every_rule_id_appears_at_most_once_in_id_list() -> None:
    ids = all_rule_ids()
    assert len(ids) == len(set(ids))
