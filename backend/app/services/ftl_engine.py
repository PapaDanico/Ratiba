"""Flight & duty time (FTL) engine for the KCAA Flight Duty Time Scheme.

Kenya's prescriptive flight- and duty-time limits are set out in the KCAA
Flight Duty Time Scheme (Advisory Circular CAA-AC-OPS033, a CAP 371-derived
scheme) made under the Civil Aviation (Operation of Aircraft) Regulations
2025, which implement the fatigue-management framework of ICAO Annex 6,
Part I, 4.10. ICAO permits two routes: prescriptive limits, and an approved
Fatigue Risk Management System (FRMS, ICAO Doc 9966). The
``REQUIRES_FRMS_DEROGATION`` verdict marks duties only acceptable under an
approved FRMS.

Every rule is a pure function returning :class:`FtlVerdict`. The numeric
limits in :data:`LIMITS` are a CAP 371 / EASA Part-ORO-aligned baseline and
must be confirmed against the authoritative CAA-AC-OPS033 tables and the
forthcoming Civil Aviation (Fatigue Management) Regulations 2025 before
operational reliance. Operator-specific overrides load via the ``ftl_rules``
table (keyed by ``rule_id``).

Rule IDs (``KCAR-P8-*``) are stable internal identifiers, not regulatory
section numbers. See ``docs/ftl-rules.md`` for the human-readable rules —
keep that document in lockstep with this module.

Framework-free by design: rules take dataclass inputs and return dataclass
verdicts (no SQLAlchemy / FastAPI), so unit tests stay fast and the
optimiser can call rules at high frequency without DB round-trips.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Any, Final
from zoneinfo import ZoneInfo

from app.models.crew import CrewRole
from app.models.ftl import FdpType, LegalityState

# -----------------------------------------------------------------------------
# Numeric limits — CAP 371 / EASA Part-ORO-aligned baseline for the KCAA
# Flight Duty Time Scheme (CAA-AC-OPS033). Pending confirmation against the
# authoritative scheme tables. Edit these together with docs/ftl-rules.md.
# -----------------------------------------------------------------------------

LIMITS: Final[dict[str, Any]] = {
    # Maximum FDP for a 2-pilot basic crew, by local report time band.
    # Reductions for ≥3 sectors are applied separately.
    "fdp_max_basic_by_band": {
        "WOCL": 11.0,  # 17:00–04:59 local
        "EARLY": 12.0,  # 05:00–05:59
        "DAY_PEAK": 13.0,  # 06:00–13:29
        "AFTERNOON": 12.0,  # 13:30–16:59
    },
    # Each sector above 2 reduces the limit by this many hours, down to floor.
    "fdp_sector_reduction_per_extra": 0.5,
    "fdp_sector_floor": 9.0,
    # Augmented crew extensions over basic limit.
    "fdp_aug_3_pilot": {1: 3.0, 2: 2.0, 3: 1.0},  # class 1 / 2 / 3 facility
    "fdp_aug_4_pilot": {1: 4.0, 2: 3.0, 3: 2.0},
    "fdp_aug_absolute_cap": 18.0,
    # Minimum rest before next FDP.
    "rest_home_floor_h": 12.0,
    "rest_away_floor_h": 10.0,
    "rest_at_limit_window_h": 0.5,  # within 0.5 h of floor → AT_LIMIT
    "rest_derogation_window_h": 1.0,  # 0.5 h below floor → REQUIRES_FRMS_DEROGATION
    # Cumulative duty hours.
    "cumul_duty_7d_h": 60.0,
    "cumul_duty_28d_h": 190.0,
    "cumul_duty_365d_h": 2000.0,
    # Cumulative block (flight) hours.
    "cumul_block_28d_h": 100.0,
    "cumul_block_365d_h": 1000.0,
    # Standby.
    "standby_short_call_max_h": 12.0,
    "standby_long_call_max_h": 24.0,
    # Split duty.
    "split_duty_qualifying_break_h": 3.0,
    "split_duty_extension_factor": 0.5,
    "split_duty_extension_cap_h": 2.0,
    # Time-zone crossing recovery.
    "tz_recovery": {4: 36.0, 6: 48.0, 8: 72.0},
    # Commander's discretion.
    "discretion_max_extension_h": 2.0,
    "discretion_max_rest_reduction_h": 1.0,
    "discretion_repeated_use_90d_threshold": 3,
    # Margin: within this many hours of the limit → AT_LIMIT.
    "at_limit_margin_h": 0.5,
}

REGULATION_REF: Final[str] = (
    "KCAA Flight Duty Time Scheme (CAA-AC-OPS033); ICAO Annex 6 Part I, 4.10"
)

# ContextVar holding the active limits dict for the current check_fdp call.
# Defaults to the module-level baseline so all existing callers work unchanged.
_active_limits: ContextVar[dict[str, Any]] = ContextVar("_active_limits", default=LIMITS)

# State precedence for aggregation (higher index wins).
_STATE_ORDER: Final[tuple[LegalityState, ...]] = (
    LegalityState.LEGAL,
    LegalityState.AT_LIMIT,
    LegalityState.REQUIRES_FRMS_DEROGATION,
    LegalityState.ILLEGAL,
)


# -----------------------------------------------------------------------------
# Inputs and verdicts
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class CrewClassification:
    """How the crew is staffed for this FDP. Drives augmented-crew rules."""

    augmented: bool = False
    pilots_on_flight_deck: int = 2  # 2 = basic, 3 or 4 = augmented
    rest_facility_class: int = 0  # 0=none, 1=full bunk, 2=lie-flat, 3=recliner


@dataclass(frozen=True)
class FdpHistoryEntry:
    """Single past FDP, used by cumulative and rest rules.

    Times are UTC timezone-aware datetimes.
    """

    date_local: str  # ISO date (YYYY-MM-DD) of report (local at base)
    report_time: datetime
    off_duty_time: datetime
    duty_hours: Decimal
    flight_hours: Decimal
    sectors_count: int
    fdp_type: FdpType
    at_home_base: bool
    timezones_crossed: int = 0


@dataclass(frozen=True)
class FdpInput:
    """All facts about an FDP needed by every rule.

    Time fields are timezone-aware UTC datetimes; ``base_tz`` is the IANA
    timezone of the operating base, used to derive local report time for
    band-based rules.
    """

    report_time: datetime
    off_duty_time: datetime
    sectors_count: int
    flight_hours: Decimal
    duty_hours: Decimal
    base_tz: str = "Africa/Nairobi"
    fdp_type: FdpType = FdpType.FDP
    crew_role: CrewRole = CrewRole.CAPT
    crew_classification: CrewClassification = field(default_factory=CrewClassification)
    discretion_extension_h: Decimal = Decimal("0")
    split_duty_break_h: Decimal = Decimal("0")
    timezones_crossed: int = 0
    at_home_base: bool = True
    # Optional context — empty by default for stand-alone validation.
    prior_fdp: FdpHistoryEntry | None = None
    history: tuple[FdpHistoryEntry, ...] = field(default_factory=tuple)
    discretion_uses_last_90d: int = 0
    standby_hours_before_call: Decimal = Decimal("0")
    standby_type: str = "NONE"  # "NONE" | "SHORT_CALL" | "LONG_CALL"

    @property
    def local_report_time(self) -> datetime:
        return self.report_time.astimezone(ZoneInfo(self.base_tz))


@dataclass(frozen=True)
class FtlVerdict:
    """Structured verdict returned by every FTL rule function."""

    legality_state: LegalityState
    rule_id: str
    reason: str
    regulation_ref: str
    rules_applied: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _hours_between(start: datetime, end: datetime) -> float:
    return max(0.0, (end - start).total_seconds() / 3600.0)


def _state_for_overshoot(
    actual_h: float,
    limit_h: float,
    *,
    at_limit_margin_h: float,
    derogation_margin_h: float,
) -> LegalityState:
    """Map (actual, limit) into a legality state with consistent windows.

    - actual < limit − margin                       → LEGAL
    - limit − margin ≤ actual ≤ limit               → AT_LIMIT
    - limit < actual ≤ limit + derogation_margin    → REQUIRES_FRMS_DEROGATION
    - actual > limit + derogation_margin            → ILLEGAL
    """
    if actual_h < limit_h - at_limit_margin_h:
        return LegalityState.LEGAL
    if actual_h <= limit_h:
        return LegalityState.AT_LIMIT
    if actual_h <= limit_h + derogation_margin_h:
        return LegalityState.REQUIRES_FRMS_DEROGATION
    return LegalityState.ILLEGAL


def _state_for_undershoot(
    actual_h: float,
    floor_h: float,
    *,
    at_limit_margin_h: float,
    derogation_margin_h: float,
) -> LegalityState:
    """Symmetric to :func:`_state_for_overshoot` for floors (rest hours)."""
    if actual_h > floor_h + at_limit_margin_h:
        return LegalityState.LEGAL
    if actual_h >= floor_h:
        return LegalityState.AT_LIMIT
    if actual_h >= floor_h - derogation_margin_h:
        return LegalityState.REQUIRES_FRMS_DEROGATION
    return LegalityState.ILLEGAL


def _report_band(local_report: datetime) -> str:
    """Map local report time to a band key in ``LIMITS['fdp_max_basic_by_band']``."""
    t = local_report.time()
    if time(17, 0) <= t or t < time(5, 0):
        return "WOCL"
    if t < time(6, 0):
        return "EARLY"
    if t < time(13, 30):
        return "DAY_PEAK"
    return "AFTERNOON"


# -----------------------------------------------------------------------------
# Rules
# -----------------------------------------------------------------------------


def rule_max_fdp_basic(fdp: FdpInput) -> FtlVerdict:
    """Maximum FDP for basic (2-pilot) crew, by local report band and sectors."""
    rule_id = "KCAR-P8-FDP-MAX-BASIC"
    band = _report_band(fdp.local_report_time)
    base_limit = float(_active_limits.get()["fdp_max_basic_by_band"][band])

    extra_sectors = max(0, fdp.sectors_count - 2)
    reduction = extra_sectors * float(_active_limits.get()["fdp_sector_reduction_per_extra"])
    limit = max(base_limit - reduction, float(_active_limits.get()["fdp_sector_floor"]))

    actual = float(fdp.duty_hours)
    state = _state_for_overshoot(
        actual,
        limit,
        at_limit_margin_h=float(_active_limits.get()["at_limit_margin_h"]),
        derogation_margin_h=float(_active_limits.get()["discretion_max_extension_h"]),
    )

    return FtlVerdict(
        legality_state=state,
        rule_id=rule_id,
        reason=(
            f"basic-crew FDP limit for {band} report and {fdp.sectors_count} sectors "
            f"is {limit:.1f}h; actual duty is {actual:.2f}h"
        ),
        regulation_ref=REGULATION_REF,
        rules_applied=[rule_id],
        metadata={
            "limit_h": limit,
            "actual_h": actual,
            "margin_h": limit - actual,
            "band": band,
            "sectors_count": fdp.sectors_count,
            "base_limit_h": base_limit,
            "sector_reduction_h": reduction,
        },
    )


def rule_max_fdp_augmented(fdp: FdpInput) -> FtlVerdict:
    """Augmented (3- or 4-pilot) crew extension over basic, with rest facility."""
    rule_id = "KCAR-P8-FDP-MAX-AUG"
    cc = fdp.crew_classification

    basic_verdict = rule_max_fdp_basic(fdp)
    basic_limit = float(basic_verdict.metadata["limit_h"])

    if not cc.augmented or cc.pilots_on_flight_deck < 3 or cc.rest_facility_class == 0:
        return FtlVerdict(
            legality_state=LegalityState.LEGAL,
            rule_id=rule_id,
            reason="not augmented or no qualifying rest facility — basic limit applies",
            regulation_ref=REGULATION_REF,
            rules_applied=[rule_id],
            metadata={"applicable": False, "basic_limit_h": basic_limit},
        )

    if cc.pilots_on_flight_deck == 3:
        extension = float(_active_limits.get()["fdp_aug_3_pilot"].get(cc.rest_facility_class, 0.0))
    else:
        extension = float(_active_limits.get()["fdp_aug_4_pilot"].get(cc.rest_facility_class, 0.0))

    limit = min(basic_limit + extension, float(_active_limits.get()["fdp_aug_absolute_cap"]))
    actual = float(fdp.duty_hours)
    state = _state_for_overshoot(
        actual,
        limit,
        at_limit_margin_h=float(_active_limits.get()["at_limit_margin_h"]),
        derogation_margin_h=float(_active_limits.get()["discretion_max_extension_h"]),
    )

    return FtlVerdict(
        legality_state=state,
        rule_id=rule_id,
        reason=(
            f"augmented {cc.pilots_on_flight_deck}-pilot crew with class-"
            f"{cc.rest_facility_class} rest: extended limit {limit:.1f}h; "
            f"actual {actual:.2f}h"
        ),
        regulation_ref=REGULATION_REF,
        rules_applied=[rule_id],
        metadata={
            "applicable": True,
            "limit_h": limit,
            "actual_h": actual,
            "margin_h": limit - actual,
            "basic_limit_h": basic_limit,
            "extension_h": extension,
            "pilots_on_flight_deck": cc.pilots_on_flight_deck,
            "rest_facility_class": cc.rest_facility_class,
        },
    )


def rule_min_rest(fdp: FdpInput) -> FtlVerdict:
    """Minimum rest before this FDP, relative to the prior FDP off-duty time."""
    rule_id = "KCAR-P8-REST-MIN"

    if fdp.prior_fdp is None:
        return FtlVerdict(
            legality_state=LegalityState.LEGAL,
            rule_id=rule_id,
            reason="no prior FDP recorded — rest rule not applicable",
            regulation_ref=REGULATION_REF,
            rules_applied=[rule_id],
            metadata={"applicable": False},
        )

    prior = fdp.prior_fdp
    rest_h = _hours_between(prior.off_duty_time, fdp.report_time)
    preceding_duty_h = float(prior.duty_hours)
    floor_base = float(
        _active_limits.get()["rest_home_floor_h"]
        if fdp.at_home_base
        else _active_limits.get()["rest_away_floor_h"]
    )
    floor = max(floor_base, preceding_duty_h)

    state = _state_for_undershoot(
        rest_h,
        floor,
        at_limit_margin_h=float(_active_limits.get()["rest_at_limit_window_h"]),
        derogation_margin_h=float(_active_limits.get()["rest_derogation_window_h"]),
    )

    location = "home base" if fdp.at_home_base else "away from base"
    return FtlVerdict(
        legality_state=state,
        rule_id=rule_id,
        reason=(
            f"rest at {location}: {rest_h:.2f}h actual against floor {floor:.2f}h "
            f"(prior duty {preceding_duty_h:.2f}h)"
        ),
        regulation_ref=REGULATION_REF,
        rules_applied=[rule_id],
        metadata={
            "actual_rest_h": rest_h,
            "floor_h": floor,
            "preceding_duty_h": preceding_duty_h,
            "at_home_base": fdp.at_home_base,
        },
    )


def _cumulative_duty_in_window(fdp: FdpInput, window_days: int) -> float:
    """Sum duty hours in the trailing window ending at this FDP's report time."""
    start = fdp.report_time - timedelta(days=window_days)
    total = float(fdp.duty_hours)
    for h in fdp.history:
        if start <= h.report_time < fdp.report_time:
            total += float(h.duty_hours)
    return total


