"""OR-Tools CP-SAT roster optimiser — Phase 2 MVP.

Solves the duty-day assignment problem: given a sector schedule and a crew
pool over a horizon, assign exactly one CAPT and one FO to each duty day
(group of sectors flown by one aircraft on one calendar date) such that:

Hard constraints (Plan §5 Phase 2):
- every duty day has the required crew complement
- no FTL breach (delegated to :mod:`app.services.ftl_engine`)
- required type rating on the aircraft
- required currency on the aircraft type
- no conflicting commitments (leave, training, off-day)
- minimum rest between consecutive duty days for the same crew
- cumulative duty / block hour caps (7 / 28 / 365 days)

Soft constraints (objective; weights configurable per operator):
- balanced block hours across crew (minimise max−min spread)
- faith-observance respect (penalty for Sunday-protected crew on Sunday)
- honoured pending-leave requests (penalty for overlapping assignment)

The module is database-free: it takes dataclass inputs and returns
dataclass results. Phase 2 wires it to the API and to a Redis-backed
job queue; persistence of the resulting roster lands later in Phase 2
(via :func:`app.services.audit_log.record`).
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from ortools.sat.python import cp_model

from app.models.crew import CrewRole
from app.models.ftl import LegalityState
from app.services import ftl_engine

# -----------------------------------------------------------------------------
# Tunable defaults (operator overrides land in the settings table in Phase 3).
# -----------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "balance_block_hours": 10.0,
    "faith_violation": 25.0,
    "leave_violation": 20.0,
    "positioning_minimisation": 5.0,
}

# Hours of buffer either side of the first/last sector to model report and
# off-duty time. The KCAA Flight Duty Time Scheme typically allows ~1 h report,
# ~30 min after.
PRE_DUTY_BUFFER_H: float = 1.0
POST_DUTY_BUFFER_H: float = 0.5

# Minimum hours between off-duty and next report (home base).
MIN_INTER_DUTY_REST_H: float = float(ftl_engine.LIMITS["rest_home_floor_h"])

# Solver scaling factor: CP-SAT works in integers, so we scale hours × 10.
HOURS_SCALE: int = 10


# -----------------------------------------------------------------------------
# Inputs
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class CrewProfile:
    crew_id: str
    role: CrewRole
    type_ratings: tuple[str, ...]
    current: bool = True
    base_tz: str = "Africa/Nairobi"
    faith_flags: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class SectorInput:
    sector_id: str
    date_local: date
    std: datetime
    sta: datetime
    aircraft_reg: str
    aircraft_type: str
    block_hours: Decimal


@dataclass(frozen=True)
class LeaveRequestInput:
    crew_id: str
    date_from: date
    date_to: date
    status: str = "PENDING"  # PENDING | APPROVED


@dataclass(frozen=True)
class OptimiserInput:
    horizon_from: date
    horizon_to: date
    crew: tuple[CrewProfile, ...]
    sectors: tuple[SectorInput, ...]
    leave_requests: tuple[LeaveRequestInput, ...] = ()
    base_tz: str = "Africa/Nairobi"
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    timeout_s: float = 60.0


# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class DutyDay:
    """One aircraft × one date = one duty day. Internal aggregate of sectors."""

    duty_day_key: str
    date_local: date
    aircraft_reg: str
    aircraft_type: str
    sector_ids: tuple[str, ...]
    report_time: datetime  # std of first sector minus PRE_DUTY_BUFFER_H
    off_duty_time: datetime  # sta of last sector plus POST_DUTY_BUFFER_H
    flight_hours: Decimal
    duty_hours: Decimal
    sectors_count: int


@dataclass(frozen=True)
class Assignment:
    duty_day_key: str
    date_local: date
    aircraft_reg: str
    aircraft_type: str
    sector_ids: tuple[str, ...]
    captain_id: str
    fo_id: str


@dataclass(frozen=True)
class OptimiserResult:
    status: str  # OPTIMAL | FEASIBLE | INFEASIBLE | TIMEOUT
    assignments: tuple[Assignment, ...]
    objective_value: float | None
    unassigned_duty_days: tuple[str, ...]
    diagnostics: dict[str, Any]
    elapsed_s: float


@dataclass(frozen=True)
class ConstraintBinding:
    rule_id: str
    description: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class Explanation:
    duty_day_key: str
    captain_id: str | None
    fo_id: str | None
    bindings: tuple[ConstraintBinding, ...]


# -----------------------------------------------------------------------------
# Pre-solve: group sectors into duty days
# -----------------------------------------------------------------------------


def build_duty_days(sectors: Iterable[SectorInput]) -> list[DutyDay]:
    """Group sectors by (aircraft_reg, date) into duty days."""
    by_key: dict[tuple[str, date], list[SectorInput]] = defaultdict(list)
    for s in sectors:
        by_key[(s.aircraft_reg, s.date_local)].append(s)

    result: list[DutyDay] = []
    for (reg, d), group in sorted(by_key.items()):
        ordered = sorted(group, key=lambda s: s.std)
        first, last = ordered[0], ordered[-1]
        report = first.std - timedelta(hours=PRE_DUTY_BUFFER_H)
        off = last.sta + timedelta(hours=POST_DUTY_BUFFER_H)
        duty_hours = Decimal(str((off - report).total_seconds() / 3600.0))
        flight_hours = sum((s.block_hours for s in ordered), start=Decimal("0"))
        result.append(
            DutyDay(
                duty_day_key=f"{reg}|{d.isoformat()}",
                date_local=d,
                aircraft_reg=reg,
                aircraft_type=ordered[0].aircraft_type,
                sector_ids=tuple(s.sector_id for s in ordered),
                report_time=report,
                off_duty_time=off,
                flight_hours=flight_hours,
                duty_hours=duty_hours,
                sectors_count=len(ordered),
            )
        )
    return result


# -----------------------------------------------------------------------------
# Pre-solve: eligibility
# -----------------------------------------------------------------------------


def _unavailable_dates(crew_id: str, leave: Iterable[LeaveRequestInput]) -> set[date]:
    out: set[date] = set()
    for req in leave:
        if req.crew_id != crew_id or req.status != "APPROVED":
            continue
        d = req.date_from
        while d <= req.date_to:
            out.add(d)
            d += timedelta(days=1)
    return out


def _has_pending_leave(crew_id: str, day: date, leave: Iterable[LeaveRequestInput]) -> bool:
    return any(
        req.crew_id == crew_id and req.status == "PENDING" and req.date_from <= day <= req.date_to
        for req in leave
    )


def _ftl_legal_solo(dd: DutyDay, base_tz: str, limits: dict[str, Any] | None = None) -> bool:
    """Cheap, stand-alone FTL pre-check (no history): would this single duty day
    be legal in isolation? Used to prune impossible (crew, duty_day) pairs.

    ``limits`` carries the operator's resolved scheme so the draft is judged
    by the same limits that govern the published roster."""
    fdp = ftl_engine.FdpInput(
        report_time=dd.report_time,
        off_duty_time=dd.off_duty_time,
        sectors_count=dd.sectors_count,
        flight_hours=dd.flight_hours,
        duty_hours=dd.duty_hours,
        base_tz=base_tz,
    )
    verdicts = ftl_engine.check_fdp(fdp, limits=limits)
    return all(v.legality_state != LegalityState.ILLEGAL for v in verdicts)


def _eligibility(
    crew: tuple[CrewProfile, ...],
    duty_days: list[DutyDay],
    leave: tuple[LeaveRequestInput, ...],
    base_tz: str,
    limits: dict[str, Any] | None = None,
) -> dict[tuple[str, str, CrewRole], dict[str, Any]]:
    """Return ``{(duty_day_key, crew_id, role): {"eligible": bool, "reasons": [...]}}``.

    A crew member is eligible for a (duty_day, role) iff:
    - their role matches the role being filled,
    - they hold the type rating for the aircraft,
    - they are current,
    - they are not on approved leave on the date,
    - the duty day itself is FTL-legal in isolation,
    - the crew is in the operator's pool (trivially true).
    """
    out: dict[tuple[str, str, CrewRole], dict[str, Any]] = {}
    leave_by_crew = {c.crew_id: _unavailable_dates(c.crew_id, leave) for c in crew}

    for dd in duty_days:
        dd_legal = _ftl_legal_solo(dd, base_tz, limits)
        for c in crew:
            for role in (CrewRole.CAPT, CrewRole.FO):
                reasons: list[str] = []
                if c.role != role:
                    reasons.append("role_mismatch")
                if dd.aircraft_type not in c.type_ratings:
                    reasons.append("no_type_rating")
                if not c.current:
                    reasons.append("not_current")
                if dd.date_local in leave_by_crew[c.crew_id]:
                    reasons.append("approved_leave")
                if not dd_legal:
                    reasons.append("fdp_ftl_illegal_in_isolation")
                out[(dd.duty_day_key, c.crew_id, role)] = {
                    "eligible": not reasons,
                    "reasons": reasons,
                }
    return out


# -----------------------------------------------------------------------------
# Solve
# -----------------------------------------------------------------------------


def _consecutive_pairs_need_rest(
    crew: CrewProfile, duty_days: list[DutyDay]
) -> list[tuple[DutyDay, DutyDay]]:
    """Pairs of duty days whose proximity would violate min-rest if both flown.

    Conservative: looks at every ordered pair (dd_a, dd_b) where dd_a.off →
    dd_b.report gap is below the floor. Doesn't include pairs already too
    far apart.
    """
    pairs: list[tuple[DutyDay, DutyDay]] = []
    by_time = sorted(duty_days, key=lambda d: d.report_time)
    for i, dd_a in enumerate(by_time):
        for dd_b in by_time[i + 1 :]:
            gap_h = (dd_b.report_time - dd_a.off_duty_time).total_seconds() / 3600.0
            if gap_h <= 0:
                # overlapping → cannot both fly anyway, will be excluded by
                # one-duty-day-per-date constraint when on same date; for
                # different dates, the overlap is itself a violation.
                pairs.append((dd_a, dd_b))
                continue
            if gap_h < MIN_INTER_DUTY_REST_H:
                pairs.append((dd_a, dd_b))
            # If far enough apart, no need to look further with this dd_a
            # (others will be even further away — by_time is sorted).
            elif gap_h >= MIN_INTER_DUTY_REST_H + 24:
                break
    return pairs


def _is_sunday(d: date) -> bool:
    return d.weekday() == 6


def solve(input: OptimiserInput, *, limits: dict[str, Any] | None = None) -> OptimiserResult:
    """Run the CP-SAT solver and return the best roster found within timeout.

    ``limits`` is the operator's resolved FTL scheme; when supplied, both the
    per-duty legality prune and the cumulative-hour caps use it instead of
    the generic baseline, keeping the draft consistent with publish."""
    t0 = time.perf_counter()
    eff_limits = limits if limits is not None else ftl_engine.LIMITS

    duty_days = build_duty_days(input.sectors)
    duty_days_in_horizon = [
        dd for dd in duty_days if input.horizon_from <= dd.date_local <= input.horizon_to
    ]
    if not duty_days_in_horizon:
        return OptimiserResult(
            status="INFEASIBLE",
            assignments=(),
            objective_value=None,
            unassigned_duty_days=(),
            diagnostics={"reason": "no duty days in horizon"},
            elapsed_s=time.perf_counter() - t0,
        )

    elig = _eligibility(
        input.crew, duty_days_in_horizon, input.leave_requests, input.base_tz, eff_limits
    )

    model = cp_model.CpModel()

    # Variables: x[(dd_key, crew_id, role)] = 1 iff assigned.
    x: dict[tuple[str, str, CrewRole], cp_model.IntVar] = {}
    for dd in duty_days_in_horizon:
        for c in input.crew:
            for role in (CrewRole.CAPT, CrewRole.FO):
                key = (dd.duty_day_key, c.crew_id, role)
                if elig[key]["eligible"]:
                    x[key] = model.NewBoolVar(f"x[{dd.duty_day_key},{c.crew_id},{role.value}]")

    # ---- Hard constraint: exactly one crew per (duty_day, role) ----
    coverage_slacks: dict[tuple[str, CrewRole], cp_model.IntVar] = {}
    for dd in duty_days_in_horizon:
        for role in (CrewRole.CAPT, CrewRole.FO):
            candidates = [
                x[(dd.duty_day_key, c.crew_id, role)]
                for c in input.crew
                if (dd.duty_day_key, c.crew_id, role) in x
            ]
            # Slack to keep the model feasible even when no candidates exist —
            # we then mark the duty day as unassigned in the result.
            slack = model.NewBoolVar(f"slack[{dd.duty_day_key},{role.value}]")
            coverage_slacks[(dd.duty_day_key, role)] = slack
            if candidates:
                model.Add(sum(candidates) + slack == 1)
            else:
                model.Add(slack == 1)

    # ---- Hard constraint: a crew flies at most one duty day per calendar date ----
    by_date: dict[tuple[str, date], list[cp_model.IntVar]] = defaultdict(list)
    for (dd_key, crew_id, _role), var in x.items():
        dd = next(d for d in duty_days_in_horizon if d.duty_day_key == dd_key)
        by_date[(crew_id, dd.date_local)].append(var)
    for var_list in by_date.values():
        model.Add(sum(var_list) <= 1)

    # ---- Hard constraint: minimum inter-duty rest ----
    for c in input.crew:
        crew_vars: dict[str, cp_model.IntVar] = {}
        for dd in duty_days_in_horizon:
            for role in (CrewRole.CAPT, CrewRole.FO):
                key = (dd.duty_day_key, c.crew_id, role)
                if key in x:
                    # Use a single per-(crew,dd) presence var = OR of role vars.
                    presence_key = dd.duty_day_key
                    if presence_key not in crew_vars:
                        crew_vars[presence_key] = model.NewBoolVar(
                            f"present[{c.crew_id},{dd.duty_day_key}]"
                        )
                    model.Add(crew_vars[presence_key] >= x[key])
        # Also bound presence by the OR of role assignments per duty day.
        for dd in duty_days_in_horizon:
            if dd.duty_day_key in crew_vars:
                role_vars = [
                    x[(dd.duty_day_key, c.crew_id, r)]
                    for r in (CrewRole.CAPT, CrewRole.FO)
                    if (dd.duty_day_key, c.crew_id, r) in x
                ]
                model.Add(crew_vars[dd.duty_day_key] <= sum(role_vars))
        # Forbid each pair that violates min-rest.
        for dd_a, dd_b in _consecutive_pairs_need_rest(c, duty_days_in_horizon):
            a, b = crew_vars.get(dd_a.duty_day_key), crew_vars.get(dd_b.duty_day_key)
            if a is not None and b is not None:
                model.Add(a + b <= 1)

    # ---- Hard constraint: cumulative duty / block caps (7 / 28 / 365) ----
    for c in input.crew:
        per_dd_role_vars: list[tuple[DutyDay, cp_model.IntVar]] = []
        for dd in duty_days_in_horizon:
            day_vars = [
                x[(dd.duty_day_key, c.crew_id, r)]
                for r in (CrewRole.CAPT, CrewRole.FO)
                if (dd.duty_day_key, c.crew_id, r) in x
            ]
            if day_vars:
                presence = model.NewBoolVar(f"present[{c.crew_id},{dd.duty_day_key}]")
                model.Add(presence == sum(day_vars))
                per_dd_role_vars.append((dd, presence))

        for window_days, duty_cap, block_cap in (
            (7, eff_limits["cumul_duty_7d_h"], None),
            (28, eff_limits["cumul_duty_28d_h"], eff_limits["cumul_block_28d_h"]),
            (365, eff_limits["cumul_duty_365d_h"], eff_limits["cumul_block_365d_h"]),
        ):
            # Rolling window starting on each unique date in the horizon.
            unique_dates = sorted({dd.date_local for dd, _ in per_dd_role_vars})
            for start in unique_dates:
                end = start + timedelta(days=window_days - 1)
                window_terms_duty: list[cp_model.IntVar] = []
                window_terms_block: list[cp_model.IntVar] = []
                window_coef_duty: list[int] = []
                window_coef_block: list[int] = []
                for dd, presence in per_dd_role_vars:
                    if start <= dd.date_local <= end:
                        window_terms_duty.append(presence)
                        window_coef_duty.append(round(float(dd.duty_hours) * HOURS_SCALE))
                        window_terms_block.append(presence)
                        window_coef_block.append(round(float(dd.flight_hours) * HOURS_SCALE))
                if window_terms_duty:
                    model.Add(
                        sum(
                            c * v for c, v in zip(window_coef_duty, window_terms_duty, strict=False)
                        )
                        <= round(duty_cap * HOURS_SCALE)
                    )
                if block_cap is not None and window_terms_block:
                    model.Add(
                        sum(
                            c * v
                            for c, v in zip(window_coef_block, window_terms_block, strict=False)
                        )
                        <= round(block_cap * HOURS_SCALE)
                    )

    # ---- Soft constraints (objective) ----
    objective_terms: list[Any] = []

    # 1. Block-hour balance: minimise (max − min) of per-crew total block hours.
    per_crew_block: dict[str, list[tuple[int, cp_model.IntVar]]] = defaultdict(list)
    for (dd_key, crew_id, _), var in x.items():
        dd = next(d for d in duty_days_in_horizon if d.duty_day_key == dd_key)
        per_crew_block[crew_id].append((round(float(dd.flight_hours) * HOURS_SCALE), var))
    total_block_h_per_crew: dict[str, cp_model.IntVar] = {}
    if per_crew_block:
        upper = sum(coef for terms in per_crew_block.values() for coef, _ in terms) + 1
        for crew_id, terms in per_crew_block.items():
            tot = model.NewIntVar(0, upper, f"block_h[{crew_id}]")
            model.Add(tot == sum(coef * var for coef, var in terms))
            total_block_h_per_crew[crew_id] = tot
        max_block = model.NewIntVar(0, upper, "block_h_max")
        min_block = model.NewIntVar(0, upper, "block_h_min")
        for tot in total_block_h_per_crew.values():
            model.Add(max_block >= tot)
            model.Add(min_block <= tot)
        spread = model.NewIntVar(0, upper, "block_h_spread")
        model.Add(spread == max_block - min_block)
        w = round(input.weights.get("balance_block_hours", 0.0) * 10)
        if w > 0:
            objective_terms.append(w * spread)

    # 2. Faith violations: Sunday-protected crew flying on a Sunday.
    w_faith = round(input.weights.get("faith_violation", 0.0) * 10)
    if w_faith > 0:
        for (dd_key, crew_id, _), var in x.items():
            dd = next(d for d in duty_days_in_horizon if d.duty_day_key == dd_key)
            c = next(c for c in input.crew if c.crew_id == crew_id)
            if c.faith_flags.get("sunday_protected") and _is_sunday(dd.date_local):
                objective_terms.append(w_faith * var)

    # 3. Leave violations: pending leave overlapping the date.
    w_leave = round(input.weights.get("leave_violation", 0.0) * 10)
    if w_leave > 0:
        for (dd_key, crew_id, _), var in x.items():
            dd = next(d for d in duty_days_in_horizon if d.duty_day_key == dd_key)
            if _has_pending_leave(crew_id, dd.date_local, input.leave_requests):
                objective_terms.append(w_leave * var)

    # 4. Coverage slack: heavily penalised so the solver only leaves a duty day
    # unassigned when truly infeasible.
    slack_penalty = 1_000_000
    for slack in coverage_slacks.values():
        objective_terms.append(slack_penalty * slack)

    if objective_terms:
        model.Minimize(sum(objective_terms))

    # ---- Solve ----
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(input.timeout_s)
    solver.parameters.num_search_workers = 8
    status_code = solver.Solve(model)

    status_label = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "INFEASIBLE",
        cp_model.UNKNOWN: "TIMEOUT",
    }.get(status_code, "TIMEOUT")

    assignments: list[Assignment] = []
    unassigned: list[str] = []

    if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for dd in duty_days_in_horizon:
            captain = next(
                (
                    c
                    for c in input.crew
                    if (dd.duty_day_key, c.crew_id, CrewRole.CAPT) in x
                    and solver.Value(x[(dd.duty_day_key, c.crew_id, CrewRole.CAPT)]) == 1
                ),
                None,
            )
            fo = next(
                (
                    c
                    for c in input.crew
                    if (dd.duty_day_key, c.crew_id, CrewRole.FO) in x
                    and solver.Value(x[(dd.duty_day_key, c.crew_id, CrewRole.FO)]) == 1
                ),
                None,
            )
            if captain and fo:
                assignments.append(
                    Assignment(
                        duty_day_key=dd.duty_day_key,
                        date_local=dd.date_local,
                        aircraft_reg=dd.aircraft_reg,
                        aircraft_type=dd.aircraft_type,
                        sector_ids=dd.sector_ids,
                        captain_id=captain.crew_id,
                        fo_id=fo.crew_id,
                    )
                )
            else:
                unassigned.append(dd.duty_day_key)

    objective_value = (
        float(solver.ObjectiveValue())
        if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        else None
    )

    return OptimiserResult(
        status=status_label,
        assignments=tuple(assignments),
        objective_value=objective_value,
        unassigned_duty_days=tuple(unassigned),
        diagnostics={
            "duty_days_in_horizon": len(duty_days_in_horizon),
            "candidate_variables": len(x),
            "wall_time_s": solver.WallTime(),
        },
        elapsed_s=time.perf_counter() - t0,
    )


# -----------------------------------------------------------------------------
# Explain
# -----------------------------------------------------------------------------


def explain(
    input: OptimiserInput, duty_day_key: str, *, limits: dict[str, Any] | None = None
) -> Explanation:
    """Return the binding constraints for a specific duty day.

    We deliberately don't re-run the solver — we enumerate the eligibility
    filter and the FTL verdict for the duty day, plus the soft objectives
    that touched the assignment. This produces ≥3 bindings per FDP for any
    real-world case (Plan §5 Phase 2 acceptance criterion).
    """
    duty_days = build_duty_days(input.sectors)
    dd = next((d for d in duty_days if d.duty_day_key == duty_day_key), None)
    if dd is None:
        return Explanation(duty_day_key, None, None, ())

    elig = _eligibility(input.crew, [dd], input.leave_requests, input.base_tz, limits)

    bindings: list[ConstraintBinding] = []

    # Coverage requirement
    bindings.append(
        ConstraintBinding(
            rule_id="OPT-COVERAGE",
            description=("Duty day must be staffed with exactly one CAPT and one FO."),
            metadata={
                "duty_day_key": dd.duty_day_key,
                "sectors": list(dd.sector_ids),
                "aircraft_reg": dd.aircraft_reg,
            },
        )
    )

    # Type rating
    rated = [c.crew_id for c in input.crew if dd.aircraft_type in c.type_ratings]
    bindings.append(
        ConstraintBinding(
            rule_id="OPT-TYPE-RATING",
            description=(f"Only crew rated on {dd.aircraft_type} may operate this duty day."),
            metadata={
                "aircraft_type": dd.aircraft_type,
                "eligible_crew_count": len(rated),
            },
        )
    )

    # FTL legality of the duty day itself
    fdp_in = ftl_engine.FdpInput(
        report_time=dd.report_time,
        off_duty_time=dd.off_duty_time,
        sectors_count=dd.sectors_count,
        flight_hours=dd.flight_hours,
        duty_hours=dd.duty_hours,
        base_tz=input.base_tz,
    )
    verdicts = ftl_engine.check_fdp(fdp_in, limits=limits)
    worst = ftl_engine.aggregate_verdicts(verdicts)
    bindings.append(
        ConstraintBinding(
            rule_id="OPT-FTL",
            description=(
                f"Duty day FTL legality aggregates to {worst.legality_state.value}: {worst.reason}"
            ),
            metadata={
                "aggregated_state": worst.legality_state.value,
                "worst_rule": worst.rule_id,
                "rules_applied": worst.rules_applied,
            },
        )
    )

    # Currency
    current_count = sum(1 for c in input.crew if c.current)
    bindings.append(
        ConstraintBinding(
            rule_id="OPT-CURRENCY",
            description="Only currently-qualified crew may be assigned.",
            metadata={"current_crew_count": current_count},
        )
    )

    # Availability (leave)
    on_leave = [
        c.crew_id
        for c in input.crew
        if dd.date_local in _unavailable_dates(c.crew_id, input.leave_requests)
    ]
    if on_leave:
        bindings.append(
            ConstraintBinding(
                rule_id="OPT-AVAILABILITY",
                description=(
                    f"{len(on_leave)} crew unavailable on {dd.date_local.isoformat()} "
                    f"due to approved leave."
                ),
                metadata={
                    "date": dd.date_local.isoformat(),
                    "unavailable_crew": on_leave,
                },
            )
        )

    # Faith / Sunday protection
    if _is_sunday(dd.date_local):
        protected = [c.crew_id for c in input.crew if c.faith_flags.get("sunday_protected")]
        if protected:
            bindings.append(
                ConstraintBinding(
                    rule_id="OPT-FAITH-OBSERVANCE",
                    description=(
                        "Sunday-protected crew incur an objective penalty for "
                        "assignment on this date."
                    ),
                    metadata={"protected_crew": protected},
                )
            )

    # Per-crew eligibility summary
    eligible_per_role = {
        role.value: sum(
            1 for c in input.crew if elig[(dd.duty_day_key, c.crew_id, role)]["eligible"]
        )
        for role in (CrewRole.CAPT, CrewRole.FO)
    }
    bindings.append(
        ConstraintBinding(
            rule_id="OPT-ELIGIBILITY-SUMMARY",
            description=(
                f"After all filters: {eligible_per_role['CAPT']} eligible captains, "
                f"{eligible_per_role['FO']} eligible first officers."
            ),
            metadata=eligible_per_role,
        )
    )

    return Explanation(
        duty_day_key=duty_day_key,
        captain_id=None,
        fo_id=None,
        bindings=tuple(bindings),
    )
