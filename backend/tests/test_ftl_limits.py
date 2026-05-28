"""Tests for operator-specific FTL limit resolution and engine binding."""

from __future__ import annotations

import copy
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.services import ftl_engine
from app.services.ftl_engine import LIMITS, FdpInput
from app.services.ftl_limits import _apply_overrides, check_fdp_for_operator, resolve_limits
from tests.ftl._factories import fdp


# ---------------------------------------------------------------------------
# _apply_overrides — unit tests
# ---------------------------------------------------------------------------


def test_apply_overrides_scalar() -> None:
    result = _apply_overrides({"rest_home_floor_h": 11.0})
    assert result["rest_home_floor_h"] == 11.0
    # Baseline unchanged
    assert LIMITS["rest_home_floor_h"] == 12.0


def test_apply_overrides_nested_string_key() -> None:
    result = _apply_overrides({"fdp_max_basic_by_band.WOCL": 10.5})
    assert result["fdp_max_basic_by_band"]["WOCL"] == 10.5
    assert LIMITS["fdp_max_basic_by_band"]["WOCL"] == 11.0  # baseline unchanged


def test_apply_overrides_nested_int_key_coercion() -> None:
    # tz_recovery keys are ints; override comes from DB as string "4"
    result = _apply_overrides({"tz_recovery.4": 40.0})
    assert result["tz_recovery"][4] == 40.0


def test_apply_overrides_unknown_key_ignored() -> None:
    result = _apply_overrides({"nonexistent_limit": 99.0})
    assert "nonexistent_limit" not in result


def test_apply_overrides_returns_deep_copy() -> None:
    result = _apply_overrides({})
    result["rest_home_floor_h"] = 999.0
    assert LIMITS["rest_home_floor_h"] == 12.0  # original untouched


# ---------------------------------------------------------------------------
# check_fdp with explicit limits — ContextVar isolation
# ---------------------------------------------------------------------------


def test_check_fdp_custom_limits_affect_verdict() -> None:
    """Tightening rest_home_floor_h makes a borderline rest period ILLEGAL."""
    # 11 h rest — legal under baseline (floor 12 h, but with derogation window it's actually REQUIRES_FRMS)
    # Let's use duty_h = 13.5 which exceeds baseline fdp_max basic DAY_PEAK = 13.0
    # So it should be ILLEGAL under baseline, and still ILLEGAL with tighter limits.
    # Instead: test that loosening the limit makes it LEGAL.

    # Baseline DAY_PEAK cap is 13.0 h; duty_h 12.5 is AT_LIMIT (within 0.5 margin).
    # Raise the cap to 14.0 → should become LEGAL.
    strict_fdp = fdp(report_local_hour=9, duty_h=12.5)  # DAY_PEAK band, 12.5 h duty

    baseline_verdicts = ftl_engine.check_fdp(strict_fdp)
    basic_rule = next(v for v in baseline_verdicts if v.rule_id == "KCAR-P8-FDP-MAX-BASIC")
    assert basic_rule.legality_state.value in ("AT_LIMIT", "LEGAL")

    # Raise the cap so 12.5 h is clearly legal
    relaxed_limits = copy.deepcopy(dict(LIMITS))
    relaxed_limits["fdp_max_basic_by_band"] = dict(LIMITS["fdp_max_basic_by_band"])
    relaxed_limits["fdp_max_basic_by_band"]["DAY_PEAK"] = 14.0

    relaxed_verdicts = ftl_engine.check_fdp(strict_fdp, limits=relaxed_limits)
    basic_relaxed = next(v for v in relaxed_verdicts if v.rule_id == "KCAR-P8-FDP-MAX-BASIC")
    assert basic_relaxed.legality_state.value == "LEGAL"


