"""Training and currency endpoints. Concrete implementation lands in Phase 1."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get("")
async def list_currencies() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Phase 1 — training endpoints not yet implemented",
    )
