"""Phase 7 — OM-A constraint parser service (LLM mocked)."""

from __future__ import annotations

import pytest

from app.services import constraint_parser
from app.services.constraint_parser import BASELINE_FLAT
from app.services.llm_client import LlmResponse

_FAKE_JSON = """Here is the extraction:
{"rules": [
  {"rule_key": "rest_home_floor_h", "value": 14.0,
   "source_excerpt": "Minimum rest at home base shall be 14 hours.", "confidence": 0.95},
  {"rule_key": "cumul_duty_7d_h", "value": 55.0,
   "source_excerpt": "Duty in any 7 consecutive days shall not exceed 55 hours.", "confidence": 1.4},
  {"rule_key": "not_a_real_key", "value": 99, "confidence": 0.5}
]}
"""


@pytest.fixture
def stub_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake(**_kwargs: object) -> LlmResponse:
        return LlmResponse(
            text=_FAKE_JSON, input_tokens=100, output_tokens=50, model="claude-sonnet-4-5"
        )

    monkeypatch.setattr(constraint_parser.llm_client, "parser_complete", _fake)


def test_flatten_limits_dots_nested_groups() -> None:
    flat = constraint_parser.flatten_limits({"a": {"x": 1, "y": 2}, "b": 3.0})
    assert flat == {"a.x": 1, "a.y": 2, "b": 3.0}


def test_extract_json_tolerates_surrounding_prose() -> None:
    assert constraint_parser._extract_json('blah {"rules": []} trailing') == {"rules": []}


def test_extract_json_raises_without_object() -> None:
    with pytest.raises(ValueError, match="no JSON object"):
        constraint_parser._extract_json("no json here")


def test_parse_emits_every_baseline_key(stub_parser: None) -> None:
    result = constraint_parser.parse_om_a("OM-A FTL chapter text")
    assert {r.rule_key for r in result.rules} == set(BASELINE_FLAT)
    assert result.model == "claude-sonnet-4-5"


def test_parse_maps_proposals_and_baselines(stub_parser: None) -> None:
    result = constraint_parser.parse_om_a("text")
    by_key = {r.rule_key: r for r in result.rules}

    rest = by_key["rest_home_floor_h"]
    assert rest.proposed_value == 14.0
    assert rest.baseline_value == BASELINE_FLAT["rest_home_floor_h"]
    assert rest.confidence == 0.95

    # Confidence is clamped into [0, 1].
    assert by_key["cumul_duty_7d_h"].confidence == 1.0

    # Keys the OM-A didn't mention carry no proposal.
    assert by_key["at_limit_margin_h"].proposed_value is None


def test_parse_ignores_unknown_keys(stub_parser: None) -> None:
    result = constraint_parser.parse_om_a("text")
    assert all(r.rule_key in BASELINE_FLAT for r in result.rules)


def test_parse_coverage_reflects_known_proposals(stub_parser: None) -> None:
    result = constraint_parser.parse_om_a("text")
    expected = round(100.0 * 2 / len(BASELINE_FLAT), 2)
    assert result.coverage_pct == expected
