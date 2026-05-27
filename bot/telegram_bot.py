"""Telegram bot entry point.

Phase 0: no-op long-running process that proves the container starts and can
read the bot token. Real command handlers land in Phase 4.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("ratiba.bot")


async def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        log.warning("TELEGRAM_BOT_TOKEN not set — bot idle until configured.")
    else:
        log.info("Bot token detected; Phase 4 will wire command handlers.")

    stop = asyncio.Event()

    def _shutdown(*_: object) -> None:
        log.info("Shutdown signal received.")
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _shutdown)

    await stop.wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
