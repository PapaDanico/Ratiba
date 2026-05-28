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
    # Populated when persisted FlightDutyPeriod rows are available for the
    # date (i.e. after ``publish_roster`` or ``amend_roster``). Empty in
    # raw optimiser output where no DB lookup has happened yet.
    legality_state: str | None = None


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


# -- Persistence (publish / amend) --------------------------------------------


class PublishRosterRequest(BaseModel):
    """Persist an optimiser result as a published roster.

    Carries the sectors + assignments produced by the optimiser so that the
    backend can build the FlightDutyPeriod and SectorAssignment rows
    transactionally with an audit_event.
    """

    horizon_from: date
    horizon_to: date
    sectors: list[SectorInputIn] = Field(min_length=1)
    assignments: list[AssignmentOut] = Field(min_length=1)


class PublishRosterResponse(BaseModel):
    roster_version: int
    sector_assignments_created: int
    flight_duty_periods_created: int


class AmendRosterRequest(BaseModel):
    """Post-publication amendment. Replaces a single duty day's crew.

    Both new crew slots are required so the caller commits to a complete
    state. The dashboard's amend modal pre-fills these from the existing
    assignment.
    """

    duty_day_key: str
    new_captain_employee_no: str
    new_fo_employee_no: str
    reason: str = Field(min_length=1, max_length=512)


class AmendRosterResponse(BaseModel):
    duty_day_key: str
    captain_id: str
    fo_id: str
    legality_state: str
