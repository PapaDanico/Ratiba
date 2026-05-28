"""API schemas for the roster endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.crew import CrewRole


class CrewProfileIn(BaseModel):
    crew_id: str
    role: CrewRole
    type_ratings: list[str] = Field(default_factory=list)
    current: bool = True
    base_tz: str = "Africa/Nairobi"
    faith_flags: dict[str, bool] = Field(default_factory=dict)


class SectorInputIn(BaseModel):
    sector_id: str
    date_local: date
    std: datetime
    sta: datetime
    aircraft_reg: str
    aircraft_type: str
    block_hours: Decimal = Field(ge=0, le=24)


class LeaveRequestIn(BaseModel):
    crew_id: str
    date_from: date
    date_to: date
    status: Literal["PENDING", "APPROVED", "REJECTED"] = "PENDING"


class GenerateRosterRequest(BaseModel):
    horizon_from: date
    horizon_to: date
    crew: list[CrewProfileIn] = Field(min_length=1)
    sectors: list[SectorInputIn] = Field(min_length=1)
    leave_requests: list[LeaveRequestIn] = Field(default_factory=list)
    base_tz: str = "Africa/Nairobi"
    weights: dict[str, float] = Field(default_factory=dict)
    timeout_s: float = Field(default=60.0, gt=0, le=600)


class GenerateRosterAcceptedResponse(BaseModel):
    job_id: str
    status: str  # QUEUED | RUNNING | FINISHED | FAILED


class AssignmentOut(BaseModel):
    duty_day_key: str
    date_local: date
    aircraft_reg: str
    aircraft_type: str
    sector_ids: list[str]
    captain_id: str
    fo_id: str


class RosterResult(BaseModel):
    status: str
    assignments: list[AssignmentOut]
    objective_value: float | None
    unassigned_duty_days: list[str]
    diagnostics: dict[str, Any]
    elapsed_s: float


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: RosterResult | None = None
    error: str | None = None


class ExplainRequest(BaseModel):
    """Re-supplies the optimiser input so /explain is self-contained.

    Phase 3 introduces persistence; until then the dashboard sends the same
    payload it submitted to /generate plus the duty_day_key it wants
    explained.
    """

    duty_day_key: str
    input: GenerateRosterRequest


class ConstraintBindingOut(BaseModel):
    rule_id: str
    description: str
    metadata: dict[str, Any]


class ExplainResponse(BaseModel):
    duty_day_key: str
    captain_id: str | None = None
    fo_id: str | None = None
    bindings: list[ConstraintBindingOut]
