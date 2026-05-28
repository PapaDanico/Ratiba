"""Training schemas: type ratings and the unified recurrency view."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TypeRatingIn(BaseModel):
    aircraft_type: str = Field(min_length=2, max_length=32)
    valid_from: date
    valid_until: date
    evidence_ref: str | None = Field(default=None, max_length=512)


class TypeRatingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    crew_id: uuid.UUID
    employee_no: str
    crew_name: str
    aircraft_type: str
    valid_from: date
    valid_until: date
    evidence_ref: str | None
    days_remaining: int
    state: str  # GREEN | AMBER | RED


class RecurrencyItem(BaseModel):
    """One trackable item (currency or type rating) and how close it is to lapse."""

    crew_id: uuid.UUID
    employee_no: str
    crew_name: str
    kind: str  # currency | type_rating
    label: str  # e.g. "OPC" or "Type rating: C208"
    expires_date: date
    days_remaining: int
    state: str  # GREEN | AMBER | RED
