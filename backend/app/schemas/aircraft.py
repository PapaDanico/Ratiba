"""Aircraft fleet-registry schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class AircraftIn(BaseModel):
    registration: str = Field(min_length=2, max_length=16)
    aircraft_type: str = Field(min_length=2, max_length=32)
    active: bool = True


class AircraftPatch(BaseModel):
    aircraft_type: str | None = Field(default=None, max_length=32)
    active: bool | None = None


class AircraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    registration: str
    aircraft_type: str
    active: bool
    aircraft_type_known: bool = False  # set by the endpoint against the reference list
