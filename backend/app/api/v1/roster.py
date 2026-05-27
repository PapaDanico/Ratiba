"""Roster endpoints. Concrete implementation lands in Phase 2."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get("")
async def list_roster() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Phase 2 — roster endpoints not yet implemented",
    )
