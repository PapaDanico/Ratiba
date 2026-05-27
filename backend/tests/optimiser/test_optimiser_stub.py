"""Phase 0: optimiser is a stub. Phase 2 replaces this with real scenarios."""

from __future__ import annotations

import pytest

from app.services.optimiser import OptimiserNotImplemented, generate_roster


def test_generate_roster_is_stubbed() -> None:
    with pytest.raises(OptimiserNotImplemented):
        generate_roster()
