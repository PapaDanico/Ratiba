"""Schemas for /healthz, /readyz and /version."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class VersionResponse(BaseModel):
    name: str
    version: str
    phase: str


class ReadyResponse(BaseModel):
    """Liveness response for orchestrator readiness probes."""

    status: Literal["ready", "degraded", "not_ready"]
    checks: dict[str, str]
