"""Team / user-management endpoints — operator-admin only.

Lets an operator administrator onboard their crewing team: list members,
create logins with a role, change roles, and activate / deactivate accounts.
All actions are operator-scoped (an admin only ever sees or touches users in
their own operator) and audited. Self-lockout is prevented: an admin cannot
strip their own ADMIN role or deactivate their own account.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.security import hash_password
from app.models import User
from app.models.user import UserRole
from app.schemas.users import UserCreate, UserOut, UserUpdate
from app.services import audit_log

router = APIRouter()


@router.get("", response_model=list[UserOut])
def list_users(
    admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> list[User]:
    return list(
        session.scalars(
            select(User).where(User.operator_id == admin.operator_id).order_by(User.full_name)
        ).all()
    )


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> User:
    existing = session.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="a user with that email already exists",
        )
    user = User(
        operator_id=admin.operator_id,
        email=str(payload.email),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    session.add(user)
    session.flush()
    audit_log.record(
        session,
        operator_id=admin.operator_id,
        actor_user_id=admin.id,
        action="CREATE_USER",
        entity_type="user",
        entity_id=user.id,
        after_state=UserOut.model_validate(user).model_dump(mode="json"),
    )
    session.commit()
    session.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> User:
    target = session.scalar(
        select(User).where(User.id == user_id).where(User.operator_id == admin.operator_id)
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    fields = payload.model_dump(exclude_unset=True)

    # Self-lockout guards: an admin may not demote themselves out of ADMIN nor
    # deactivate their own account — that could leave the operator with no
    # administrator able to manage the team.
    if target.id == admin.id:
        if "role" in fields and fields["role"] is not UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="you cannot remove your own administrator role",
            )
        if fields.get("is_active") is False:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="you cannot deactivate your own account",
            )

    before = UserOut.model_validate(target).model_dump(mode="json")
    for key, value in fields.items():
        setattr(target, key, value)
    session.flush()
    audit_log.record(
        session,
        operator_id=admin.operator_id,
        actor_user_id=admin.id,
        action="UPDATE_USER",
        entity_type="user",
        entity_id=target.id,
        before_state=before,
        after_state=UserOut.model_validate(target).model_dump(mode="json"),
    )
    session.commit()
    session.refresh(target)
    return target
