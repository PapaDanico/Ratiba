"""Flight routing (sector) schemas.

A "routing" in operator parlance is a scheduled flight leg: a flight
number flying origin → destination on a date, with scheduled
times-of-departure/arrival held in UTC. These rows are the raw schedule
the auto-roster assigns crew to.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SectorIn(BaseModel):
    flight_no: str = Field(min_length=1, max_length=16)
    date: date
    origin: str = Field(min_length=3, max_length=8)
    destination: str = Field(min_length=3, max_length=8)
    std: datetime  # scheduled time of departure (UTC)
    sta: datetime  # scheduled time of arrival (UTC)
    aircraft_reg: str = Field(min_length=1, max_length=16)
    aircraft_type: str = Field(min_length=2, max_length=32)

    @field_validator("origin", "destination", "aircraft_reg", "aircraft_type", "flight_no")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()


class SectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    flight_no: str
    date: date
    origin: str
    destination: str
    std: datetime
    sta: datetime
    aircraft_reg: str
    aircraft_type: str
    status: str
    block_hours: float
