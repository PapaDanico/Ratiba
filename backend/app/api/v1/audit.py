"""Audit pack endpoints — Phase 5."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_writer
from app.models import AuditPack, User
from app.schemas.audit import (
    AuditPackOut,
    AuditPackVerifyResponse,
    GenerateAuditPackRequest,
)
from app.services import audit_pack

router = APIRouter()


@router.post("/generate", response_model=AuditPackOut, dependencies=[Depends(require_writer)])
def generate(
    payload: GenerateAuditPackRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> AuditPackOut:
    """Build a KCAA-presentable PDF audit pack for the requested period.

    Synchronous: a 90-day pack for a 25-pilot operator runs in well
    under the Plan §5 Phase 5 acceptance bound of 30 s. Phase 6 will
    swap to the async rq queue if real-world packs grow larger.
    """
    try:
        pack = audit_pack.generate_pack(
            session,
            user=user,
            period_from=payload.period_from,
            period_to=payload.period_to,
        )
    except audit_pack.AuditPackError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AuditPackOut.model_validate(pack)


@router.get("/packs", response_model=list[AuditPackOut])
def list_packs(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[AuditPackOut]:
    q = select(AuditPack).where(AuditPack.operator_id == user.operator_id)
    if date_from is not None:
        q = q.where(AuditPack.period_to >= date_from)
    if date_to is not None:
        q = q.where(AuditPack.period_from <= date_to)
    q = q.order_by(AuditPack.created_at.desc())
    return [AuditPackOut.model_validate(r) for r in session.scalars(q).all()]


@router.get("/packs/{pack_id}/download")
def download(
    pack_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Response:
    try:
        body, pack = audit_pack.read_pack_bytes(
            session, pack_id=pack_id, operator_id=user.operator_id
        )
    except audit_pack.AuditPackError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    filename = f"ratiba_audit_{pack.period_from.isoformat()}_{pack.period_to.isoformat()}.pdf"
    return Response(
        content=body,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Audit-Pack-SHA256": pack.sha256_hex,
        },
    )


@router.get(
    "/packs/{pack_id}/verify",
    response_model=AuditPackVerifyResponse,
)
def verify(
    pack_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> AuditPackVerifyResponse:
    try:
        body = audit_pack.verify_pack(session, pack_id=pack_id, operator_id=user.operator_id)
    except audit_pack.AuditPackError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AuditPackVerifyResponse.from_dict(body)
