"""Seed sample data for local development.

Two modes:

- Default (``python scripts/seed.py``) — one operator + one Crewing
  Officer. Minimum needed to log in and click around.
- Demo (``python scripts/seed.py --demo``) — two fictional operators,
  multiple crew across roles, type ratings, currencies spanning the
  GREEN/AMBER/RED traffic-light states, 28 days of sectors with a
  published roster covering the past 14 days, pending + approved leave,
  one pending swap, and a generated audit pack. Built so a prospective
  user can poke at every dashboard screen and see realistic data.

Idempotent in both modes — safe to re-run.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    Aircraft,
    Crew,
    CrewCurrency,
    CrewTypeRating,
    LeaveRequest,
    Notice,
    Operator,
    SwapRequest,
    User,
)
from app.models.crew import ContractType, CrewRole
from app.models.leave import LeaveStatus, LeaveType
from app.models.notice import NoticeCategory, NoticeSeverity
from app.models.operator import OperatorTier
from app.models.swap import SwapStatus
from app.models.training import CurrencyType
from app.models.user import UserRole
from app.schemas.roster import AssignmentOut, PublishRosterRequest, SectorInputIn
from app.services import audit_pack, roster_service

DEFAULT_OPERATOR_AOC = "DEV-AOC-001"
DEFAULT_USER_EMAIL = "officer@example.aero"
DEFAULT_USER_PASSWORD = "hunter2pass"


@dataclass(frozen=True)
class DemoCrew:
    employee_no: str
    first_name: str
    last_name: str
    role: CrewRole
    languages: tuple[str, ...] = ("en", "sw")
    sunday_protected: bool = False


@dataclass(frozen=True)
class DemoOperator:
    aoc_number: str
    name: str
    base: str
    tier: OperatorTier
    contact_email: str
    crew: tuple[DemoCrew, ...]
    aircraft_regs: tuple[str, ...]
    aircraft_type: str


# Two clearly fictional Kenyan-flavoured operators. Names chosen so they
# can't be confused with any real AOC holder.
DEMO_OPERATORS: tuple[DemoOperator, ...] = (
    DemoOperator(
        aoc_number="DEMO-AOC-AC",
        name="Acacia Air",
        base="HKJK",
        tier=OperatorTier.STANDARD,
        contact_email="ops@acacia-demo.example.aero",
        aircraft_regs=("5Y-DM1", "5Y-DM2", "5Y-DM3"),
        aircraft_type="DH8D",
        crew=(
            DemoCrew("AC-CAP-01", "Wanjiku", "Kamau", CrewRole.CAPT),
            DemoCrew("AC-CAP-02", "Achieng", "Otieno", CrewRole.CAPT),
            DemoCrew("AC-CAP-03", "Faraja", "Mwangi", CrewRole.CAPT, sunday_protected=True),
            DemoCrew("AC-CAP-04", "Baraka", "Kiprotich", CrewRole.CAPT),
            DemoCrew("AC-CAP-05", "Zawadi", "Njoroge", CrewRole.CAPT),
            DemoCrew("AC-FO-01", "Imani", "Wairimu", CrewRole.FO),
            DemoCrew("AC-FO-02", "Tumaini", "Onyango", CrewRole.FO),
            DemoCrew("AC-FO-03", "Sifa", "Maina", CrewRole.FO),
            DemoCrew("AC-FO-04", "Furaha", "Cheruiyot", CrewRole.FO),
            DemoCrew("AC-FO-05", "Neema", "Akinyi", CrewRole.FO),
        ),
    ),
    DemoOperator(
        aoc_number="DEMO-AOC-MA",
        name="Maendeleo Aviation",
        base="HKWJ",
        tier=OperatorTier.ENTRY,
        contact_email="ops@maendeleo-demo.example.aero",
        aircraft_regs=("5Y-DA1", "5Y-DA2"),
        aircraft_type="ATR72",
        crew=(
            DemoCrew("MA-CAP-01", "Salim", "Ali", CrewRole.CAPT),
            DemoCrew("MA-CAP-02", "Halima", "Mohammed", CrewRole.CAPT),
            DemoCrew("MA-CAP-03", "Daudi", "Karanja", CrewRole.CAPT),
            DemoCrew("MA-FO-01", "Mwajuma", "Hassan", CrewRole.FO),
            DemoCrew("MA-FO-02", "Juma", "Ndegwa", CrewRole.FO),
            DemoCrew("MA-FO-03", "Pendo", "Kibet", CrewRole.FO),
        ),
    ),
)


def _ensure(session: Session, *, aoc_number: str, **kwargs: Any) -> Operator:
    op = session.scalar(select(Operator).where(Operator.aoc_number == aoc_number))
    if op is None:
        op = Operator(aoc_number=aoc_number, **kwargs)
        session.add(op)
        session.commit()
        session.refresh(op)
    return op


def _ensure_user(
    session: Session,
    *,
    operator: Operator,
    email: str,
    full_name: str,
    role: UserRole,
    password: str,
) -> User:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            operator_id=operator.id,
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def _ensure_crew(session: Session, *, operator: Operator, spec: DemoCrew, hire_date: date) -> Crew:
    crew = session.scalar(
        select(Crew)
        .where(Crew.operator_id == operator.id)
        .where(Crew.employee_no == spec.employee_no)
    )
    if crew is None:
        crew = Crew(
            operator_id=operator.id,
            employee_no=spec.employee_no,
            first_name=spec.first_name,
            last_name=spec.last_name,
            role=spec.role,
            date_of_hire=hire_date,
            date_of_birth=date(1985, 6, 15),
            base_station=operator.base,
            contract_type=ContractType.FULL_TIME,
            active=True,
            languages=list(spec.languages),
            faith_observance_flags={"sunday_protected": spec.sunday_protected}
            if spec.sunday_protected
            else {},
        )
        session.add(crew)
        session.commit()
        session.refresh(crew)
    return crew


def _ensure_type_rating(
    session: Session,
    *,
    operator: Operator,
    crew: Crew,
    aircraft_type: str,
    today: date,
) -> None:
    existing = session.scalar(
        select(CrewTypeRating)
        .where(CrewTypeRating.crew_id == crew.id)
        .where(CrewTypeRating.aircraft_type == aircraft_type)
    )
    if existing is not None:
        return
    session.add(
        CrewTypeRating(
            operator_id=operator.id,
            crew_id=crew.id,
            aircraft_type=aircraft_type,
            valid_from=today - timedelta(days=365 * 3),
            valid_until=today + timedelta(days=365 * 2),
            evidence_ref="DEMO-TR",
        )
    )
    session.commit()


def _ensure_currencies(
    session: Session, *, operator: Operator, crew: Crew, today: date, profile: int
) -> None:
    """Three currencies per crew with a deterministic GREEN/AMBER/RED mix."""
    plan = [
        (CurrencyType.OPC, today - timedelta(days=180), today + timedelta(days=200)),
        (CurrencyType.LPC, today - timedelta(days=30), today + timedelta(days=15)),
        (
            CurrencyType.LANDINGS_90D,
            today - timedelta(days=120),
            today - timedelta(days=5),
        ),
    ]
    # Shift the AMBER / RED currencies to a subset of crew so the dashboard
    # has a mix instead of every pilot flashing red.
    if profile % 4 == 0:
        plan[1] = (CurrencyType.LPC, today - timedelta(days=10), today + timedelta(days=120))
        plan[2] = (CurrencyType.LANDINGS_90D, today - timedelta(days=5), today + timedelta(days=60))
    elif profile % 4 == 1:
        plan[2] = (
            CurrencyType.LANDINGS_90D,
            today - timedelta(days=10),
            today + timedelta(days=45),
        )

    existing_types = {
        c.currency_type
        for c in session.scalars(select(CrewCurrency).where(CrewCurrency.crew_id == crew.id)).all()
    }
    for ctype, last, expires in plan:
        if ctype in existing_types:
            continue
        session.add(
            CrewCurrency(
                operator_id=operator.id,
                crew_id=crew.id,
                currency_type=ctype,
                last_completed_date=last,
                expires_date=expires,
                evidence_ref="DEMO",
            )
        )
    session.commit()


def _publish_demo_roster(
    session: Session,
    *,
    user: User,
    operator: DemoOperator,
    today: date,
) -> int:
    """Publish 14 days of past sectors + 14 days of future sectors.

    Captains rotate across crew, FOs rotate independently — produces a
    visually-pleasing roster grid that doesn't trivially repeat.
    """
    captains = [c.employee_no for c in operator.crew if c.role == CrewRole.CAPT]
    fos = [c.employee_no for c in operator.crew if c.role == CrewRole.FO]
    horizon_from = today - timedelta(days=14)
    horizon_to = today + timedelta(days=13)

    sectors: list[SectorInputIn] = []
    assignments: list[AssignmentOut] = []
    counter = 0
    for d_off in range(28):
        d = horizon_from + timedelta(days=d_off)
        for a_idx, reg in enumerate(operator.aircraft_regs):
            std = datetime.combine(d, time(6, 0), tzinfo=UTC) + timedelta(hours=a_idx * 2)
            for sector_idx in range(2):
                seg_std = std + timedelta(hours=sector_idx * 2)
                seg_sta = seg_std + timedelta(hours=1, minutes=45)
                # flight_no is VARCHAR(16); keep the demo id compact but
                # operator-distinct via the AOC's trailing segment.
                sector_id = f"{operator.aoc_number.split('-')[-1]}-S{counter:04d}"
                counter += 1
                sectors.append(
                    SectorInputIn(
                        sector_id=sector_id,
                        date_local=d,
                        std=seg_std,
                        sta=seg_sta,
                        aircraft_reg=reg,
                        aircraft_type=operator.aircraft_type,
                        block_hours=Decimal("1.75"),
                    )
                )
            cap_idx = (d_off + a_idx) % len(captains)
            fo_idx = (d_off + a_idx * 2) % len(fos)
            assignments.append(
                AssignmentOut(
                    duty_day_key=f"{reg}|{d.isoformat()}",
                    date_local=d,
                    aircraft_reg=reg,
                    aircraft_type=operator.aircraft_type,
                    sector_ids=[s.sector_id for s in sectors[-2:]],
                    captain_id=captains[cap_idx],
                    fo_id=fos[fo_idx],
                )
            )

    payload = PublishRosterRequest(
        horizon_from=horizon_from,
        horizon_to=horizon_to,
        sectors=sectors,
        assignments=assignments,
    )
    roster_service.publish_roster(session, user=user, payload=payload)
    return len(assignments)


def _ensure_leave_and_swap(
    session: Session,
    *,
    operator_id: uuid.UUID,
    crew_by_emp: dict[str, Crew],
    today: date,
) -> None:
    if session.scalar(select(LeaveRequest).where(LeaveRequest.operator_id == operator_id)):
        return

    samples = [
        (
            "AC-FO-02" if "AC-FO-02" in crew_by_emp else next(iter(crew_by_emp)),
            LeaveType.ANNUAL,
            LeaveStatus.PENDING,
            "Family event abroad",
        ),
        (
            "AC-CAP-03" if "AC-CAP-03" in crew_by_emp else next(iter(crew_by_emp)),
            LeaveType.FAITH,
            LeaveStatus.APPROVED,
            "Religious observance",
        ),
    ]
    for emp, ltype, status, note in samples:
        crew = crew_by_emp.get(emp)
        if crew is None:
            continue
        session.add(
            LeaveRequest(
                operator_id=operator_id,
                crew_id=crew.id,
                type=ltype,
                date_from=today + timedelta(days=7),
                date_to=today + timedelta(days=10),
                note=note,
                status=status,
            )
        )

    crew_ids = list(crew_by_emp.values())
    if len(crew_ids) >= 2:
        session.add(
            SwapRequest(
                operator_id=operator_id,
                crew_id_initiator=crew_ids[0].id,
                crew_id_counterparty=crew_ids[1].id,
                fdp_or_sector_ref=f"5Y-DM1|{today.isoformat()}",
                reason="Personal commitment — would appreciate the swap.",
                status=SwapStatus.PENDING,
            )
        )
    session.commit()


def _ensure_fleet(
    session: Session, *, operator_id: uuid.UUID, demo: DemoOperator, user_id: uuid.UUID
) -> None:
    for reg in demo.aircraft_regs:
        existing = session.scalar(
            select(Aircraft)
            .where(Aircraft.operator_id == operator_id)
            .where(Aircraft.registration == reg)
        )
        if existing is None:
            session.add(
                Aircraft(
                    operator_id=operator_id,
                    created_by_user_id=user_id,
                    registration=reg,
                    aircraft_type=demo.aircraft_type,
                    active=True,
                )
            )
    session.commit()


def _ensure_notices(session: Session, *, operator_id: uuid.UUID, user_id: uuid.UUID) -> None:
    if session.scalar(select(Notice).where(Notice.operator_id == operator_id)):
        return
    samples = [
        (
            NoticeCategory.OPERATIONAL,
            NoticeSeverity.IMPORTANT,
            "Revised winter ops procedures",
            "From Monday, all departures before 07:00 local require a "
            "de-icing check sign-off. See OM-A 8.4 for the revised checklist.",
            True,
            True,
        ),
        (
            NoticeCategory.FLEET,
            NoticeSeverity.INFO,
            "5Y-DM2 returns from C-check",
            "5Y-DM2 is back on line from Thursday. Roster has been updated "
            "to reflect availability.",
            False,
            False,
        ),
        (
            NoticeCategory.SAFETY,
            NoticeSeverity.CRITICAL,
            "Bird activity — HKJK approach",
            "Increased bird activity reported on short final RWY 06. "
            "Heightened vigilance on approach and landing. Acknowledge receipt.",
            True,
            False,
        ),
        (
            NoticeCategory.SOCIAL,
            NoticeSeverity.INFO,
            "Crew room: end-of-month get-together 🎉",
            "Drinks + nyama choma at the crew lounge, last Friday of the "
            "month from 18:00. All crew + families welcome.",
            False,
            False,
        ),
    ]
    from datetime import UTC, datetime

    for category, severity, title, body, requires_ack, pinned in samples:
        session.add(
            Notice(
                operator_id=operator_id,
                created_by_user_id=user_id,
                category=category,
                severity=severity,
                title=title,
                body=body,
                requires_ack=requires_ack,
                pinned=pinned,
                published=True,
                published_at=datetime.now(UTC),
            )
        )
    session.commit()


def _generate_demo_audit_pack(session: Session, *, user: User, today: date) -> None:
    audit_pack.generate_pack(
        session,
        user=user,
        period_from=today - timedelta(days=89),
        period_to=today,
    )


def _seed_default(session: Session) -> None:
    """Single operator + crewing officer — the minimum to log in."""
    op = _ensure(
        session,
        aoc_number=DEFAULT_OPERATOR_AOC,
        name="Dev Aviation Ltd.",
        base="HKJK",
        contact_email="ops@dev-aviation.example.ke",
        tier=OperatorTier.ENTRY,
    )
    _ensure_user(
        session,
        operator=op,
        email=DEFAULT_USER_EMAIL,
        full_name="Dev Crewing Officer",
        role=UserRole.CREWING_OFFICER,
        password=DEFAULT_USER_PASSWORD,
    )
    print(f"Default seed ready. Log in as {DEFAULT_USER_EMAIL} / {DEFAULT_USER_PASSWORD}")


def _seed_demo(session: Session) -> None:
    today = date.today()
    for demo in DEMO_OPERATORS:
        op_row = _ensure(
            session,
            aoc_number=demo.aoc_number,
            name=demo.name,
            base=demo.base,
            contact_email=demo.contact_email,
            tier=demo.tier,
        )
        officer = _ensure_user(
            session,
            operator=op_row,
            email=f"officer@{demo.aoc_number.lower()}.example.aero",
            full_name=f"{demo.name} Crewing Officer",
            role=UserRole.CREWING_OFFICER,
            password=DEFAULT_USER_PASSWORD,
        )
        _ensure_user(
            session,
            operator=op_row,
            email=f"chief@{demo.aoc_number.lower()}.example.aero",
            full_name=f"{demo.name} Chief Pilot",
            role=UserRole.CHIEF_PILOT,
            password=DEFAULT_USER_PASSWORD,
        )
        for idx, spec in enumerate(demo.crew):
            crew = _ensure_crew(
                session,
                operator=op_row,
                spec=spec,
                hire_date=today - timedelta(days=365 * (idx % 5 + 1)),
            )
            _ensure_type_rating(
                session,
                operator=op_row,
                crew=crew,
                aircraft_type=demo.aircraft_type,
                today=today,
            )
            _ensure_currencies(session, operator=op_row, crew=crew, today=today, profile=idx)

        crew_by_emp = {
            c.employee_no: c
            for c in session.scalars(select(Crew).where(Crew.operator_id == op_row.id)).all()
        }
        _ensure_leave_and_swap(session, operator_id=op_row.id, crew_by_emp=crew_by_emp, today=today)
        _ensure_fleet(session, operator_id=op_row.id, demo=demo, user_id=officer.id)
        _ensure_notices(session, operator_id=op_row.id, user_id=officer.id)

        # Roster publish is idempotent — but generating it twice creates two
        # GENERATE_AUDIT_PACK + PUBLISH_ROSTER audit events, which is the
        # right behaviour for re-runs.
        try:
            count = _publish_demo_roster(session, user=officer, operator=demo, today=today)
            print(f"  Published {count} duty-day assignments for {demo.name}.")
        except Exception as exc:
            print(f"  Roster publish skipped for {demo.name}: {exc}")

        try:
            _generate_demo_audit_pack(session, user=officer, today=today)
            print(f"  Generated 90-day audit pack for {demo.name}.")
        except Exception as exc:
            print(f"  Audit pack generation skipped for {demo.name}: {exc}")

    # The flagship Jetways Airlines demo (dual-Fokker fleet, night cargo,
    # 27-pilot establishment) lives in its own module — richer than the
    # uniform DemoOperator shape allows.
    try:
        from seed_jetways import seed_jetways

        summary = seed_jetways(session)
        print(
            f"  Seeded Jetways Airlines: {summary['crew']} pilots, "
            f"{summary['aircraft']} aircraft, {summary['assignments']} assignments."
        )
    except Exception as exc:  # never let Jetways break the core demo seed
        print(f"  Jetways seed skipped: {exc}")

    print()
    print("Demo seed ready. Operators populated:")
    for demo in DEMO_OPERATORS:
        print(
            f"  {demo.name:<22} → officer@{demo.aoc_number.lower()}.example.aero "
            f"/ {DEFAULT_USER_PASSWORD}"
        )
    print(
        f"  {'Jetways Airlines Ltd':<22} → officer@jetways.example.aero / {DEFAULT_USER_PASSWORD}"
    )
    print()
    print(
        "Each operator has crew with mixed currency states, a 28-day "
        "published roster, pending + approved leave, a pending swap, and a "
        "90-day audit pack ready to download."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Populate two fictional operators with rich demo data.",
    )
    parser.add_argument(
        "--jetways",
        action="store_true",
        help="Seed only the Jetways Airlines demo workspace.",
    )
    args = parser.parse_args(argv)

    with SessionLocal() as session:
        if args.jetways:
            from seed_jetways import seed_jetways

            seed_jetways(session)
        elif args.demo:
            _seed_demo(session)
        else:
            _seed_default(session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
