"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    audit,
    auth,
    crew,
    ftl,
    leave,
    roster,
    swap,
    training,
)
from app.api.v1 import (
    settings as settings_routes,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(crew.router, prefix="/crew", tags=["crew"])
api_router.include_router(roster.router, prefix="/roster", tags=["roster"])
api_router.include_router(ftl.router, prefix="/ftl", tags=["ftl"])
api_router.include_router(training.router, prefix="/training", tags=["training"])
api_router.include_router(leave.router, prefix="/leave", tags=["leave"])
api_router.include_router(swap.router, prefix="/swap", tags=["swap"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(settings_routes.router, prefix="/settings", tags=["settings"])

__all__ = ["api_router"]
