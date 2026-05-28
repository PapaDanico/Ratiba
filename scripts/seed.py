"""Seed sample data for local development.

Creates one operator and one Crewing Officer user that the Phase 3 dashboard
and the Playwright E2E flow can log in as.

Idempotent — safe to re-run.
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Operator, User
from app.models.operator import OperatorTier
from app.models.user import UserRole

DEFAULT_OPERATOR_AOC = "DEV-AOC-001"
DEFAULT_USER_EMAIL = "officer@example.aero"
DEFAULT_USER_PASSWORD = "hunter2pass"


def main() -> int:
    with SessionLocal() as session:
        operator = session.scalar(
            select(Operator).where(Operator.aoc_number == DEFAULT_OPERATOR_AOC)
        )
        if operator is None:
            operator = Operator(
                aoc_number=DEFAULT_OPERATOR_AOC,
                name="Dev Aviation Ltd.",
                base="HKJK",
                contact_email="ops@dev-aviation.example.ke",
                tier=OperatorTier.ENTRY,
            )
            session.add(operator)
            session.commit()
            session.refresh(operator)
            print(f"Created operator: {operator.name} ({operator.id})")
        else:
            print(f"Operator already present: {operator.name} ({operator.id})")

        user = session.scalar(select(User).where(User.email == DEFAULT_USER_EMAIL))
        if user is None:
            user = User(
                operator_id=operator.id,
                email=DEFAULT_USER_EMAIL,
                hashed_password=hash_password(DEFAULT_USER_PASSWORD),
                full_name="Dev Crewing Officer",
                role=UserRole.CREWING_OFFICER,
                is_active=True,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"Created user: {user.email} (login with password {DEFAULT_USER_PASSWORD!r})")
        else:
            print(f"User already present: {user.email}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
