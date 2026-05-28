"""Pydantic schemas for API request and response models.

Concrete schemas are added phase-by-phase as endpoints are implemented.
Phase 0 only contains health and version schemas.
"""

from app.schemas.health import HealthResponse, VersionResponse

__all__ = ["HealthResponse", "VersionResponse"]
