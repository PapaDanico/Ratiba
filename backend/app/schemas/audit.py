"""Audit pack schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class GenerateAuditPackRequest(BaseModel):
    period_from: date
    period_to: date


class AuditPackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    operator_id: uuid.UUID
    period_from: date
    period_to: date
    sha256_hex: str
    byte_size: int
    generator_version: str
    crew_count: int
    fdp_count: int
    anomaly_count: int
    created_at: datetime


class AuditPackVerifyResponse(BaseModel):
    verified: bool
    expected_sha256: str
    actual_sha256: str | None = None
    byte_size: int | None = None
    reason: str | None = None

    # Keep the response shape stable even if the service adds extra
    # diagnostics later.
    @classmethod
    def from_dict(cls, body: dict[str, Any]) -> AuditPackVerifyResponse:
        return cls(
            verified=bool(body.get("verified")),
            expected_sha256=str(body.get("expected_sha256", "")),
            actual_sha256=body.get("actual_sha256"),
            byte_size=body.get("byte_size"),
            reason=body.get("reason"),
        )
