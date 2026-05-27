"""LLM-fronted free-text router for the bot.

Phase 4 wires Claude Haiku 4.5 to extract intent from plain-language messages
and dispatch to the appropriate command handler. Phase 0 is a stub.
"""

from __future__ import annotations


class NlpRouterNotImplemented(NotImplementedError):
    """Raised by Phase 0 stubs to make the deferral obvious."""


async def route(_text: str) -> str:
    raise NlpRouterNotImplemented("NLP router arrives in Phase 4")
