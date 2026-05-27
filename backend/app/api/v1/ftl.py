"""FTL endpoints. Concrete implementation lands in Phase 1."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("/check")
async def check_roster_slice() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Phase 1 — FTL endpoints not yet implemented",
    )


@router.post("/validate-fdp")
async def validate_fdp() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Phase 1 — FTL endpoints not yet implemented",
    )