def _cumulative_block_in_window(fdp: FdpInput, window_days: int) -> float:
    start = fdp.report_time - timedelta(days=window_days)
    total = float(fdp.flight_hours)
    for h in fdp.history:
        if start <= h.report_time < fdp.report_time:
            total += float(h.flight_hours)
    return total


def _cumulative_verdict(
    actual_h: float, limit_h: float, rule_id: str, window_label: str
) -> FtlVerdict:
    state = _state_for_overshoot(
        actual_h,
        limit_h,
        at_limit_margin_h=float(_active_limits.get()["at_limit_margin_h"]),
        derogation_margin_h=float(_active_limits.get()["discretion_max_extension_h"]),
    )
    return FtlVerdict(
        legality_state=state,
        rule_id=rule_id,
        reason=(f"cumulative {window_label}: {actual_h:.2f}h actual against limit {limit_h:.1f}h"),
        regulation_ref=REGULATION_REF,
        rules_applied=[rule_id],
        metadata={
            "actual_h": actual_h,
            "limit_h": limit_h,
            "margin_h": limit_h - actual_h,
            "window_label": window_label,
        },
    )


def rule_cumulative_duty_7d(fdp: FdpInput) -> FtlVerdict:
    return _cumulative_verdict(
        _cumulative_duty_in_window(fdp, 7),
        float(_active_limits.get()["cumul_duty_7d_h"]),
        "KCAR-P8-CUMUL-DUTY-7D",
        "duty hours in trailing 7 days",
    )


