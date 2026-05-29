"""Outstation / ACMI posting schemas."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.crew import CrewCategory, CrewRole
from app.models.posting import PostingType


class PostingIn(BaseModel):
    location_icao: str
    country: str
    type: PostingType
    start_date: date
    end_date: date
    base_tz: str = "Africa/Nairobi"
    lessee_name: str | None = None
    notes: str | None = None


class PostingAssignIn(BaseModel):
    crew_id: uuid.UUID


class PostingCrewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_no: str
    first_name: str
    last_name: str
    role: CrewRole
    crew_category: CrewCategory


class PostingOut(BaseModel):
    id: uuid.UUID
    location_icao: str
    country: str
    base_tz: str
    type: PostingType
    lessee_name: str | None
    start_date: date
    end_date: date
    duration_days: int
    notes: str | None
    crew: list[PostingCrewOut]
    engineer_cover: bool  # at least one engineer on the team
