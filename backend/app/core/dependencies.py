"""Common FastAPI dependencies — current user, current operator, DB session."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models import Crew, Operator, User

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(_oauth2_scheme),
    session: Session = Depends(get_db),
) -> User:
    """Resolve the bearer token to a User row. Raises 401 on any failure."""
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
    token: str | None = Depends(_oauth2_scheme),
    session: Session = Depends(get_db),
) -> Crew:
    """Resolve a pilot JWT (sub=``crew:<uuid>``) to a Crew row.

    Pilots authenticate via :func:`app.core.security.create_pilot_token`,
    issued by ``POST /api/v1/auth/pilot-pair``. Same Bearer-header shape as
    user tokens so the bot and the /crew/me web view share one client.
    """
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
