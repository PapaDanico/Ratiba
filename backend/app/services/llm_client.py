"""Thin wrapper around the Anthropic SDK.

Centralised so we can swap models per call site, capture cost telemetry,
and keep prompt caching consistent. Phase 0 only sketches the surface.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LlmModels:
    """Model selection for each call site."""

    parser: str  # heavy lift — OM-A parsing (Sonnet)
    conversational: str  # light lift — bot intent routing (Haiku)


class LlmClientNotImplemented(NotImplementedError):
    """Raised by Phase 0 stubs to make the deferral obvious."""


def parser_complete(*_args: object, **_kwargs: object) -> str:
    """Phase 7 entry point — heavy completion via Sonnet."""
    raise LlmClientNotImplemented("Parser LLM client arrives in Phase 7")


def conversational_route(*_args: object, **_kwargs: object) -> str:
    """Phase 4 entry point — light completion via Haiku for bot routing."""
    raise LlmClientNotImplemented("Conversational LLM client arrives in Phase 4")
