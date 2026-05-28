"""Thin wrapper around the Anthropic SDK.

Centralised so we can swap models per call site, capture cost telemetry,
and keep prompt caching consistent across the bot's intent router
(Phase 4 — Claude Haiku 4.5) and the OM-A constraint parser
(Phase 7 — Claude Sonnet 4.5).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.llm_usage import LlmUsageEvent

log = logging.getLogger("ratiba.llm")


@dataclass(frozen=True)
class LlmResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class LlmClientNotConfigured(RuntimeError):
    """Raised when ANTHROPIC_API_KEY is missing — callers should fall back."""


def _log_usage(
    *,
    call_site: str,
    response: LlmResponse,
    session: Session | None,
    operator_id: uuid.UUID | None,
    crew_id: uuid.UUID | None,
) -> None:
    """Always emit a structured log line; persist a row if a session is given.

    Backend-side callers (Phase 7 parser) pass a session and persist. The
    bot has no DB connection — it relies on the structured log + Phase 6's
    log-aggregation pipeline.
    """
    log.info(
        "llm_usage",
        extra={
            "call_site": call_site,
            "model": response.model,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        },
    )
    if session is None:
        return
    session.add(
        LlmUsageEvent(
            operator_id=operator_id,
            crew_id=crew_id,
            call_site=call_site,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
    )


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
    session: Session | None = None,
    operator_id: uuid.UUID | None = None,
    crew_id: uuid.UUID | None = None,
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
    result = LlmResponse(
        text=text.strip(),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        model=response.model,
    )
    _log_usage(
        call_site="conversational_route",
        response=result,
        session=session,
        operator_id=operator_id,
        crew_id=crew_id,
    )
    return result


def parser_complete(
    *,
    system: str,
    user_message: str,
    max_tokens: int = 4096,
    session: Session | None = None,
    operator_id: uuid.UUID | None = None,
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
    result = LlmResponse(
        text=text.strip(),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        model=response.model,
    )
    _log_usage(
        call_site="parser_complete",
        response=result,
        session=session,
        operator_id=operator_id,
        crew_id=None,
    )
    return result
