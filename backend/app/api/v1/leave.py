"""Leave request endpoints — Phase 3."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_writer
from app.models import LeaveRequest, User
from app.models.leave import LeaveStatus
from app.schemas.leave_swap import LeaveDecision, LeaveRequestIn, LeaveRequestOut
from app.services import audit_log, notify

router = APIRouter()


@router.post(
    "",
    response_model=LeaveRequestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_writer)],
)
def create_leave(
    payload: LeaveRequestIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> LeaveRequestOut:
    row = LeaveRequest(
        operator_id=user.operator_id,
        created_by_user_id=user.id,
        status=LeaveStatus.PENDING,
        **payload.model_dump(),
    )
    session.add(row)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="SUBMIT_LEAVE",
        entity_type="leave_request",
        entity_id=row.id,
        before_state=None,
        after_state=payload.model_dump(mode="json"),
    )
    session.commit()
    session.refresh(row)
    return LeaveRequestOut.model_validate(row)


@router.get("", response_model=list[LeaveRequestOut])
def list_leave(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    status_filter: LeaveStatus | None = Query(default=None, alias="status"),
) -> list[LeaveRequestOut]:
    q = select(LeaveRequest).where(LeaveRequest.operator_id == user.operator_id)
    if status_filter is not None:
        q = q.where(LeaveRequest.status == status_filter)
    q = q.order_by(LeaveRequest.created_at.desc())
    rows = session.scalars(q).all()
    return [LeaveRequestOut.model_validate(r) for r in rows]


@router.patch("/{leave_id}", response_model=LeaveRequestOut, dependencies=[Depends(require_writer)])
def decide_leave(
    leave_id: uuid.UUID,
    payload: LeaveDecision,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> LeaveRequestOut:
    row = session.scalar(
        select(LeaveRequest)
        .where(LeaveRequest.id == leave_id)
        .where(LeaveRequest.operator_id == user.operator_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="leave request not found")

    before = LeaveRequestOut.model_validate(row).model_dump(mode="json")
    row.status = payload.status
    if payload.note is not None:
        row.note = payload.note
    row.approver_id = user.id
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action=f"LEAVE_{payload.status.value}",
        entity_type="leave_request",
        entity_id=row.id,
        before_state=before,
        after_state=LeaveRequestOut.model_validate(row).model_dump(mode="json"),
    )
    session.commit()
    session.refresh(row)

    decision = row.status.value.lower()
    note_suffix = f" Note: {row.note}" if row.note else ""
    notify.notify_crew_member(
        session,
        crew_id=row.crew_id,
        subject=f"Leave request {decision}",
        body=(
            f"Your leave {row.date_from.isoformat()} to {row.date_to.isoformat()} "
            f"was {decision} by {user.full_name}.{note_suffix}"
        ),
    )
    return LeaveRequestOut.model_validate(row)