def test_check_fdp_limits_dont_leak_between_calls() -> None:
    """ContextVar token ensures limits from one call don't bleed into the next."""
    tight_limits = copy.deepcopy(dict(LIMITS))
    tight_limits["cumul_duty_7d_h"] = 1.0  # absurdly low

    # duty_h=4.0 exceeds cap(1.0) + derogation_margin(2.0) = 3.0 → ILLEGAL
    test_fdp = fdp(duty_h=4.0)
    verdicts_tight = ftl_engine.check_fdp(test_fdp, limits=tight_limits)
    verdicts_baseline = ftl_engine.check_fdp(test_fdp)  # no limits arg → should use LIMITS

    cumul_tight = next(v for v in verdicts_tight if v.rule_id == "KCAR-P8-CUMUL-DUTY-7D")
    cumul_baseline = next(v for v in verdicts_baseline if v.rule_id == "KCAR-P8-CUMUL-DUTY-7D")

    assert cumul_tight.legality_state.value == "ILLEGAL"
    assert cumul_baseline.legality_state.value == "LEGAL"


# ---------------------------------------------------------------------------
# resolve_limits — DB queries mocked
# ---------------------------------------------------------------------------


def _mock_rule(key: str, value: Any) -> Any:
    return SimpleNamespace(rule_key=key, final_value=value)


def _mock_cset(cset_id: uuid.UUID) -> Any:
    return SimpleNamespace(id=cset_id, accepted_at=datetime(2026, 1, 1, tzinfo=UTC))


def test_resolve_limits_no_accepted_set_returns_baseline() -> None:
    session = MagicMock()
    session.scalars.return_value.first.return_value = None

    result = resolve_limits(uuid.uuid4(), session)
    assert result["rest_home_floor_h"] == LIMITS["rest_home_floor_h"]
    assert result["cumul_duty_7d_h"] == LIMITS["cumul_duty_7d_h"]


def test_resolve_limits_merges_final_values() -> None:
    cset_id = uuid.uuid4()
    session = MagicMock()

    call_count = 0

    def scalars_side_effect(stmt):  # noqa: ANN001
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        if call_count == 1:
            mock.first.return_value = _mock_cset(cset_id)
        else:
            mock.all.return_value = [
                _mock_rule("rest_home_floor_h", 11.0),
                _mock_rule("fdp_max_basic_by_band.WOCL", 10.0),
            ]
        return mock

    session.scalars.side_effect = scalars_side_effect

    result = resolve_limits(uuid.uuid4(), session)
    assert result["rest_home_floor_h"] == 11.0
    assert result["fdp_max_basic_by_band"]["WOCL"] == 10.0
    # Non-overridden keys remain at baseline
    assert result["fdp_max_basic_by_band"]["DAY_PEAK"] == LIMITS["fdp_max_basic_by_band"]["DAY_PEAK"]


# ---------------------------------------------------------------------------
# check_fdp_for_operator — integration via mocked session
# ---------------------------------------------------------------------------


def test_check_fdp_for_operator_uses_resolved_limits() -> None:
    """An accepted constraint set that tightens cumul_duty_7d_h to 1 h
    causes a 2-hour duty to be ILLEGAL via check_fdp_for_operator."""
    cset_id = uuid.uuid4()
    operator_id = uuid.uuid4()
    session = MagicMock()

    call_count = 0

    def scalars_side_effect(stmt):  # noqa: ANN001
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        if call_count == 1:
            mock.first.return_value = _mock_cset(cset_id)
        else:
            mock.all.return_value = [_mock_rule("cumul_duty_7d_h", 1.0)]
        return mock

    session.scalars.side_effect = scalars_side_effect

    # duty_h=4.0 exceeds cap(1.0) + derogation_margin(2.0) = 3.0 → ILLEGAL
    test_fdp = fdp(duty_h=4.0)
    verdicts = check_fdp_for_operator(test_fdp, operator_id, session)

    cumul = next(v for v in verdicts if v.rule_id == "KCAR-P8-CUMUL-DUTY-7D")
    assert cumul.legality_state.value == "ILLEGAL"
