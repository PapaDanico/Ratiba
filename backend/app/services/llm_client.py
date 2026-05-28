"""Thin wrapper around the Anthropic SDK.

Centralised so we can swap models per call site, capture cost telemetry,
and keep prompt caching consistent across the bot's intent router
(Phase 4 — Claude Haiku 4.5) and the OM-A constraint parser
(Phase 7 — Claude Sonnet 4.5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings

log = logging.getLogger("ratiba.llm")


@dataclass(frozen=True)
class LlmResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class LlmClientNotConfigured(RuntimeError):
    """Raised when ANTHROPIC_API_KEY is missing — callers should fall back."""


def _client() -> Any:
    """Lazily import + construct the Anthropic client.

    Lazy so test environments without ``ANTHROPIC_API_KEY`` don't
    import-fail just by touching this module.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise LlmClientNotConfigured("ANTHROPIC_API_KEY is not set")
    import anthropic

    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def conversational_route(
    *,
    system: str,
    user_message: str,
    max_tokens: int = 256,
) -> LlmResponse:
    """Light completion via Haiku for bot intent routing.

    Caller is responsible for catching :class:`LlmClientNotConfigured` and
    falling back to a command-only message; LLM outages must never break
    the bot's basic command surface.
    """
    settings = get_settings()
    response = _client().messages.create(
        model=settings.anthropic_model_conversational,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    return LlmResponse(
        text=text.strip(),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        model=response.model,
    )


def parser_complete(
    *,
    system: str,
    user_message: str,
    max_tokens: int = 4096,
) -> LlmResponse:
    """Heavy completion via Sonnet — Phase 7 OM-A parser entry point."""
    settings = get_settings()
    response = _client().messages.create(
        model=settings.anthropic_model_parser,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    return LlmResponse(
        text=text.strip(),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        model=response.model,
    )