def rule_cumulative_duty_28d(fdp: FdpInput) -> FtlVerdict:
    return _cumulative_verdict(
        _cumulative_duty_in_window(fdp, 28),
        float(_active_limits.get()["cumul_duty_28d_h"]),
        "KCAR-P8-CUMUL-DUTY-28D",
        "duty hours in trailing 28 days",
    )


def rule_cumulative_duty_365d(fdp: FdpInput) -> FtlVerdict:
    return _cumulative_verdict(
        _cumulative_duty_in_window(fdp, 365),
        float(_active_limits.get()["cumul_duty_365d_h"]),
        "KCAR-P8-CUMUL-DUTY-365D",
        "duty hours in trailing 365 days",
    )


def rule_cumulative_block_28d(fdp: FdpInput) -> FtlVerdict:
    return _cumulative_verdict(
        _cumulative_block_in_window(fdp, 28),
        float(_active_limits.get()["cumul_block_28d_h"]),
        "KCAR-P8-CUMUL-BLOCK-28D",
        "block hours in trailing 28 days",
    )


def rule_cumulative_block_365d(fdp: FdpInput) -> FtlVerdict:
    return _cumulative_verdict(
        _cumulative_block_in_window(fdp, 365),
        float(_active_limits.get()["cumul_block_365d_h"]),
        "KCAR-P8-CUMUL-BLOCK-365D",
        "block hours in trailing 365 days",
    )


