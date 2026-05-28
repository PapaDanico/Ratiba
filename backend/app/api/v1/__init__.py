"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    aircraft,
    audit,
    auth,
    constraints,
    crew,
    documents,
    ftl,
    leave,
    me,
    notices,
    onboarding,
    reference,
    reports,
    roster,
    sectors,
    swap,
    training,
)
from app.api.v1 import (
    settings as settings_routes,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# Pilot self-service surface (bot + /crew/me web view) registered before the
# crewing-officer-scoped /crew router so /crew/me/* matches first.
api_router.include_router(me.router, prefix="/crew/me", tags=["crew-me"])
api_router.include_router(crew.router, prefix="/crew", tags=["crew"])
api_router.include_router(roster.router, prefix="/roster", tags=["roster"])
api_router.include_router(sectors.router, prefix="/sectors", tags=["sectors"])
api_router.include_router(ftl.router, prefix="/ftl", tags=["ftl"])
api_router.include_router(training.router, prefix="/training", tags=["training"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(leave.router, prefix="/leave", tags=["leave"])
api_router.include_router(swap.router, prefix="/swap", tags=["swap"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(notices.router, prefix="/notices", tags=["notices"])
api_router.include_router(aircraft.router, prefix="/fleet", tags=["fleet"])
api_router.include_router(reference.router, prefix="/reference", tags=["reference"])
api_router.include_router(constraints.router, prefix="/constraints", tags=["constraints"])
api_router.include_router(settings_routes.router, prefix="/settings", tags=["settings"])

__all__ = ["api_router"]
