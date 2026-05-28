"""Self-serve demo workspace provisioning.

Creates an isolated operator + crewing-officer login pre-seeded with a
small, ready-to-use sandbox (crew, type ratings, fleet, and a few planned
routings) so an evaluator can immediately walk the golden path:
Routings → Auto-generate → Publish → PDF / payroll.

Isolation matters: each evaluator gets their own operator, so feedback
testers don't step on each other's data.
"""

from __future__ import annotations

import secrets
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Aircraft, Crew, CrewTypeRating, Operator, Sector, User
from app.models.crew import ContractType, CrewRole
from app.models.operator import OperatorTier
from app.models.roster import SectorStatus
from app.models.user import UserRole

_SEED_TYPE = "C208"
_BASE = "HKJK"

_SEED_CREW = (
    ("DEMO-CAP-01", "Amani", "Mwangi", CrewRole.CAPT),
    ("DEMO-CAP-02", "Zuri", "Otieno", CrewRole.CAPT),
    ("DEMO-FO-01", "Baraka", "Kamau", CrewRole.FO),
    ("DEMO-FO-02", "Neema", "Achieng", CrewRole.FO),
)
_SEED_REGS = ("5Y-DMA", "5Y-DMB")


class DemoWorkspaceError(Exception):
    """Raised when a workspace can't be provisioned (e.g. email already taken)."""


def create_workspace(
    session: Session,
    *,
    full_name: str,
    email: str,
    password: str,
    operator_name: str | None,
) -> tuple[Operator, User]:
    email = email.strip().lower()
    if session.scalar(select(User).where(User.email == email)) is not None:
        raise DemoWorkspaceError("an account with that email already exists")

    aoc = f"DEMO-{secrets.token_hex(3).upper()}"
    operator = Operator(
        aoc_number=aoc,
        name=(operator_name or f"{full_name.split()[0]}'s Air").strip()[:128] or "Demo Air",
        base=_BASE,
        contact_email=email,
        tier=OperatorTier.ENTRY,
    )
    session.add(operator)
    session.flush()

    user = User(
        operator_id=operator.id,
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name.strip()[:128] or "Demo Officer",
        role=UserRole.CREWING_OFFICER,
        is_active=True,
    )
    session.add(user)
    session.flush()

    _seed(session, operator=operator, user=user)
    session.commit()
    session.refresh(operator)
    session.refresh(user)
    return operator, user


def _seed(session: Session, *, operator: Operator, user: User) -> None:
    today = date.today()
    valid_from = today - timedelta(days=365)
    valid_until = today + timedelta(days=365)

    # Fleet.
    for reg in _SEED_REGS:
        session.add(
            Aircraft(
                operator_id=operator.id,
                created_by_user_id=user.id,
                registration=reg,
                aircraft_type=_SEED_TYPE,
                active=True,
            )
        )

    # Crew + type ratings on the common type so the auto-roster can assign them.
    for emp, first, last, role in _SEED_CREW:
        crew = Crew(
            operator_id=operator.id,
            created_by_user_id=user.id,
            employee_no=emp,
            first_name=first,
            last_name=last,
            role=role,
            date_of_hire=today - timedelta(days=900),
            date_of_birth=date(1988, 1, 1),
            base_station=_BASE,
            contract_type=ContractType.FULL_TIME,
            active=True,
            languages=["en", "sw"],
            faith_observance_flags={},
        )
        session.add(crew)
        session.flush()
        session.add(
            CrewTypeRating(
                operator_id=operator.id,
                created_by_user_id=user.id,
                crew_id=crew.id,
                aircraft_type=_SEED_TYPE,
                valid_from=valid_from,
                valid_until=valid_until,
                evidence_ref="DEMO",
            )
        )

    # A few PLANNED routings over the next 7 days (weekdays) so the evaluator
    # can immediately run Auto-generate and publish a roster.
    created = 0
    for offset in range(7):
        d = today + timedelta(days=offset)
        if d.weekday() >= 5:  # skip weekends
            continue
        std = datetime.combine(d, time(8, 0), tzinfo=UTC)
        sta = datetime.combine(d, time(10, 0), tzinfo=UTC)
        session.add(
            Sector(
                operator_id=operator.id,
                created_by_user_id=user.id,
                flight_no=f"DM{created + 1:03d}",
                date=d,
                origin=_BASE,
                destination="HKMO",
                std=std,
                sta=sta,
                aircraft_reg=_SEED_REGS[0],
                aircraft_type=_SEED_TYPE,
                status=SectorStatus.PLANNED,
            )
        )
        created += 1