def rule_standby_short_call(fdp: FdpInput) -> FtlVerdict:
    """Short-call standby: standby time counts toward FDP if called out."""
    rule_id = "KCAR-P8-STANDBY-SHORT-CALL"
    if fdp.standby_type != "SHORT_CALL":
        return FtlVerdict(
            legality_state=LegalityState.LEGAL,
            rule_id=rule_id,
            reason="not on short-call standby",
            regulation_ref=REGULATION_REF,
            rules_applied=[rule_id],
            metadata={"applicable": False},
        )

    standby_h = float(fdp.standby_hours_before_call)
    standby_limit = float(_active_limits.get()["standby_short_call_max_h"])
    if standby_h > standby_limit:
        return FtlVerdict(
            legality_state=LegalityState.ILLEGAL,
            rule_id=rule_id,
            reason=(
                f"short-call standby duration {standby_h:.2f}h exceeds maximum {standby_limit:.1f}h"
            ),
            regulation_ref=REGULATION_REF,
            rules_applied=[rule_id],
            metadata={
                "standby_h": standby_h,
                "standby_limit_h": standby_limit,
            },
        )

    # When called out, standby + duty must respect basic FDP limit.
    basic = rule_max_fdp_basic(fdp)
    basic_limit = float(basic.metadata["limit_h"])
    combined = standby_h + float(fdp.duty_hours)
    state = _state_for_overshoot(
        combined,
        basic_limit,
        at_limit_margin_h=float(_active_limits.get()["at_limit_margin_h"]),
        derogation_margin_h=float(_active_limits.get()["discretion_max_extension_h"]),
    )
    return FtlVerdict(
        legality_state=state,
        rule_id=rule_id,
        reason=(
            f"short-call standby {standby_h:.2f}h + duty {float(fdp.duty_hours):.2f}h "
            f"= {combined:.2f}h against FDP limit {basic_limit:.1f}h"
        ),
        regulation_ref=REGULATION_REF,
        rules_applied=[rule_id],
        metadata={
            "standby_h": standby_h,
            "duty_h": float(fdp.duty_hours),
            "combined_h": combined,
            "fdp_limit_h": basic_limit,
        },
    )


