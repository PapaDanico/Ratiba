"""Operator settings endpoints — Phase 3."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import Operator, User
from app.schemas.settings import OperatorOut, OperatorPatch
from app.services import audit_log

router = APIRouter()


@router.get("/operator", response_model=OperatorOut)
def get_operator(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> OperatorOut:
    op = session.scalar(select(Operator).where(Operator.id == user.operator_id))
    if op is None:
        raise HTTPException(status_code=404, detail="operator not found")
    return OperatorOut.model_validate(op)


@router.patch("/operator", response_model=OperatorOut)
def update_operator(
    payload: OperatorPatch,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> OperatorOut:
    op = session.scalar(select(Operator).where(Operator.id == user.operator_id))
    if op is None:
        raise HTTPException(status_code=404, detail="operator not found")

    before = OperatorOut.model_validate(op).model_dump(mode="json")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(op, k, v)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="UPDATE_OPERATOR",
        entity_type="operator",
        entity_id=op.id,
        before_state=before,
        after_state=OperatorOut.model_validate(op).model_dump(mode="json"),
    )
    session.commit()
    session.refresh(op)
    return OperatorOut.model_validate(op)
