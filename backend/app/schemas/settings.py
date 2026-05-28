"""Operator settings schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from app.models.operator import OperatorTier


class OperatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    aoc_number: str
    name: str
    base: str
    contact_email: str
    tier: OperatorTier


class OperatorPatch(BaseModel):
    name: str | None = None
    base: str | None = None
    contact_email: str | None = None
    tier: OperatorTier | None = None
