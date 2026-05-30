"""FTL validation endpoints — Phase 1.

These endpoints are read-style: they evaluate FDPs against the KCAA Flight
Duty Time Scheme (CAA-AC-OPS033) rules without writing to the database.
Phase 2's optimiser calls
``app.services.ftl_engine.check_fdp`` directly; this surface exists for
clients (dashboard, bot) that need a structured legality verdict.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User
from app.models.constraint import ConstraintSet, ConstraintSetStatus
from app.schemas.ftl import (
    CheckRosterSliceRequest,
    CheckRosterSliceResponse,
    FdpHistoryEntryIn,
    FdpInputIn,
    FtlVerdictOut,
    ValidateFdpResponse,
)
from app.services import ftl_engine, ftl_limits

router = APIRouter()


@router.get("/limits", summary="The FTL limits currently in force for this operator")
def current_limits(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    """Read-only view of the limits the engine is enforcing for this operator.

    Returns the operator's *resolved* scheme (their accepted OM-A overrides
    merged over the generic baseline) and whether it's the generic baseline
    or operator-specific.
    """
    has_scheme = (
        session.scalar(
            select(ConstraintSet.id)
            .where(ConstraintSet.operator_id == user.operator_id)
            .where(ConstraintSet.status == ConstraintSetStatus.ACCEPTED)
            .limit(1)
        )
        is not None
    )
    return {
        "source": "operator" if has_scheme else "baseline",
        "regulation_ref": ftl_engine.REGULATION_REF,
        "limits": ftl_limits.resolve_limits(user.operator_id, session),
    }


def _history_in_to_engine(h: FdpHistoryEntryIn) -> ftl_engine.FdpHistoryEntry:
    return ftl_engine.FdpHistoryEntry(
        date_local=h.date_local,
        report_time=h.report_time,
        off_duty_time=h.off_duty_time,
        duty_hours=h.duty_hours,
        flight_hours=h.flight_hours,
        sectors_count=h.sectors_count,
        fdp_type=h.fdp_type,
        at_home_base=h.at_home_base,
        timezones_crossed=h.timezones_crossed,
    )


def _to_engine(payload: FdpInputIn) -> ftl_engine.FdpInput:
    cc = ftl_engine.CrewClassification(
        augmented=payload.crew_classification.augmented,
        pilots_on_flight_deck=payload.crew_classification.pilots_on_flight_deck,
        rest_facility_class=payload.crew_classification.rest_facility_class,
    )
    return ftl_engine.FdpInput(
        report_time=payload.report_time,
        off_duty_time=payload.off_duty_time,
        sectors_count=payload.sectors_count,
        flight_hours=payload.flight_hours,
        duty_hours=payload.duty_hours,
        base_tz=payload.base_tz,
        fdp_type=payload.fdp_type,
        crew_role=payload.crew_role,
        crew_classification=cc,
        discretion_extension_h=payload.discretion_extension_h,
        split_duty_break_h=payload.split_duty_break_h,
        timezones_crossed=payload.timezones_crossed,
        at_home_base=payload.at_home_base,
        prior_fdp=_history_in_to_engine(payload.prior_fdp) if payload.prior_fdp else None,
        history=tuple(_history_in_to_engine(h) for h in payload.history),
        discretion_uses_last_90d=payload.discretion_uses_last_90d,
        standby_hours_before_call=payload.standby_hours_before_call,
        standby_type=payload.standby_type,
        reserve_sleep_opportunity_h=payload.reserve_sleep_opportunity_h,
    )


def _verdict_to_out(v: ftl_engine.FtlVerdict) -> FtlVerdictOut:
    return FtlVerdictOut(
        legality_state=v.legality_state,
        rule_id=v.rule_id,
        reason=v.reason,
        regulation_ref=v.regulation_ref,
        rules_applied=v.rules_applied,
        metadata=v.metadata,
    )


@router.post(
    "/validate-fdp",
    response_model=ValidateFdpResponse,
    summary="Validate a single FDP against the KCAA Flight Duty Time Scheme",
)
async def validate_fdp(payload: FdpInputIn) -> ValidateFdpResponse:
    aggregated, trace = ftl_engine.validate_fdp(_to_engine(payload))
    return ValidateFdpResponse(
        aggregated=_verdict_to_out(aggregated),
        rule_trace=[_verdict_to_out(v) for v in trace],
    )


@router.post(
    "/check",
    response_model=CheckRosterSliceResponse,
    summary="Validate a roster slice (many FDPs) and return one verdict per FDP",
)
async def check_roster_slice(
    payload: CheckRosterSliceRequest,
) -> CheckRosterSliceResponse:
    out: dict[str, FtlVerdictOut] = {}
    for ref, fdp_in in payload.fdps.items():
        aggregated, _ = ftl_engine.validate_fdp(_to_engine(fdp_in))
        out[ref] = _verdict_to_out(aggregated)
    return CheckRosterSliceResponse(verdicts=out)
