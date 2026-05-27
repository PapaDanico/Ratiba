"""Seed sample data for local development.

Phase 0 only inserts a single placeholder operator so the schema is
exercised end-to-end. Real fixtures land in Phase 1 alongside the FTL
engine.
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Operator, OperatorTier


def main() -> int:
    with SessionLocal() as session:
        existing = session.scalar(select(Operator).where(Operator.aoc_number == "DEV-AOC-001"))
        if existing is not None:
            print(f"Operator already present: {existing.name} ({existing.id})")
            return 0

        operator = Operator(
            aoc_number="DEV-AOC-001",
            name="Dev Aviation Ltd.",
            base="HKJK",
            contact_email="ops@dev-aviation.example.ke",
            tier=OperatorTier.ENTRY,
        )
        session.add(operator)
        session.commit()
        session.refresh(operator)
        print(f"Created operator: {operator.name} ({operator.id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