def rule_standby_long_call(fdp: FdpInput) -> FtlVerdict:
    """Long-call standby: only the called-out FDP counts toward duty."""
    rule_id = "KCAR-P8-STANDBY-LONG-CALL"
    if fdp.standby_type != "LONG_CALL":
        return FtlVerdict(
            legality_state=LegalityState.LEGAL,
            rule_id=rule_id,
            reason="not on long-call standby",
            regulation_ref=REGULATION_REF,
            rules_applied=[rule_id],
            metadata={"applicable": False},
        )

    standby_h = float(fdp.standby_hours_before_call)
    standby_limit = float(_active_limits.get()["standby_long_call_max_h"])
    state = _state_for_overshoot(
        standby_h,
        standby_limit,
        at_limit_margin_h=float(_active_limits.get()["at_limit_margin_h"]),
        derogation_margin_h=float(_active_limits.get()["discretion_max_extension_h"]),
    )
    return FtlVerdict(
        legality_state=state,
        rule_id=rule_id,
        reason=(f"long-call standby {standby_h:.2f}h against maximum {standby_limit:.1f}h"),
        regulation_ref=REGULATION_REF,
        rules_applied=[rule_id],
        metadata={
            "standby_h": standby_h,
            "standby_limit_h": standby_limit,
        },
    )


