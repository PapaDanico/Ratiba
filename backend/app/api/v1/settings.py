"""Operator settings endpoints — Phase 3."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_writer
from app.core.security import hash_password, verify_password
from app.models import Operator, User
from app.schemas.settings import (
    AccountOut,
    AccountPatch,
    OperatorOut,
    OperatorPatch,
    PasswordChange,
)
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


@router.patch("/operator", response_model=OperatorOut, dependencies=[Depends(require_writer)])
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


# -- Account self-service (any authenticated staff user) ---------------------


@router.get("/account", response_model=AccountOut)
def get_account(user: User = Depends(get_current_user)) -> AccountOut:
    return AccountOut.model_validate(user)


@router.patch("/account", response_model=AccountOut)
def update_account(
    payload: AccountPatch,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> AccountOut:
    user.full_name = payload.full_name
    session.commit()
    session.refresh(user)
    return AccountOut.model_validate(user)


@router.post("/account/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current password is incorrect",
        )
    user.hashed_password = hash_password(payload.new_password)
    session.commit()
    return None
