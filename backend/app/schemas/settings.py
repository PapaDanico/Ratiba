"""Operator settings schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.operator import OperatorTier


class OperatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    aoc_number: str
    name: str
    base: str
    contact_email: str
    tier: OperatorTier
    default_soft_weights: dict[str, float] = Field(default_factory=dict)


class OperatorPatch(BaseModel):
    name: str | None = None
    base: str | None = None
    contact_email: str | None = None
    tier: OperatorTier | None = None
    default_soft_weights: dict[str, float] | None = None
