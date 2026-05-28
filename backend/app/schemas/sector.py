"""Flight routing (sector) schemas.

A "routing" in operator parlance is a scheduled flight leg: a flight
number flying origin → destination on a date, with scheduled
times-of-departure/arrival held in UTC. These rows are the raw schedule
the auto-roster assigns crew to.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

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


class RecurringSectorIn(BaseModel):
    """Generate one routing per matching date in [date_from, date_to].

    Times are wall-clock UTC times-of-day applied to each generated date.
    If sta_time is at or before std_time the arrival rolls to the next day
    (overnight sector). ``days_of_week`` uses 0=Mon … 6=Sun; an empty list
    means every day in the range.
    """

    flight_no: str = Field(min_length=1, max_length=16)
    origin: str = Field(min_length=3, max_length=8)
    destination: str = Field(min_length=3, max_length=8)
    std_time: time  # UTC time-of-day, e.g. "08:00"
    sta_time: time  # UTC time-of-day, e.g. "10:00"
    aircraft_reg: str = Field(min_length=1, max_length=16)
    aircraft_type: str = Field(min_length=2, max_length=32)
    date_from: date
    date_to: date
    days_of_week: list[int] = Field(default_factory=list)

    @field_validator("origin", "destination", "aircraft_reg", "aircraft_type", "flight_no")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("days_of_week")
    @classmethod
    def _valid_weekdays(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("days_of_week entries must be 0 (Mon) … 6 (Sun)")
        return sorted(set(v))


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


class RecurringSectorResult(BaseModel):
    created: int
    skipped_existing: int
    sectors: list[SectorOut]
