"""IROP (irregular operations) assessment schemas."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class IropAssessIn(BaseModel):
    crew_id: uuid.UUID
    date: date
    extra_flight_h: Decimal = Field(default=Decimal("0"), ge=0, le=12)
    extra_ground_h: Decimal = Field(default=Decimal("0"), ge=0, le=24)
    discretion_h: Decimal = Field(default=Decimal("0"), ge=0, le=4)


class IropAlternativesIn(BaseModel):
    date: date
    role: str  # CAPT | FO | ...
    aircraft_type: str
    exclude_crew_id: uuid.UUID | None = None


class AltCrewOut(BaseModel):
    crew_id: uuid.UUID
    employee_no: str
    name: str
    role: str
    type_rated: bool
    landings_current: bool
    free: bool
    available: bool


class CascadeImpactOut(BaseModel):
    next_date: date | None
    new_rest_h: float | None
    rest_floor_h: float | None
    breached: bool


class IropAssessmentOut(BaseModel):
    crew_employee_no: str
    date: date
    away_from_base: bool
    original_flight_h: float
    original_duty_h: float
    original_legality: str
    disrupted_flight_h: float
    disrupted_duty_h: float
    disrupted_legality: str
    rules_breached: list[str]
    cascade: CascadeImpactOut