def rule_split_duty(fdp: FdpInput) -> FtlVerdict:
    """A qualifying break extends the maximum FDP by up to a cap."""
    rule_id = "KCAR-P8-SPLIT-DUTY"
    break_h = float(fdp.split_duty_break_h)
    threshold = float(_active_limits.get()["split_duty_qualifying_break_h"])

    if break_h < threshold:
        return FtlVerdict(
            legality_state=LegalityState.LEGAL,
            rule_id=rule_id,
            reason=(
                f"break {break_h:.2f}h below qualifying threshold {threshold:.1f}h — no extension"
            ),
            regulation_ref=REGULATION_REF,
            rules_applied=[rule_id],
            metadata={"applicable": False, "break_h": break_h},
        )

    extension = min(
        break_h * float(_active_limits.get()["split_duty_extension_factor"]),
        float(_active_limits.get()["split_duty_extension_cap_h"]),
    )
    basic = rule_max_fdp_basic(fdp)
    basic_limit = float(basic.metadata["limit_h"])
    effective_limit = basic_limit + extension
    actual = float(fdp.duty_hours)
    state = _state_for_overshoot(
        actual,
        effective_limit,
        at_limit_margin_h=float(_active_limits.get()["at_limit_margin_h"]),
        derogation_margin_h=float(_active_limits.get()["discretion_max_extension_h"]),
    )

    return FtlVerdict(
        legality_state=state,
        rule_id=rule_id,
        reason=(
            f"qualifying break {break_h:.2f}h extends FDP by {extension:.2f}h "
            f"to {effective_limit:.2f}h; actual {actual:.2f}h"
        ),
        regulation_ref=REGULATION_REF,
        rules_applied=[rule_id],
        metadata={
            "applicable": True,
            "break_h": break_h,
            "extension_h": extension,
            "basic_limit_h": basic_limit,
            "effective_limit_h": effective_limit,
            "actual_h": actual,
        },
    )


