"""Phase 0: the FTL engine is a stub. Phase 1 replaces this with rule tests."""

from __future__ import annotations

import pytest

from app.services.ftl_engine import FtlEngineNotImplemented, check_fdp


def test_check_fdp_is_stubbed() -> None:
    with pytest.raises(FtlEngineNotImplemented):
        check_fdp()
