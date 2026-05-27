"""LLM-driven OM-A FTL chapter parser.

Phase 0 skeleton only. The Claude Sonnet 4.5 pipeline + human-review interface
land in Phase 7 (post-pilot).
"""

from __future__ import annotations


class ConstraintParserNotImplemented(NotImplementedError):
    """Raised by Phase 0 stubs to make the deferral obvious."""


def parse_om_a(*_args: object, **_kwargs: object) -> None:
    """Phase 7 entry point — parse an OM-A FTL chapter into a constraint set."""
    raise ConstraintParserNotImplemented("Constraint parser arrives in Phase 7")
