"""Pilot pairing service.

The crewing officer issues a short-lived code from the dashboard. The pilot
hands it to the Telegram bot (``/start <code>``) or pastes it into the
``/crew/me`` web view. Both flows exchange the code for a long-lived
pilot JWT via :func:`redeem_pairing_code`.
"""

from __future__ import annotations

import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_pilot_token
from app.models import Crew, PairingToken, User
from app.services import audit_log

CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_LENGTH = 8
DEFAULT_EXPIRY_MINUTES = 15


class PairingError(Exception):
    """Raised when a pairing code is unknown / expired / already redeemed."""


def _new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def issue_pairing_code(
    session: Session,
    *,
    user: User,
    crew_id: uuid.UUID,
    expiry_minutes: int = DEFAULT_EXPIRY_MINUTES,
) -> PairingToken:
    """Generate and persist a pairing token for ``crew_id``."""
    crew = session.scalar(
        select(Crew).where(Crew.id == crew_id).where(Crew.operator_id == user.operator_id)
    )
    if crew is None:
        raise PairingError("crew not found in operator scope")

    code = _new_code()
    while session.scalar(select(PairingToken).where(PairingToken.code == code)) is not None:
        code = _new_code()

    token = PairingToken(
        operator_id=user.operator_id,
        created_by_user_id=user.id,
        crew_id=crew_id,
        code=code,
        expires_at=datetime.now(UTC) + timedelta(minutes=expiry_minutes),
    )
    session.add(token)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="ISSUE_PAIRING_CODE",
        entity_type="pairing_token",
        entity_id=token.id,
        before_state=None,
        after_state={"crew_id": str(crew_id)},
    )
    session.commit()
    session.refresh(token)
    return token


def redeem_pairing_code(
    session: Session,
    *,
    code: str,
    telegram_chat_id: int | None = None,
) -> tuple[Crew, str]:
    """Redeem a code, attach chat_id, return (crew, pilot_jwt)."""
    token = session.scalar(select(PairingToken).where(PairingToken.code == code))
    if token is None:
        raise PairingError("unknown pairing code")
    if token.redeemed_at is not None:
        raise PairingError("pairing code already redeemed")
    if token.expires_at <= datetime.now(UTC):
        raise PairingError("pairing code expired")

    crew = session.get(Crew, token.crew_id)
    if crew is None:
        raise PairingError("crew not found")

    token.redeemed_at = datetime.now(UTC)
    if telegram_chat_id is not None:
        token.redeemed_telegram_chat_id = telegram_chat_id
        crew.telegram_chat_id = telegram_chat_id
    session.flush()
    audit_log.record(
        session,
        operator_id=token.operator_id,
        actor_user_id=None,
        action="REDEEM_PAIRING_CODE",
        entity_type="pairing_token",
        entity_id=token.id,
        before_state=None,
        after_state={
            "crew_id": str(crew.id),
            "telegram_chat_id": telegram_chat_id,
        },
    )
    session.commit()
    session.refresh(crew)

    jwt_token = create_pilot_token(str(crew.id), str(crew.operator_id))
    return crew, jwt_token
