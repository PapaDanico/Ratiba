"""Auth endpoints. Concrete implementation lands in Phase 3."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("/login")
async def login() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Phase 3 — auth not yet implemented",
    )


@router.post("/refresh")
async def refresh() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Phase 3 — auth not yet implemented",
    )


@router.post("/logout")
async def logout() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Phase 3 — auth not yet implemented",
    )
