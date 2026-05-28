"""Phase 7 — LLM-driven OM-A FTL chapter parser.

Pipeline: an operator's OM-A flight-time-limitation chapter (plain text)
is handed to Claude Sonnet, which is asked to extract the numeric limits
that map onto Ratiba's internal FTL rule schema. Each extracted value is
diffed against the KCAA scheme baseline (:data:`app.services.ftl_engine.LIMITS`)
so a crewing officer reviews *changes*, not a wall of numbers.

The output is intentionally a flat ``rule_key -> value`` map (nested
baseline groups are flattened with dotted keys, e.g.
``fdp_max_basic_by_band.WOCL``) so each limit is an independently
reviewable, commentable unit.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.services import llm_client
from app.services.ftl_engine import LIMITS, REGULATION_REF

# Human context for each top-level baseline group, surfaced to both the LLM
# (so it knows what to look for) and the reviewer (so the diff reads cleanly).
GROUP_DESCRIPTIONS: dict[str, str] = {
    "fdp_max_basic_by_band": "Max flight duty period (h) for a 2-pilot basic crew, by report-time band",
    "fdp_sector_reduction_per_extra": "FDP reduction (h) per sector beyond the second",
    "fdp_sector_floor": "Floor (h) the per-sector FDP reduction cannot go below",
    "fdp_aug_3_pilot": "FDP extension (h) for a 3-pilot augmented crew, by rest-facility class",
    "fdp_aug_4_pilot": "FDP extension (h) for a 4-pilot augmented crew, by rest-facility class",
    "fdp_aug_absolute_cap": "Absolute FDP cap (h) regardless of augmentation",
    "rest_home_floor_h": "Minimum rest (h) before next FDP at home base",
    "rest_away_floor_h": "Minimum rest (h) before next FDP away from base",
    "rest_at_limit_window_h": "Window (h) above the rest floor that flags AT_LIMIT",
    "rest_derogation_window_h": "Window (h) below the rest floor needing an FRMS derogation",
    "cumul_duty_7d_h": "Cumulative duty hours limit over any 7 days",
    "cumul_duty_28d_h": "Cumulative duty hours limit over any 28 days",
    "cumul_duty_365d_h": "Cumulative duty hours limit over any 365 days",
    "cumul_block_28d_h": "Cumulative block (flight) hours limit over any 28 days",
    "cumul_block_365d_h": "Cumulative block (flight) hours limit over any 365 days",
    "standby_short_call_max_h": "Maximum short-call standby duration (h)",
    "standby_long_call_max_h": "Maximum long-call standby duration (h)",
    "split_duty_qualifying_break_h": "Minimum break (h) for a duty to qualify as split",
    "split_duty_extension_factor": "Fraction of a qualifying break credited as FDP extension",
    "split_duty_extension_cap_h": "Cap (h) on split-duty FDP extension",
    "tz_recovery": "Recovery rest (h) after crossing N time zones",
    "discretion_max_extension_h": "Max commander's-discretion FDP extension (h)",
    "discretion_max_rest_reduction_h": "Max commander's-discretion rest reduction (h)",
    "discretion_repeated_use_90d_threshold": "Discretion uses in 90 days before review is triggered",
    "at_limit_margin_h": "Margin (h) below a limit that flags AT_LIMIT",
}


@dataclass(frozen=True)
class ParsedRule:
    rule_key: str
    proposed_value: Any | None
    baseline_value: Any | None
    source_excerpt: str | None
    confidence: float | None
    regulation_ref: str


@dataclass(frozen=True)
class ParsedConstraintSet:
    model: str
    coverage_pct: float
    rules: list[ParsedRule]


def flatten_limits(limits: dict[str, Any]) -> dict[str, Any]:
    """Flatten one level of nested baseline groups into dotted keys."""
    flat: dict[str, Any] = {}
    for key, value in limits.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flat[f"{key}.{sub_key}"] = sub_value
        else:
            flat[key] = value
    return flat


BASELINE_FLAT: dict[str, Any] = flatten_limits(LIMITS)


def _describe(rule_key: str) -> str:
    group = rule_key.split(".", 1)[0]
    base = GROUP_DESCRIPTIONS.get(group, group)
    if "." in rule_key:
        return f"{base} ({rule_key.split('.', 1)[1]})"
    return base


def _build_system_prompt() -> str:
    schema_lines = "\n".join(
        f"- {key}: {_describe(key)} [baseline {BASELINE_FLAT[key]}]"
        for key in sorted(BASELINE_FLAT)
    )
    return (
        "You are an aviation flight-time-limitations (FTL) analyst. You are given "
        "the flight-time-limitation chapter of an operator's Operations Manual "
        "Part A (OM-A). Extract the operator's numeric limits and map each onto "
        "the rule keys below. The baseline is the Kenyan KCAA Flight Duty Time "
        "Scheme (CAA-AC-OPS033); only return a key if the OM-A text actually "
        "states a value for it.\n\n"
        "Return ONLY a JSON object (no prose, no code fences) of the form:\n"
        '{"rules": [{"rule_key": "<key>", "value": <number>, '
        '"source_excerpt": "<verbatim quote from the OM-A>", '
        '"confidence": <0.0-1.0>}]}\n\n'
        "Rule keys and their baseline values:\n"
        f"{schema_lines}"
    )


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the JSON object out of an LLM reply, tolerating stray prose/fences."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in parser response")
    parsed: dict[str, Any] = json.loads(text[start : end + 1])
    return parsed


def _coerce_confidence(raw: Any) -> float | None:
    try:
        conf = float(raw)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, conf))


def parse_om_a(
    om_a_text: str,
    *,
    session: Session | None = None,
    operator_id: uuid.UUID | None = None,
) -> ParsedConstraintSet:
    """Parse an OM-A FTL chapter into a reviewable, baseline-diffed rule set."""
    response = llm_client.parser_complete(
        system=_build_system_prompt(),
        user_message=om_a_text,
        session=session,
        operator_id=operator_id,
    )
    payload = _extract_json(response.text)
    proposed_by_key: dict[str, dict[str, Any]] = {}
    raw_rules = payload.get("rules", [])
    if isinstance(raw_rules, list):
        for item in raw_rules:
            if not isinstance(item, dict):
                continue
            key = item.get("rule_key")
            if isinstance(key, str) and key in BASELINE_FLAT:
                proposed_by_key[key] = item

    rules: list[ParsedRule] = []
    for key in sorted(BASELINE_FLAT):
        item = proposed_by_key.get(key)
        rules.append(
            ParsedRule(
                rule_key=key,
                proposed_value=item.get("value") if item else None,
                baseline_value=BASELINE_FLAT[key],
                source_excerpt=item.get("source_excerpt") if item else None,
                confidence=_coerce_confidence(item.get("confidence")) if item else None,
                regulation_ref=REGULATION_REF,
            )
        )

    covered = sum(1 for r in rules if r.proposed_value is not None)
    coverage_pct = round(100.0 * covered / len(rules), 2) if rules else 0.0
    return ParsedConstraintSet(model=response.model, coverage_pct=coverage_pct, rules=rules)
