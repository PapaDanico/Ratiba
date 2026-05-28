"""Non-flight duty (standby / off-day) schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel


class DutyIn(BaseModel):
    crew_id: uuid.UUID
    date: date
    duty_type: Literal["STANDBY_SHORT", "STANDBY_LONG", "OFF"]
    start_time: time | None = None  # UTC time-of-day; required for standby
    end_time: time | None = None  # UTC time-of-day; required for standby


class DutyOut(BaseModel):
    id: uuid.UUID
    crew_id: uuid.UUID
    employee_no: str
    crew_name: str
    date: date
    type: str  # STANDBY | OFF | …
    start: datetime
    end: datetime
    duration_h: float
    legality_state: str | None
