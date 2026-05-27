"""KCARs 2025 Part 8 FTL engine.

Phase 0 only sketches the public surface and the structured verdict shape;
each rule will be implemented as a pure function with explicit inputs in
Phase 1, with ≥1 pytest test per rule (see ``backend/tests/ftl/``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.ftl import LegalityState


@dataclass(frozen=True)
class FtlVerdict:
    """Structured verdict returned by every FTL rule function.

    Attributes:
        legality_state: aggregated state for this FDP (LEGAL .. ILLEGAL).
        rule_id: e.g. ``KCAR-P8-FDP-MAX-13H``.
        reason: human-readable justification, safe to surface to the user.
        regulation_ref: e.g. ``KCARs 2025 Part 8 §8.X.Y``.
        rules_applied: every rule_id evaluated to produce this verdict.
    """

    legality_state: LegalityState
    rule_id: str
    reason: str
    regulation_ref: str
    rules_applied: list[str] = field(default_factory=list)


class FtlEngineNotImplemented(NotImplementedError):
    """Raised by Phase 0 stubs to make missing rules obvious."""


def check_fdp(*_args: object, **_kwargs: object) -> FtlVerdict:
    """Phase 1 entry point — validate a single FDP against all applicable rules."""
    raise FtlEngineNotImplemented("FTL engine arrives in Phase 1")
