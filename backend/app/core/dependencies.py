"""Common FastAPI dependencies — current user, current operator, DB session."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cookies import ACCESS_COOKIE, PILOT_COOKIE, bearer_or_cookie
from app.core.database import get_db
from app.core.security import decode_token
from app.models import Crew, Operator, User
from app.models.user import UserRole

# Roles permitted to perform staff write actions (create/update/delete operator
# data, approvals, publish, imports). A future restricted ``PILOT`` *user* role
# is intentionally excluded; crew use their own scoped token via
# :func:`get_current_pilot`, not a staff login.
STAFF_WRITER_ROLES: tuple[UserRole, ...] = (
    UserRole.CREWING_OFFICER,
    UserRole.CHIEF_PILOT,
    UserRole.ADMIN,
)


def get_current_user(
    request: Request,
    session: Session = Depends(get_db),
) -> User:
    """Resolve the access token to a User row. Raises 401 on any failure.

    The token comes from an ``Authorization: Bearer`` header (bot / API
    clients / tests) or, for browser sessions, the httpOnly ``rt_access``
    cookie."""
    token = bearer_or_cookie(request, ACCESS_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="not an access token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_writer(user: User = Depends(get_current_user)) -> User:
    """Authorise a staff *write* action — 403 unless the user holds a writer role.

    Added as a route ``dependencies=[...]`` entry on mutating endpoints. Reads
    stay open to any authenticated staff user. ``get_current_user`` is request-
    cached, so this shares the single user lookup with the endpoint's own param.
    """
    if user.role not in STAFF_WRITER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="your role cannot perform this action",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Authorise an operator-administration action (team / user management) —
    403 unless the user is an ADMIN. Stricter than :func:`require_writer`."""
    if user.role is not UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="only an operator administrator can manage users",
        )
    return user


def get_current_operator(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Operator:
    operator = session.scalar(select(Operator).where(Operator.id == user.operator_id))
    if operator is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user's operator not found",
        )
    return operator


def get_current_pilot(
    request: Request,
    session: Session = Depends(get_db),
) -> Crew:
    """Resolve a pilot JWT (sub=``crew:<uuid>``) to a Crew row.

    Pilots authenticate via :func:`app.core.security.create_pilot_token`,
    issued by ``POST /api/v1/auth/pilot-pair``. The bot sends it as a Bearer
    header; the ``/crew/me`` web view sends the httpOnly ``rt_pilot`` cookie.
    """
    token = bearer_or_cookie(request, PILOT_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token)
        if payload.get("type") != "pilot":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="not a pilot token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        sub = str(payload["sub"])
        if not sub.startswith("crew:"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="malformed pilot token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        crew_id = uuid.UUID(sub.removeprefix("crew:"))
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    crew = session.get(Crew, crew_id)
    if crew is None or not crew.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="crew member not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return crew
