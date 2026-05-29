"""Swap request endpoints — Phase 3."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_writer
from app.models import SwapRequest, User
from app.models.swap import SwapStatus
from app.schemas.leave_swap import SwapDecision, SwapRequestIn, SwapRequestOut
from app.services import audit_log, notify

router = APIRouter()


@router.post(
    "",
    response_model=SwapRequestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_writer)],
)
def create_swap(
    payload: SwapRequestIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SwapRequestOut:
    row = SwapRequest(
        operator_id=user.operator_id,
        created_by_user_id=user.id,
        status=SwapStatus.PENDING,
        **payload.model_dump(),
    )
    session.add(row)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="SUBMIT_SWAP",
        entity_type="swap_request",
        entity_id=row.id,
        before_state=None,
        after_state=payload.model_dump(mode="json"),
    )
    session.commit()
    session.refresh(row)
    return SwapRequestOut.model_validate(row)


@router.get("", response_model=list[SwapRequestOut])
def list_swaps(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    status_filter: SwapStatus | None = Query(default=None, alias="status"),
) -> list[SwapRequestOut]:
    q = select(SwapRequest).where(SwapRequest.operator_id == user.operator_id)
    if status_filter is not None:
        q = q.where(SwapRequest.status == status_filter)
    q = q.order_by(SwapRequest.created_at.desc())
    rows = session.scalars(q).all()
    return [SwapRequestOut.model_validate(r) for r in rows]


@router.patch("/{swap_id}", response_model=SwapRequestOut, dependencies=[Depends(require_writer)])
def decide_swap(
    swap_id: uuid.UUID,
    payload: SwapDecision,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SwapRequestOut:
    row = session.scalar(
        select(SwapRequest)
        .where(SwapRequest.id == swap_id)
        .where(SwapRequest.operator_id == user.operator_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="swap request not found")

    before = SwapRequestOut.model_validate(row).model_dump(mode="json")
    row.status = payload.status
    row.approver_id = user.id
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action=f"SWAP_{payload.status.value}",
        entity_type="swap_request",
        entity_id=row.id,
        before_state=before,
        after_state=SwapRequestOut.model_validate(row).model_dump(mode="json"),
    )
    session.commit()
    session.refresh(row)

    decision = row.status.value.lower()
    for crew_id in (row.crew_id_initiator, row.crew_id_counterparty):
        notify.notify_crew_member(
            session,
            crew_id=crew_id,
            subject=f"Duty swap {decision}",
            body=f"Your duty-swap request was {decision} by {user.full_name}.",
        )
    return SwapRequestOut.model_validate(row)