def rule_timezone_recovery(fdp: FdpInput) -> FtlVerdict:
    """After a long time-zone-crossing FDP, the next FDP needs extra rest."""
    rule_id = "KCAR-P8-TZ-RECOVERY"
    if fdp.prior_fdp is None or fdp.prior_fdp.timezones_crossed < 4:
        return FtlVerdict(
            legality_state=LegalityState.LEGAL,
            rule_id=rule_id,
            reason="no qualifying time-zone-crossing prior FDP",
            regulation_ref=REGULATION_REF,
            rules_applied=[rule_id],
            metadata={"applicable": False},
        )

    zones = fdp.prior_fdp.timezones_crossed
    floor = float(_active_limits.get()["tz_recovery"][4])
    if zones >= 8:
        floor = float(_active_limits.get()["tz_recovery"][8])
    elif zones >= 6:
        floor = float(_active_limits.get()["tz_recovery"][6])

    rest_h = _hours_between(fdp.prior_fdp.off_duty_time, fdp.report_time)
    state = _state_for_undershoot(
        rest_h,
        floor,
        at_limit_margin_h=float(_active_limits.get()["rest_at_limit_window_h"]),
        derogation_margin_h=float(_active_limits.get()["rest_derogation_window_h"]),
    )
    return FtlVerdict(
        legality_state=state,
        rule_id=rule_id,
        reason=(
            f"prior FDP crossed {zones} time zones; recovery rest "
            f"{rest_h:.2f}h against floor {floor:.1f}h"
        ),
        regulation_ref=REGULATION_REF,
        rules_applied=[rule_id],
        metadata={
            "zones_crossed": zones,
            "actual_rest_h": rest_h,
            "floor_h": floor,
        },
    )


def rule_discretion(fdp: FdpInput) -> FtlVerdict:
    """Commander's discretion: bounded extension, with audit trail."""
    rule_id = "KCAR-P8-DISCRETION"
    extension = float(fdp.discretion_extension_h)
    cap = float(_active_limits.get()["discretion_max_extension_h"])

    if extension <= 0:
        # Repeated-use check still applies — if many recent uses, flag.
        if fdp.discretion_uses_last_90d >= int(
            _active_limits.get()["discretion_repeated_use_90d_threshold"]
        ):
            return FtlVerdict(
                legality_state=LegalityState.AT_LIMIT,
                rule_id=rule_id,
                reason=(
                    f"commander has used discretion "
                    f"{fdp.discretion_uses_last_90d} times in last 90 days — "
                    f"review required"
                ),
                regulation_ref=REGULATION_REF,
                rules_applied=[rule_id],
                metadata={
                    "extension_h": 0.0,
                    "uses_last_90d": fdp.discretion_uses_last_90d,
                    "repeated_use_threshold": int(
                        _active_limits.get()["discretion_repeated_use_90d_threshold"]
                    ),
                },
            )
        return FtlVerdict(
            legality_state=LegalityState.LEGAL,
            rule_id=rule_id,
            reason="no commander's discretion applied",
            regulation_ref=REGULATION_REF,
            rules_applied=[rule_id],
            metadata={"extension_h": 0.0, "uses_last_90d": fdp.discretion_uses_last_90d},
        )

    if extension > cap:
        return FtlVerdict(
            legality_state=LegalityState.ILLEGAL,
            rule_id=rule_id,
            reason=(
                f"discretion extension {extension:.2f}h exceeds maximum {cap:.1f}h — not permitted"
            ),
            regulation_ref=REGULATION_REF,
            rules_applied=[rule_id],
            metadata={"extension_h": extension, "max_extension_h": cap},
        )

    state = LegalityState.REQUIRES_FRMS_DEROGATION
    if fdp.discretion_uses_last_90d >= int(
        _active_limits.get()["discretion_repeated_use_90d_threshold"]
    ):
        state = LegalityState.AT_LIMIT if state == LegalityState.LEGAL else state

    return FtlVerdict(
        legality_state=state,
        rule_id=rule_id,
        reason=(
            f"commander's discretion of {extension:.2f}h applied (cap "
            f"{cap:.1f}h); 90-day uses {fdp.discretion_uses_last_90d}"
        ),
        regulation_ref=REGULATION_REF,
        rules_applied=[rule_id],
        metadata={
            "extension_h": extension,
            "max_extension_h": cap,
            "uses_last_90d": fdp.discretion_uses_last_90d,
        },
    )


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------


