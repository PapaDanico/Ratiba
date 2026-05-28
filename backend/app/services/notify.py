"""Best-effort Telegram push for published notices.

When ``TELEGRAM_BOT_TOKEN`` is set, a published notice is pushed to every
paired crew member's Telegram chat via the Bot API's ``sendMessage``.
Pure best-effort: failures are logged, never raised — a notice is
persisted regardless of whether the push succeeds. Crew who aren't
paired (no ``telegram_chat_id``) simply see the notice in the
``/crew/me`` web view + the bot's ``/notices`` command instead.
"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Crew
from app.models.notice import Notice

log = logging.getLogger("ratiba.notify")

_SEVERITY_ICON = {"INFO": "ℹ️", "IMPORTANT": "❗", "CRITICAL": "🚨"}
_CATEGORY_LABEL = {
    "OPERATIONAL": "Operational",
    "FLEET": "Fleet notice",
    "SAFETY": "Safety",
    "SOCIAL": "Crew room",
}


def _format(notice: Notice) -> str:
    icon = _SEVERITY_ICON.get(notice.severity.value, "ℹ️")
    cat = _CATEGORY_LABEL.get(notice.category.value, notice.category.value)
    lines = [f"{icon} {cat}: {notice.title}", "", notice.body]
    if notice.image_url:
        lines += ["", notice.image_url]
    if notice.requires_ack:
        lines += ["", "Please acknowledge in the Ratiba app."]
    return "\n".join(lines)


def push_notice(session: Session, notice: Notice) -> int:
    """Push ``notice`` to all paired crew. Returns the number of sends attempted.

    No-op (returns 0) when no bot token is configured.
    """
    settings = get_settings()
    token = settings.telegram_bot_token.strip()
    if not token:
        return 0

    chat_ids = [
        cid
        for cid in session.scalars(
            select(Crew.telegram_chat_id)
            .where(Crew.operator_id == notice.operator_id)
            .where(Crew.telegram_chat_id.is_not(None))
        ).all()
        if cid is not None
    ]
    if not chat_ids:
        return 0

    text = _format(notice)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    sent = 0
    with httpx.Client(timeout=10.0) as client:
        for chat_id in chat_ids:
            try:
                resp = client.post(url, json={"chat_id": chat_id, "text": text})
                if resp.status_code == 200:
                    sent += 1
                else:
                    log.warning("telegram push %s → %s", chat_id, resp.status_code)
            except Exception as exc:
                log.warning("telegram push failed for %s: %r", chat_id, exc)
    return sent
