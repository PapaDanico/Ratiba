"""KCAR-P8-FDP-MAX-BASIC — basic-crew maximum FDP."""

from __future__ import annotations

import pytest

from app.models.ftl import LegalityState
from app.services.ftl_engine import rule_max_fdp_basic
from tests.ftl._factories import fdp


@pytest.mark.parametrize(
    ("report_hour", "sectors", "duty_h", "expected_state", "expected_band"),
    [
        # DAY_PEAK band: limit 13h for ≤2 sectors
        (9, 2, 10.0, LegalityState.LEGAL, "DAY_PEAK"),
        (9, 2, 12.5, LegalityState.AT_LIMIT, "DAY_PEAK"),  # within 0.5h of 13h
        (9, 2, 13.0, LegalityState.AT_LIMIT, "DAY_PEAK"),  # exactly at limit
        (9, 2, 14.0, LegalityState.REQUIRES_FRMS_DEROGATION, "DAY_PEAK"),
        (9, 2, 15.5, LegalityState.ILLEGAL, "DAY_PEAK"),
        # EARLY band: limit 12h
        (5, 2, 10.0, LegalityState.LEGAL, "EARLY"),
        (5, 2, 11.6, LegalityState.AT_LIMIT, "EARLY"),
        (5, 2, 13.0, LegalityState.REQUIRES_FRMS_DEROGATION, "EARLY"),
        # AFTERNOON band: limit 12h
        (14, 2, 11.0, LegalityState.LEGAL, "AFTERNOON"),
        (14, 2, 12.5, LegalityState.REQUIRES_FRMS_DEROGATION, "AFTERNOON"),
        # WOCL band: limit 11h
        (20, 2, 9.0, LegalityState.LEGAL, "WOCL"),
        (3, 2, 11.0, LegalityState.AT_LIMIT, "WOCL"),
        # Sector reduction: DAY_PEAK 13h → 5 sectors = 13 - 3*0.5 = 11.5h
        (9, 5, 11.0, LegalityState.AT_LIMIT, "DAY_PEAK"),
        (9, 5, 11.5, LegalityState.AT_LIMIT, "DAY_PEAK"),
        (9, 5, 12.0, LegalityState.REQUIRES_FRMS_DEROGATION, "DAY_PEAK"),
        # Sector floor: 9h regardless of how many sectors
        (9, 20, 9.0, LegalityState.AT_LIMIT, "DAY_PEAK"),
        (9, 20, 8.0, LegalityState.LEGAL, "DAY_PEAK"),
    ],
)
def test_basic_fdp_states(
    report_hour: int,
    sectors: int,
    duty_h: float,
    expected_state: LegalityState,
    expected_band: str,
) -> None:
    verdict = rule_max_fdp_basic(fdp(report_local_hour=report_hour, sectors=sectors, duty_h=duty_h))
    assert verdict.legality_state == expected_state, verdict.reason
    assert verdict.rule_id == "KCAR-P8-FDP-MAX-BASIC"
    assert verdict.metadata["band"] == expected_band
    assert verdict.regulation_ref.startswith("KCAA Flight Duty Time Scheme")


def test_basic_fdp_metadata_carries_limit_and_margin() -> None:
    verdict = rule_max_fdp_basic(fdp(report_local_hour=9, sectors=2, duty_h=10.0))
    assert verdict.metadata["limit_h"] == 13.0
    assert verdict.metadata["actual_h"] == 10.0
    assert verdict.metadata["margin_h"] == pytest.approx(3.0)
