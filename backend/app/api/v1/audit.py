"""Audit pack endpoints. Concrete implementation lands in Phase 5."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("/generate")
async def generate_audit_pack() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Phase 5 — audit pack endpoints not yet implemented",
    )
