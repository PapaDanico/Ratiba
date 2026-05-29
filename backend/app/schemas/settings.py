"""Operator settings schemas."""

from __future__ import annotations

import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.operator import OperatorTier


class OperatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    aoc_number: str
    name: str
    base: str
    timezone: str
    contact_email: str
    tier: OperatorTier
    default_soft_weights: dict[str, float] = Field(default_factory=dict)


class OperatorPatch(BaseModel):
    name: str | None = None
    base: str | None = None
    timezone: str | None = None
    contact_email: str | None = None
    tier: OperatorTier | None = None
    default_soft_weights: dict[str, float] | None = None

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown timezone {v!r}") from exc
        return v
