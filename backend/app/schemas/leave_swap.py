"""Leave + swap request schemas."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.leave import LeaveStatus, LeaveType
from app.models.swap import SwapStatus


class LeaveRequestIn(BaseModel):
    crew_id: uuid.UUID
    type: LeaveType
    date_from: date
    date_to: date
    note: str | None = None


class LeaveDecision(BaseModel):
    status: LeaveStatus
    note: str | None = None


class LeaveRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    crew_id: uuid.UUID
    type: LeaveType
    date_from: date
    date_to: date
    status: LeaveStatus
    note: str | None
    approver_id: uuid.UUID | None


class SwapRequestIn(BaseModel):
    crew_id_initiator: uuid.UUID
    crew_id_counterparty: uuid.UUID
    fdp_or_sector_ref: str
    reason: str | None = None


class SwapDecision(BaseModel):
    status: SwapStatus


class SwapRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    crew_id_initiator: uuid.UUID
    crew_id_counterparty: uuid.UUID
    fdp_or_sector_ref: str
    reason: str | None
    status: SwapStatus
    approver_id: uuid.UUID | None
