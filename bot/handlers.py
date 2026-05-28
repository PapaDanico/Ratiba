"""Pure handler functions — easy to unit-test without spinning up Telegram.

Each handler takes the raw text the user sent + a chat_id + an
:class:`RatibaApi` instance and returns the reply text. The Telegram
adapter in :mod:`telegram_bot` wraps these into ``CommandHandler`` /
``MessageHandler`` callbacks.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from bot import formatters, nlp_router
from bot.api_client import BackendError, RatibaApi

log = logging.getLogger("ratiba.bot.handlers")


async def handle_start(*, args: list[str], chat_id: int, api: RatibaApi) -> str:
    if not args:
        return (
            "Welcome to Ratiba.\n\n"
            "To pair this chat with your crew record, ask your crewing "
            "officer to issue a pairing code from the dashboard, then send:\n"
            "  /start <code>"
        )
    code = args[0].strip().upper()
    try:
        body = await api.pair(code=code, chat_id=chat_id)
    except BackendError as exc:
        return f"Could not pair: {exc.body.get('detail') if isinstance(exc.body, dict) else exc}"
    return (
        f"✅ Paired as {body['employee_no']} ({body['role']}).\nTry /roster, /duty, or /currency."
    )


async def handle_help(*, chat_id: int, api: RatibaApi) -> str:
    return formatters.HELP_TEXT


async def handle_roster(*, chat_id: int, api: RatibaApi) -> str:
    today = date.today()
    payload = await api.roster(
        chat_id,
        date_from=today.isoformat(),
        date_to=(today + timedelta(days=13)).isoformat(),
    )
    return formatters.format_roster(payload)


async def handle_duty(*, chat_id: int, api: RatibaApi) -> str:
    payload = await api.duty_today(chat_id)
    return formatters.format_today(payload)


async def handle_currency(*, chat_id: int, api: RatibaApi) -> str:
    payload = await api.currency(chat_id)
    return formatters.format_currency(payload)


async def handle_leave_help(*, chat_id: int, api: RatibaApi) -> str:
    return (
        "To submit a leave request, send:\n"
        "  /leave ANNUAL 2026-07-01 2026-07-07 Family event\n"
        "Types: ANNUAL, SICK, COMPASSIONATE, FAITH, OTHER"
    )


async def handle_swap_help(*, chat_id: int, api: RatibaApi) -> str:
    return (
        "To request a swap, send:\n"
        "  /swap <counterparty-employee-no> <FDP-or-sector-ref> <reason…>\n"
        "Example: /swap P012 RB101-2026-07-15 Doctor appointment"
    )


async def handle_leave_submit(*, args: list[str], chat_id: int, api: RatibaApi) -> str:
    if len(args) < 3:
        return await handle_leave_help(chat_id=chat_id, api=api)
    type_, date_from, date_to, *note_parts = args
    note = " ".join(note_parts) if note_parts else None
    try:
        body = await api.submit_leave(
            chat_id,
            type_=type_.upper(),
            date_from=date_from,
            date_to=date_to,
            note=note,
        )
    except BackendError as exc:
        return f"Could not submit leave: {exc.body.get('detail') if isinstance(exc.body, dict) else exc}"
    return (
        f"📝 Leave request submitted ({body['type']}, {body['date_from']} → "
        f"{body['date_to']}). Status: {body['status']}."
    )


async def handle_swap_submit(*, args: list[str], chat_id: int, api: RatibaApi) -> str:
    if len(args) < 2:
        return await handle_swap_help(chat_id=chat_id, api=api)
    counterparty, ref, *reason_parts = args
    reason = " ".join(reason_parts) if reason_parts else None
    try:
        body = await api.submit_swap(
            chat_id,
            counterparty_employee_no=counterparty,
            fdp_or_sector_ref=ref,
            reason=reason,
        )
    except BackendError as exc:
        return f"Could not submit swap: {exc.body.get('detail') if isinstance(exc.body, dict) else exc}"
    return f"🔁 Swap request submitted ({body['fdp_or_sector_ref']}). Status: {body['status']}."


_INTENT_TO_HANDLER = {
    "roster": handle_roster,
    "duty_today": handle_duty,
    "currency": handle_currency,
    "swap_help": handle_swap_help,
    "leave_help": handle_leave_help,
    "help": handle_help,
}


async def handle_free_text(*, text: str, chat_id: int, api: RatibaApi) -> str:
    """Route a plain-language message via the NLP layer and dispatch."""
    routed = nlp_router.route(text)
    log.info("free_text routed", extra={"intent": routed.intent, "confidence": routed.confidence})
    handler = _INTENT_TO_HANDLER.get(routed.intent)
    if handler is None:
        return (
            f"I didn't catch that. {formatters.HELP_TEXT}"
            if routed.intent == "unknown"
            else formatters.HELP_TEXT
        )
    try:
        return await handler(chat_id=chat_id, api=api)
    except BackendError as exc:
        if exc.status_code == 401:
            return "I can't see your crew record yet — please pair this chat first: /start <code>"
        return f"Backend error: {exc}"
