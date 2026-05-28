"""Schemas for the pilot-facing surface (/auth/pilot-pair, /crew/me/*)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.crew import CrewRole
from app.models.ftl import LegalityState
from app.models.leave import LeaveType


class IssuePairingResponse(BaseModel):
    code: str
    expires_at: datetime


class PilotPairRequest(BaseModel):
    code: str = Field(min_length=4, max_length=16)
    telegram_chat_id: int | None = None


class PilotPairResponse(BaseModel):
    pilot_token: str
    crew_id: uuid.UUID
    employee_no: str
    role: CrewRole
    operator_id: uuid.UUID


class PilotProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_no: str
    first_name: str
    last_name: str
    role: CrewRole
    base_station: str


class PilotDutyDay(BaseModel):
    date_local: date
    aircraft_reg: str
    aircraft_type: str
    sector_ids: list[str]
    role_on_duty: str  # CAPT | FO
    report_time: datetime | None
    off_duty_time: datetime | None
    flight_hours: Decimal | None
    duty_hours: Decimal | None
    legality_state: LegalityState | None


class PilotRosterResponse(BaseModel):
    date_from: date
    date_to: date
    duty_days: list[PilotDutyDay]


class PilotDutyTodayResponse(BaseModel):
    has_duty: bool
    duty_day: PilotDutyDay | None = None


class PilotCurrencyOut(BaseModel):
    currency_type: str
    expires_date: date
    days_remaining: int
    state: str  # GREEN | AMBER | RED


class PilotCurrencyResponse(BaseModel):
    currencies: list[PilotCurrencyOut]


class PilotLeaveRequestIn(BaseModel):
    type: LeaveType
    date_from: date
    date_to: date
    note: str | None = None


class PilotSwapRequestIn(BaseModel):
    counterparty_employee_no: str
    fdp_or_sector_ref: str
    reason: str | None = None
