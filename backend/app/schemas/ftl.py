"""API schemas for the FTL endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.crew import CrewRole
from app.models.ftl import FdpType, LegalityState


class CrewClassificationIn(BaseModel):
    augmented: bool = False
    pilots_on_flight_deck: int = Field(default=2, ge=2, le=4)
    rest_facility_class: int = Field(default=0, ge=0, le=3)


class FdpHistoryEntryIn(BaseModel):
    date_local: str
    report_time: datetime
    off_duty_time: datetime
    duty_hours: Decimal = Field(ge=0, le=24)
    flight_hours: Decimal = Field(ge=0, le=24)
    sectors_count: int = Field(ge=0)
    fdp_type: FdpType = FdpType.FDP
    at_home_base: bool = True
    timezones_crossed: int = Field(default=0, ge=0)


class FdpInputIn(BaseModel):
    """Single FDP for `/ftl/validate-fdp`.

    All times must be timezone-aware ISO 8601. The engine converts to local
    time at ``base_tz`` (IANA name) for the report-band rules.
    """

    report_time: datetime
    off_duty_time: datetime
    sectors_count: int = Field(ge=0)
    flight_hours: Decimal = Field(ge=0, le=24)
    duty_hours: Decimal = Field(ge=0, le=24)
    base_tz: str = "Africa/Nairobi"
    fdp_type: FdpType = FdpType.FDP
    crew_role: CrewRole = CrewRole.CAPT
    crew_classification: CrewClassificationIn = Field(default_factory=CrewClassificationIn)
    discretion_extension_h: Decimal = Field(default=Decimal("0"), ge=0, le=4)
    split_duty_break_h: Decimal = Field(default=Decimal("0"), ge=0, le=24)
    timezones_crossed: int = Field(default=0, ge=0)
    at_home_base: bool = True
    prior_fdp: FdpHistoryEntryIn | None = None
    history: list[FdpHistoryEntryIn] = Field(default_factory=list)
    discretion_uses_last_90d: int = Field(default=0, ge=0)
    standby_hours_before_call: Decimal = Field(default=Decimal("0"), ge=0, le=24)
    standby_type: Literal["NONE", "SHORT_CALL", "LONG_CALL"] = "NONE"
    # Protected sleep opportunity (h) in the 24 h before a reserve call-out
    # (CAA-AC-OPS033 §4.6.8). Defaults to a clearly-compliant value.
    reserve_sleep_opportunity_h: Decimal = Field(default=Decimal("10"), ge=0, le=24)


class FtlVerdictOut(BaseModel):
    legality_state: LegalityState
    rule_id: str
    reason: str
    regulation_ref: str
    rules_applied: list[str]
    metadata: dict[str, Any]


class ValidateFdpResponse(BaseModel):
    """Result of `/ftl/validate-fdp`."""

    aggregated: FtlVerdictOut
    rule_trace: list[FtlVerdictOut]


class CheckRosterSliceRequest(BaseModel):
    """Roster slice for `/ftl/check`. Each entry is an FDP keyed by client ref."""

    fdps: dict[str, FdpInputIn] = Field(min_length=1)


class CheckRosterSliceResponse(BaseModel):
    """Per-FDP aggregated verdict; clients can drill in via `/ftl/validate-fdp`."""

    verdicts: dict[str, FtlVerdictOut]
