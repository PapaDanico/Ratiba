"""Operator settings endpoints — Phase 3."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin, require_writer
from app.core.security import hash_password, verify_password
from app.models import Crew, Operator, User
from app.schemas.crew import CrewOut
from app.schemas.settings import (
    AccountOut,
    AccountPatch,
    OperatorOut,
    OperatorPatch,
    PasswordChange,
)
from app.schemas.users import UserOut
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


# -- Data export (KDPA portability; operator-admin) --------------------------


@router.get("/operator/export")
def export_operator_data(
    admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> Response:
    """Download a JSON bundle of the operator's own structured data — operator
    profile, dashboard logins, and crew roster. Admin-only; supports KDPA 2019
    data-portability. Credentials (password hashes) are never included."""
    operator = session.scalar(select(Operator).where(Operator.id == admin.operator_id))
    if operator is None:
        raise HTTPException(status_code=404, detail="operator not found")

    users = session.scalars(
        select(User).where(User.operator_id == admin.operator_id).order_by(User.full_name)
    ).all()
    crew = session.scalars(
        select(Crew).where(Crew.operator_id == admin.operator_id).order_by(Crew.employee_no)
    ).all()

    bundle = {
        "exported_at": datetime.now(UTC).isoformat(),
        "operator": OperatorOut.model_validate(operator).model_dump(mode="json"),
        "users": [UserOut.model_validate(u).model_dump(mode="json") for u in users],
        "crew": [CrewOut.model_validate(c).model_dump(mode="json") for c in crew],
    }
    audit_log.record(
        session,
        operator_id=admin.operator_id,
        actor_user_id=admin.id,
        action="EXPORT_OPERATOR_DATA",
        entity_type="operator",
        entity_id=operator.id,
    )
    session.commit()

    filename = f"ratiba_export_{operator.aoc_number}_{datetime.now(UTC).date().isoformat()}.json"
    return Response(
        content=json.dumps(bundle, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
