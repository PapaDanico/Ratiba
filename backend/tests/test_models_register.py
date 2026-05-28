"""Phase 0 acceptance — every Section 4 table is registered on Base metadata."""

from __future__ import annotations

import app.models  # noqa: F401 — populates Base.metadata
from app.core.database import Base

EXPECTED_TABLES = {
    "operators",
    "users",
    "crew",
    "crew_type_ratings",
    "crew_currencies",
    "sectors",
    "sector_assignments",
    "flight_duty_periods",
    "ftl_rules",
    "leave_requests",
    "swap_requests",
    "audit_events",
}


def test_every_section_4_table_is_registered() -> None:
    registered = set(Base.metadata.tables.keys())
    missing = EXPECTED_TABLES - registered
    assert not missing, f"missing tables: {missing}"