_ALL_RULES: Final[tuple[Any, ...]] = (
    rule_max_fdp_basic,
    rule_max_fdp_augmented,
    rule_min_rest,
    rule_cumulative_duty_7d,
    rule_cumulative_duty_28d,
    rule_cumulative_duty_365d,
    rule_cumulative_block_28d,
    rule_cumulative_block_365d,
    rule_standby_short_call,
    rule_standby_long_call,
    rule_split_duty,
    rule_timezone_recovery,
    rule_discretion,
)


def check_fdp(fdp: FdpInput, *, limits: dict[str, Any] | None = None) -> list[FtlVerdict]:
    """Run every applicable rule against ``fdp`` and return individual verdicts.

    Pass ``limits`` to override the module-level baseline for this call only
    (operator-specific constraint sets resolved via ``ftl_limits.resolve_limits``).
    The list order is stable across runs so audit packs can rely on it.
    """
    token = _active_limits.set(limits if limits is not None else LIMITS)
    try:
        return [rule(fdp) for rule in _ALL_RULES]
    finally:
        _active_limits.reset(token)


def aggregate_verdicts(verdicts: list[FtlVerdict]) -> FtlVerdict:
    """Reduce per-rule verdicts to a single FDP-level verdict.

    Aggregation rule: worst legality state wins. The aggregated verdict's
    ``rule_id`` is the worst-state rule's ID, and ``rules_applied`` is the
    union of every input rule.
    """
    if not verdicts:
        raise ValueError("aggregate_verdicts requires at least one verdict")

    worst = max(verdicts, key=lambda v: _STATE_ORDER.index(v.legality_state))
    all_rules = [rule_id for v in verdicts for rule_id in v.rules_applied]
    return FtlVerdict(
        legality_state=worst.legality_state,
        rule_id=worst.rule_id,
        reason=worst.reason,
        regulation_ref=worst.regulation_ref,
        rules_applied=all_rules,
        metadata={"per_rule": [v.metadata for v in verdicts]},
    )


def validate_fdp(fdp: FdpInput) -> tuple[FtlVerdict, list[FtlVerdict]]:
    """Convenience: return both the aggregated verdict and the full rule trace."""
    verdicts = check_fdp(fdp)
    return aggregate_verdicts(verdicts), verdicts


def all_rule_ids() -> list[str]:
    """Stable list of every rule ID this engine evaluates.

    Used by the audit pack methodology page and by the rule-coverage test.
    """
    return [
        "KCAR-P8-FDP-MAX-BASIC",
        "KCAR-P8-FDP-MAX-AUG",
        "KCAR-P8-REST-MIN",
        "KCAR-P8-CUMUL-DUTY-7D",
        "KCAR-P8-CUMUL-DUTY-28D",
        "KCAR-P8-CUMUL-DUTY-365D",
        "KCAR-P8-CUMUL-BLOCK-28D",
        "KCAR-P8-CUMUL-BLOCK-365D",
        "KCAR-P8-STANDBY-SHORT-CALL",
        "KCAR-P8-STANDBY-LONG-CALL",
        "KCAR-P8-SPLIT-DUTY",
        "KCAR-P8-TZ-RECOVERY",
        "KCAR-P8-DISCRETION",
    ]
