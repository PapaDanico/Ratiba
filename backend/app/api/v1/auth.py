"""Auth endpoints — JWT login, refresh, current user."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cookies import (
    REFRESH_COOKIE,
    clear_auth_cookies,
    set_auth_cookies,
    set_pilot_cookie,
)
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import DEMO_WORKSPACE_LIMITER, LOGIN_LIMITER, PAIRING_LIMITER
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models import User
from app.schemas.auth import (
    CurrentUserOut,
    DemoWorkspaceRequest,
    DemoWorkspaceResponse,
    LoginRequest,
    RefreshRequest,
    TokenPair,
)
from app.schemas.pilot import PilotPairRequest, PilotPairResponse
from app.services import demo_workspace, pairing, tokens

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
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
) -> TokenPair:
    ip = request.client.host if request.client else "unknown"
    if not LOGIN_LIMITER.hit(f"ip:{ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many login attempts — try again in a minute",
        )
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
    pair = TokenPair(
        access_token=create_access_token(sub, extra={"operator_id": str(user.operator_id)}),
        refresh_token=create_refresh_token(sub),
    )
    # Browser sessions read these from httpOnly cookies; the body copy is kept
    # for the bot / API clients / tests that authenticate with a Bearer header.
    set_auth_cookies(response, pair.access_token, pair.refresh_token)
    return pair


@router.post("/refresh", response_model=TokenPair)
def refresh(
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    payload: RefreshRequest | None = Body(default=None),
) -> TokenPair:
    """Rotate the refresh token: validate it, revoke it, and issue a fresh
    access + refresh pair. A previously-used (or logged-out) refresh token is
    rejected, so a leaked token is single-use.

    The token is taken from the request body (Bearer clients) or, for browser
    sessions, the httpOnly ``rt_refresh`` cookie."""
    raw = payload.refresh_token if payload is not None else request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing refresh token"
        )
    try:
        decoded = decode_token(raw)
        if decoded.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="not a refresh token"
            )
        user_id = uuid.UUID(decoded["sub"])
        jti = str(decoded["jti"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token"
        ) from exc

    if tokens.is_revoked(session, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token already used or revoked"
        )

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")

    tokens.revoke(session, jti, datetime.fromtimestamp(int(decoded["exp"]), tz=UTC))
    session.commit()
    sub = str(user.id)
    pair = TokenPair(
        access_token=create_access_token(sub, extra={"operator_id": str(user.operator_id)}),
        refresh_token=create_refresh_token(sub),
    )
    set_auth_cookies(response, pair.access_token, pair.refresh_token)
    return pair


@router.post(
    "/demo-workspace",
    response_model=DemoWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_demo_workspace(
    payload: DemoWorkspaceRequest,
    request: Request,
    session: Session = Depends(get_db),
) -> DemoWorkspaceResponse:
    """Provision an isolated, pre-seeded demo workspace + crewing-officer login.

    Public + rate-limited per source IP. Lets an evaluator spin up their own
    sandbox (so feedback testers don't collide on shared data) and walk the
    golden path immediately. After this returns, the client logs in normally
    with the email + password just chosen.
    """
    ip = request.client.host if request.client else "unknown"
    if not DEMO_WORKSPACE_LIMITER.hit(f"ip:{ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many demo workspaces created from this network — try again later",
        )
    try:
        operator, _user = demo_workspace.create_workspace(
            session,
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
            operator_name=payload.operator_name,
        )
    except demo_workspace.DemoWorkspaceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DemoWorkspaceResponse(
        operator_id=operator.id,
        operator_name=operator.name,
        email=payload.email,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    payload: RefreshRequest | None = Body(default=None),
) -> None:
    """Revoke the presented refresh token so it can't mint new access tokens,
    and clear the browser session cookies.

    Best-effort: a malformed/expired/absent token still yields 204 (the client
    clears regardless). The current access token lapses at its own expiry."""
    raw = payload.refresh_token if payload is not None else request.cookies.get(REFRESH_COOKIE)
    if raw:
        try:
            decoded = decode_token(raw)
            jti = decoded.get("jti")
            if decoded.get("type") == "refresh" and jti:
                tokens.revoke(
                    session, str(jti), datetime.fromtimestamp(int(decoded["exp"]), tz=UTC)
                )
                session.commit()
        except (JWTError, KeyError, ValueError):
            pass  # logout is idempotent/best-effort
    clear_auth_cookies(response)
    return None


@router.get("/me", response_model=CurrentUserOut)
def me(user: User = Depends(get_current_user)) -> CurrentUserOut:
    return _user_to_out(user)


# -- Pilot pairing -----------------------------------------------------------


@router.post("/pilot-pair", response_model=PilotPairResponse)
def pilot_pair(
    payload: PilotPairRequest,
    request: Request,
    response: Response,
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

    # The bot reads ``pilot_token`` from the body; the /crew/me web view uses
    # the httpOnly cookie instead.
    set_pilot_cookie(response, token)
    return PilotPairResponse(
        pilot_token=token,
        crew_id=crew.id,
        employee_no=crew.employee_no,
        role=crew.role,
        operator_id=crew.operator_id,
    )
