"""Auth endpoints — JWT login, refresh, current user."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import PAIRING_LIMITER
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models import User
from app.schemas.auth import (
    AccessTokenOnly,
    CurrentUserOut,
    LoginRequest,
    RefreshRequest,
    TokenPair,
)
from app.schemas.pilot import PilotPairRequest, PilotPairResponse
from app.services import pairing

router = APIRouter()


def _user_to_out(user: User) -> CurrentUserOut:
    return CurrentUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        operator_id=user.operator_id,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, session: Session = Depends(get_db)) -> TokenPair:
    user = session.scalar(select(User).where(User.email == payload.email))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid email or password",
        )
    sub = str(user.id)
    return TokenPair(
        access_token=create_access_token(sub, extra={"operator_id": str(user.operator_id)}),
        refresh_token=create_refresh_token(sub),
    )


@router.post("/refresh", response_model=AccessTokenOnly)
def refresh(payload: RefreshRequest, session: Session = Depends(get_db)) -> AccessTokenOnly:
    try:
        decoded = decode_token(payload.refresh_token)
        if decoded.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="not a refresh token"
            )
        user_id = uuid.UUID(decoded["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token"
        ) from exc

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return AccessTokenOnly(
        access_token=create_access_token(str(user.id), extra={"operator_id": str(user.operator_id)})
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> None:
    """Stateless JWT — client discards tokens. Phase 4+: token revocation list."""
    return None


@router.get("/me", response_model=CurrentUserOut)
def me(user: User = Depends(get_current_user)) -> CurrentUserOut:
    return _user_to_out(user)


# -- Pilot pairing -----------------------------------------------------------


@router.post("/pilot-pair", response_model=PilotPairResponse)
def pilot_pair(
    payload: PilotPairRequest,
    request: Request,
    session: Session = Depends(get_db),
) -> PilotPairResponse:
    """Exchange a pairing code (issued by the dashboard) for a pilot JWT.

    Public endpoint — anyone with a valid, unredeemed, unexpired code can
    redeem. Used by the Telegram bot's ``/start`` handler and by the
    ``/crew/me`` web view's pairing screen.

    Rate-limited to 5 attempts per minute per ``telegram_chat_id`` or
    per source IP when no chat id is supplied — blunts brute-force
    enumeration of the 8-character code space.
    """
    rate_key = (
        f"chat:{payload.telegram_chat_id}"
        if payload.telegram_chat_id is not None
        else f"ip:{request.client.host if request.client else 'unknown'}"
    )
    if not PAIRING_LIMITER.hit(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many pairing attempts — try again in a minute",
        )
    try:
        crew, token = pairing.redeem_pairing_code(
            session,
            code=payload.code.strip().upper(),
            telegram_chat_id=payload.telegram_chat_id,
        )
    except pairing.PairingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PilotPairResponse(
        pilot_token=token,
        crew_id=crew.id,
        employee_no=crew.employee_no,
        role=crew.role,
        operator_id=crew.operator_id,
    )
