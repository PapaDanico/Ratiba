"""The optimiser draft honours the operator's resolved FTL limits.

Mirrors the publish path: a duty day that's LEGAL under the baseline but
ILLEGAL under a tighter operator scheme must be pruned (left unassigned),
so the auto-generated draft matches what publish would record.
"""

from __future__ import annotations

import copy
from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.crew import CrewRole
from app.services import optimiser
from app.services.ftl_engine import LIMITS


def _input() -> optimiser.OptimiserInput:
    # std 08:00Z, sta 18:30Z → 10.5 h block; report 07:00Z (10:00 Nairobi,
    # DAY_PEAK), off 19:00Z → 12 h duty.
    sector = optimiser.SectorInput(
        sector_id="KQ1",
        date_local=date(2025, 6, 2),
        std=datetime(2025, 6, 2, 8, 0, tzinfo=UTC),
        sta=datetime(2025, 6, 2, 18, 30, tzinfo=UTC),
        aircraft_reg="5Y-AB",
        aircraft_type="C208",
        block_hours=Decimal("10.5"),
    )
    crew = (
        optimiser.CrewProfile(crew_id="C1", role=CrewRole.CAPT, type_ratings=("C208",)),
        optimiser.CrewProfile(crew_id="F1", role=CrewRole.FO, type_ratings=("C208",)),
    )
    return optimiser.OptimiserInput(
        horizon_from=date(2025, 6, 2),
        horizon_to=date(2025, 6, 2),
        crew=crew,
        sectors=(sector,),
        timeout_s=10.0,
    )


def test_baseline_assigns_the_duty() -> None:
    result = optimiser.solve(_input())
    assert len(result.assignments) == 1
    assert result.unassigned_duty_days == ()


def test_tight_operator_limits_prune_the_duty() -> None:
    # Operator scheme caps DAY_PEAK FDP at 6 h (clamped up to the 9 h floor);
    # a 12 h duty is then > 9 + 2 h → ILLEGAL → pruned.
    tight = copy.deepcopy(dict(LIMITS))
    tight["fdp_max_basic_by_band"] = {**tight["fdp_max_basic_by_band"], "DAY_PEAK": 6.0}

    result = optimiser.solve(_input(), limits=tight)
    assert result.assignments == ()
    assert result.unassigned_duty_days == ("5Y-AB|2025-06-02",)
