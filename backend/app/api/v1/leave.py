"""Leave and swap endpoints. Concrete implementation lands in Phase 3/4."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get("")
async def list_leave_requests() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Phase 3 — leave endpoints not yet implemented",
    )
