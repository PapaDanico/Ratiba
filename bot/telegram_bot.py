"""Telegram bot — Phase 4.

Thin adapter around the pure handler functions in :mod:`bot.handlers`. Polls
Telegram for updates and routes ``/command`` and free-text messages through.

If ``TELEGRAM_BOT_TOKEN`` isn't set the process stays alive but idle —
useful for the docker-compose dev stack where the bot service exists but
nobody's plugged in a token yet.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys

from bot.api_client import RatibaApi
from bot.handlers import (
    handle_currency,
    handle_duty,
    handle_free_text,
    handle_help,
    handle_leave_submit,
    handle_roster,
    handle_start,
    handle_swap_submit,
)

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("ratiba.bot")


async def _run_telegram(token: str) -> None:
    """Wire python-telegram-bot v21 handlers around our pure handlers."""
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )

    api = RatibaApi()

    async def _reply(update: Update, text: str) -> None:
        if update.effective_chat is None:
            return
        await update.effective_chat.send_message(text)

    def _args_for(update: Update) -> list[str]:
        text = (update.effective_message and update.effective_message.text) or ""
        return text.split()[1:]

    async def _cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id if update.effective_chat else 0
        await _reply(update, await handle_start(args=_args_for(update), chat_id=chat_id, api=api))

    async def _cmd_help(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id if update.effective_chat else 0
        await _reply(update, await handle_help(chat_id=chat_id, api=api))

    async def _cmd_roster(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id if update.effective_chat else 0
        await _reply(update, await handle_roster(chat_id=chat_id, api=api))

    async def _cmd_duty(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id if update.effective_chat else 0
        await _reply(update, await handle_duty(chat_id=chat_id, api=api))

    async def _cmd_currency(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id if update.effective_chat else 0
        await _reply(update, await handle_currency(chat_id=chat_id, api=api))

    async def _cmd_leave(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id if update.effective_chat else 0
        await _reply(
            update,
            await handle_leave_submit(args=_args_for(update), chat_id=chat_id, api=api),
        )

    async def _cmd_swap(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id if update.effective_chat else 0
        await _reply(
            update,
            await handle_swap_submit(args=_args_for(update), chat_id=chat_id, api=api),
        )

    async def _on_text(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id if update.effective_chat else 0
        text = (update.effective_message and update.effective_message.text) or ""
        await _reply(update, await handle_free_text(text=text, chat_id=chat_id, api=api))

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", _cmd_start))
    app.add_handler(CommandHandler("help", _cmd_help))
    app.add_handler(CommandHandler("roster", _cmd_roster))
    app.add_handler(CommandHandler("duty", _cmd_duty))
    app.add_handler(CommandHandler("currency", _cmd_currency))
    app.add_handler(CommandHandler("leave", _cmd_leave))
    app.add_handler(CommandHandler("swap", _cmd_swap))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _on_text))

    log.info("Telegram bot starting in long-poll mode.")
    try:
        await app.initialize()
        await app.start()
        if app.updater is not None:
            await app.updater.start_polling()
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        await stop.wait()
    finally:
        if app.updater is not None:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await api.aclose()


async def _idle_forever() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()


async def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        log.warning("TELEGRAM_BOT_TOKEN not set — bot idle until configured.")
        await _idle_forever()
        return
    await _run_telegram(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
