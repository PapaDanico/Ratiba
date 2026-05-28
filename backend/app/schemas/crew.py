"""Crew + currency schemas."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.crew import ContractType, CrewRole
from app.models.training import CurrencyType


class CrewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_no: str
    first_name: str
    last_name: str
    role: CrewRole
    base_station: str
    contract_type: ContractType
    active: bool
    languages: list[str]
    faith_observance_flags: dict[str, bool]


class CrewIn(BaseModel):
    employee_no: str
    first_name: str
    last_name: str
    role: CrewRole
    date_of_hire: date
    date_of_birth: date
    base_station: str
    contract_type: ContractType
    active: bool = True
    languages: list[str] = Field(default_factory=list)
    faith_observance_flags: dict[str, bool] = Field(default_factory=dict)


class CrewPatch(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    base_station: str | None = None
    contract_type: ContractType | None = None
    active: bool | None = None
    languages: list[str] | None = None
    faith_observance_flags: dict[str, bool] | None = None


class CurrencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    crew_id: uuid.UUID
    currency_type: CurrencyType
    last_completed_date: date
    expires_date: date
    evidence_ref: str | None


class CurrencyIn(BaseModel):
    currency_type: CurrencyType
    last_completed_date: date
    expires_date: date
    evidence_ref: str | None = None


class CurrencyStatus(BaseModel):
    """Traffic-light view of one currency: GREEN/AMBER/RED + days remaining."""

    crew_id: uuid.UUID
    currency_type: CurrencyType
    expires_date: date
    days_remaining: int
    state: str  # GREEN | AMBER | RED
