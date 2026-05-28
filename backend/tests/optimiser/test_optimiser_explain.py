"""Explain endpoint — ≥3 binding constraints per FDP (Plan §5 Phase 2)."""

from __future__ import annotations

from app.services import optimiser
from tests.optimiser._factories import small_scenario, with_leave


def test_explain_returns_at_least_three_bindings() -> None:
    input_ = small_scenario(horizon_days=1, aircraft=1)
    duty_days = optimiser.build_duty_days(input_.sectors)
    dd_key = duty_days[0].duty_day_key

    explanation = optimiser.explain(input_, dd_key)
    assert len(explanation.bindings) >= 3
    rule_ids = [b.rule_id for b in explanation.bindings]
    assert "OPT-COVERAGE" in rule_ids
    assert "OPT-TYPE-RATING" in rule_ids
    assert "OPT-FTL" in rule_ids


def test_explain_surfaces_leave_when_applicable() -> None:
    base = small_scenario(horizon_days=1, aircraft=1)
    input_ = with_leave(base, crew_id="CAP-1", day_offset=0)
    dd_key = optimiser.build_duty_days(input_.sectors)[0].duty_day_key

    explanation = optimiser.explain(input_, dd_key)
    rule_ids = [b.rule_id for b in explanation.bindings]
    assert "OPT-AVAILABILITY" in rule_ids
    avail = next(b for b in explanation.bindings if b.rule_id == "OPT-AVAILABILITY")
    assert "CAP-1" in avail.metadata["unavailable_crew"]


def test_explain_unknown_duty_day_returns_empty() -> None:
    input_ = small_scenario(horizon_days=1, aircraft=1)
    explanation = optimiser.explain(input_, "5Y-NOPE|2025-01-01")
    assert explanation.bindings == ()
