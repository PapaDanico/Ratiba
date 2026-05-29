"""Seed the *Jetways Airlines* live-demo workspace.

A data-authentic demo operator built from the JAL/CMS handover brief: a
dual-Fokker fleet (F50/F70/F100), an anonymised 27-pilot establishment
(CPT-001..012, FO-001..015), a daily Somalia night-cargo programme, a
published roster mixing night-cargo and daytime pax duties, training /
medical expiries that drive the currency dashboard, and an operator FTL
scheme (KCAR Part 8 hard limits) layered over the generic baseline.

Idempotent — safe to run on every deploy. Login after seeding:

    officer@jetways.example.aero / hunter2pass   (Crewing Officer)
    chief@jetways.example.aero   / hunter2pass   (Chief Pilot)

Airport ICAO codes are the authoritative real-world values (e.g. Mogadishu
HCMM, Hargeisa HCMH, Galcaio HCMR), which differ from a few codes in the
source brief; corrected here for accuracy.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

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
    Posting,
    SwapRequest,
    User,
)
from app.models.constraint import (
    ConstraintReviewStatus,
    ConstraintRule,
    ConstraintSet,
    ConstraintSetStatus,
)
from app.models.crew import ContractType, CrewRole
from app.models.document import CrewDocument, DocumentType
from app.models.leave import LeaveStatus, LeaveType
from app.models.notice import NoticeCategory, NoticeSeverity
from app.models.operator import OperatorTier
from app.models.posting import PostingType
from app.models.swap import SwapStatus
from app.models.training import CurrencyType
from app.models.user import UserRole
from app.schemas.roster import AssignmentOut, PublishRosterRequest, SectorInputIn
from app.services import audit_pack, roster_service
from app.services import postings as postings_service

EAT = ZoneInfo("Africa/Nairobi")

OPERATOR_AOC = "JWX-265"
OFFICER_EMAIL = "officer@jetways.example.aero"
CHIEF_EMAIL = "chief@jetways.example.aero"
PASSWORD = "hunter2pass"


@dataclass(frozen=True)
class PilotSpec:
    pilot_id: str
    role: CrewRole
    fleets: tuple[str, ...]  # type ratings held, e.g. ("F70", "F100")
    night_pct: int
    medical_expiry: date
    opc_lpc_due: date
    retention_risk: str
    title: str = ""
    flags: str = ""
    cargo: bool = False


def _d(y: int, m: int, day: int) -> date:
    return date(y, m, day)


# ── Establishment (anonymised) — verbatim from the handover brief ──────────
CAPTAINS: tuple[PilotSpec, ...] = (
    PilotSpec(
        "CPT-001",
        CrewRole.CAPT,
        ("F70", "F100"),
        28,
        _d(2026, 11, 30),
        _d(2026, 11, 15),
        "Low",
        "Head of Operations",
        "Post-holder; key-man dependency",
    ),
    PilotSpec(
        "CPT-002",
        CrewRole.CAPT,
        ("F70", "F100"),
        31,
        _d(2026, 10, 31),
        _d(2026, 10, 31),
        "Low",
        "Senior Captain",
    ),
    PilotSpec(
        "CPT-003",
        CrewRole.CAPT,
        ("F70", "F100"),
        24,
        _d(2026, 9, 30),
        _d(2026, 9, 30),
        "Medium",
        "Head of Training / Capt",
        "Dual post load",
    ),
    PilotSpec(
        "CPT-004",
        CrewRole.CAPT,
        ("F70", "F100"),
        18,
        _d(2027, 2, 28),
        _d(2027, 1, 31),
        "Low",
        "SFI / Check Captain",
        "Simulator authority",
    ),
    PilotSpec(
        "CPT-005",
        CrewRole.CAPT,
        ("F70", "F100"),
        84,
        _d(2026, 7, 31),
        _d(2026, 6, 30),
        "High",
        "Captain",
        "Medical expiry imminent — URGENT renewal",
        cargo=True,
    ),
    PilotSpec(
        "CPT-006",
        CrewRole.CAPT,
        ("F70", "F100"),
        22,
        _d(2026, 12, 31),
        _d(2026, 12, 15),
        "Low",
        "Captain",
        cargo=True,
    ),
    PilotSpec(
        "CPT-007",
        CrewRole.CAPT,
        ("F50", "F70"),
        91,
        _d(2027, 1, 31),
        _d(2026, 12, 31),
        "Critical",
        "Captain",
        "Highest night-departure rate in fleet (91%); FRMS review required",
        cargo=True,
    ),
    PilotSpec(
        "CPT-008",
        CrewRole.CAPT,
        ("F50", "F70"),
        84,
        _d(2027, 3, 31),
        _d(2027, 2, 28),
        "High",
        "Captain",
        "16-day consecutive duty streak recorded",
        cargo=True,
    ),
    PilotSpec(
        "CPT-009",
        CrewRole.CAPT,
        ("F50", "F70"),
        26,
        _d(2026, 9, 30),
        _d(2026, 9, 30),
        "Medium",
        "Captain",
        cargo=True,
    ),
    PilotSpec(
        "CPT-010",
        CrewRole.CAPT,
        ("F70", "F100"),
        27,
        _d(2026, 10, 31),
        _d(2026, 10, 31),
        "Medium",
        "Captain",
    ),
    PilotSpec(
        "CPT-011",
        CrewRole.CAPT,
        ("F70", "F100"),
        15,
        _d(2027, 4, 30),
        _d(2027, 3, 31),
        "Low",
        "SFI / Check Captain",
        "Simulator authority",
    ),
    PilotSpec(
        "CPT-012",
        CrewRole.CAPT,
        ("F70",),
        19,
        _d(2027, 6, 30),
        _d(2026, 9, 30),
        "High",
        "Captain (recent conversion)",
        "Supervised line flying — paired ops only",
    ),
)

FIRST_OFFICERS: tuple[PilotSpec, ...] = (
    PilotSpec("FO-001", CrewRole.FO, ("F50", "F70"), 29, _d(2026, 8, 31), _d(2026, 8, 31), "Low"),
    PilotSpec(
        "FO-002",
        CrewRole.FO,
        ("F50", "F70"),
        83,
        _d(2027, 2, 28),
        _d(2026, 12, 31),
        "High",
        flags="Night-cargo lead FO; FRMS review due",
        cargo=True,
    ),
    PilotSpec(
        "FO-003",
        CrewRole.FO,
        ("F50",),
        26,
        _d(2027, 1, 31),
        _d(2026, 11, 30),
        "Low",
        flags="Highest total flying days in fleet",
        cargo=True,
    ),
    PilotSpec(
        "FO-004",
        CrewRole.FO,
        ("F50", "F70"),
        31,
        _d(2026, 11, 30),
        _d(2026, 11, 30),
        "Low",
        cargo=True,
    ),
    PilotSpec("FO-005", CrewRole.FO, ("F50",), 28, _d(2027, 3, 31), _d(2027, 1, 31), "Low"),
    PilotSpec("FO-006", CrewRole.FO, ("F50",), 32, _d(2026, 10, 31), _d(2026, 10, 31), "Medium"),
    PilotSpec(
        "FO-007",
        CrewRole.FO,
        ("F50", "F70"),
        84,
        _d(2026, 12, 31),
        _d(2026, 11, 30),
        "High",
        flags="16-day consecutive streak recorded",
        cargo=True,
    ),
    PilotSpec("FO-008", CrewRole.FO, ("F50", "F70"), 27, _d(2026, 9, 30), _d(2026, 9, 30), "Low"),
    PilotSpec("FO-009", CrewRole.FO, ("F50",), 33, _d(2027, 2, 28), _d(2026, 12, 31), "Low"),
    PilotSpec("FO-010", CrewRole.FO, ("F50",), 25, _d(2027, 1, 31), _d(2026, 10, 31), "Low"),
    PilotSpec("FO-011", CrewRole.FO, ("F50",), 30, _d(2026, 11, 30), _d(2026, 11, 30), "Medium"),
    PilotSpec("FO-012", CrewRole.FO, ("F50",), 28, _d(2027, 4, 30), _d(2027, 3, 31), "Low"),
    PilotSpec("FO-013", CrewRole.FO, ("F50",), 24, _d(2026, 10, 31), _d(2026, 9, 30), "Low"),
    PilotSpec("FO-014", CrewRole.FO, ("F50",), 27, _d(2027, 3, 31), _d(2027, 2, 28), "Low"),
    PilotSpec(
        "FO-015",
        CrewRole.FO,
        ("F50",),
        29,
        _d(2026, 12, 31),
        _d(2026, 12, 31),
        "Medium",
        flags="Recent type rating — supervised ops",
    ),
)

ALL_PILOTS = CAPTAINS + FIRST_OFFICERS


@dataclass(frozen=True)
class FleetTail:
    registration: str
    aircraft_type: str
    active: bool = True
    note: str = ""


# 8 tails. The three brief-anonymised tails (REG-006/007/008) get plausible
# 5Y- demo registrations. 5Y-JWF is the F50 in its C-check (inactive).
FLEET: tuple[FleetTail, ...] = (
    FleetTail("5Y-JET", "F100", True, "Primary revenue aircraft — high-density regional"),
    FleetTail("5Y-JEA", "F70", True, "Charter + scheduled; most versatile"),
    FleetTail("5Y-SKC", "F50", True, "Highest roster utilisation — domestic pax"),
    FleetTail("5Y-CAR", "F50", True, "Dedicated night cargo — Somalia programme"),
    FleetTail("5Y-CMB", "F50", True, "Combi — pax fwd / cargo aft"),
    FleetTail("5Y-JWF", "F50", False, "In C-check — return planned Q3 2026"),
    FleetTail("5Y-JWG", "F70", True, "Regional scheduled + ACMI"),
    FleetTail("5Y-JWH", "F100", True, "High-frequency routes; recent avionics upgrade"),
)


def _get_or_create(session: Session, model: type, defaults: dict | None = None, **keys):
    obj = session.scalar(select(model).filter_by(**keys))
    if obj is not None:
        return obj, False
    params = {**keys, **(defaults or {})}
    obj = model(**params)
    session.add(obj)
    session.flush()
    return obj, True


def _eat(d: date, hour: int, minute: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=EAT)


def _pick(pool: list[str], used: set[str], i: int, offset: int = 0) -> str:
    n = len(pool)
    for k in range(n):
        cand = pool[(i + offset + k) % n]
        if cand not in used:
            used.add(cand)
            return cand
    cand = pool[(i + offset) % n]
    used.add(cand)
    return cand


def seed_jetways(session: Session) -> dict[str, int]:
    """Idempotently seed the Jetways Airlines demo workspace."""
    today = date.today()

    operator, _ = _get_or_create(
        session,
        Operator,
        defaults={
            "name": "Jetways Airlines Limited",
            "base": "HKJK",
            "contact_email": "ops@jetways.example.aero",
            "tier": OperatorTier.PLUS,
        },
        aoc_number=OPERATOR_AOC,
    )

    officer, _ = _get_or_create(
        session,
        User,
        defaults={
            "hashed_password": hash_password(PASSWORD),
            "full_name": "Jetways Crewing Officer",
            "role": UserRole.CREWING_OFFICER,
            "is_active": True,
        },
        operator_id=operator.id,
        email=OFFICER_EMAIL,
    )
    _get_or_create(
        session,
        User,
        defaults={
            "hashed_password": hash_password(PASSWORD),
            "full_name": "Jetways Chief Pilot",
            "role": UserRole.CHIEF_PILOT,
            "is_active": True,
        },
        operator_id=operator.id,
        email=CHIEF_EMAIL,
    )

    # ── Fleet ──
    for tail in FLEET:
        _get_or_create(
            session,
            Aircraft,
            defaults={
                "aircraft_type": tail.aircraft_type,
                "active": tail.active,
                "created_by_user_id": officer.id,
            },
            operator_id=operator.id,
            registration=tail.registration,
        )

    # ── Crew + ratings + currencies + documents ──
    crew_by_id: dict[str, Crew] = {}
    for idx, p in enumerate(ALL_PILOTS):
        number = p.pilot_id.split("-")[1]
        crew, created = _get_or_create(
            session,
            Crew,
            defaults={
                "first_name": "Captain" if p.role is CrewRole.CAPT else "First Officer",
                "last_name": number,
                "role": p.role,
                "date_of_hire": date(
                    today.year - 4 - (idx % 6), ((idx * 3) % 12) + 1, ((idx * 5) % 27) + 1
                ),
                "date_of_birth": date(
                    1972 + (idx % 18), ((idx * 5) % 12) + 1, ((idx * 7) % 27) + 1
                ),
                "base_station": "HKJK" if "F100" in p.fleets or "F70" in p.fleets else "HKNW",
                "contract_type": ContractType.FULL_TIME,
                "active": True,
                "languages": ["en", "sw"],
                "faith_observance_flags": {},
            },
            operator_id=operator.id,
            employee_no=p.pilot_id,
        )
        crew_by_id[p.pilot_id] = crew
        if not created:
            continue

        for ac_type in p.fleets:
            recent = p.pilot_id == "CPT-012"
            _get_or_create(
                session,
                CrewTypeRating,
                defaults={
                    "valid_from": today - timedelta(days=120 if recent else 1095),
                    "valid_until": today + timedelta(days=730),
                    "evidence_ref": f"TR-{p.pilot_id}-{ac_type}",
                },
                operator_id=operator.id,
                crew_id=crew.id,
                aircraft_type=ac_type,
            )

        # Recurrent checks — OPC (annual), LPC (6-monthly), 90-day landings.
        _get_or_create(
            session,
            CrewCurrency,
            defaults={
                "last_completed_date": p.opc_lpc_due - timedelta(days=365),
                "expires_date": p.opc_lpc_due,
                "evidence_ref": "DEMO",
            },
            operator_id=operator.id,
            crew_id=crew.id,
            currency_type=CurrencyType.OPC,
        )
        _get_or_create(
            session,
            CrewCurrency,
            defaults={
                "last_completed_date": p.opc_lpc_due - timedelta(days=182),
                "expires_date": p.opc_lpc_due - timedelta(days=14),
                "evidence_ref": "DEMO",
            },
            operator_id=operator.id,
            crew_id=crew.id,
            currency_type=CurrencyType.LPC,
        )
        _get_or_create(
            session,
            CrewCurrency,
            defaults={
                "last_completed_date": today - timedelta(days=30 + (idx % 55)),
                "expires_date": today - timedelta(days=30 + (idx % 55)) + timedelta(days=90),
                "evidence_ref": "DEMO",
            },
            operator_id=operator.id,
            crew_id=crew.id,
            currency_type=CurrencyType.LANDINGS_90D,
        )
        if p.cargo:
            _get_or_create(
                session,
                CrewCurrency,
                defaults={
                    "last_completed_date": today - timedelta(days=300 + idx),
                    "expires_date": today - timedelta(days=300 + idx) + timedelta(days=730),
                    "evidence_ref": "DGR CAT 6",
                },
                operator_id=operator.id,
                crew_id=crew.id,
                currency_type=CurrencyType.DG,
            )

        # Documents — KCAA Class 1 medical + licence.
        _get_or_create(
            session,
            CrewDocument,
            defaults={
                "document_number": f"MED-{number}",
                "issuing_authority": "KCAA",
                "issue_date": p.medical_expiry - timedelta(days=182),
                "expiry_date": p.medical_expiry,
                "notes": "Class 1 medical certificate",
            },
            operator_id=operator.id,
            crew_id=crew.id,
            doc_type=DocumentType.MEDICAL,
        )
        _get_or_create(
            session,
            CrewDocument,
            defaults={
                "document_number": f"{'ATPL' if p.role is CrewRole.CAPT else 'CPL'}-{number}",
                "issuing_authority": "KCAA",
                "issue_date": today - timedelta(days=900),
                "expiry_date": today + timedelta(days=900),
                "notes": p.flags or None,
            },
            operator_id=operator.id,
            crew_id=crew.id,
            doc_type=DocumentType.LICENCE,
        )

    # ── Cabin crew + accompanying engineers ──
    # Tracked and qualified, but not auto-paired (full crew-complement
    # rostering is a later phase). Cabin crew carry SEP / first-aid / CRM +
    # medical; engineers carry a maintenance type-authorisation + DGR.
    cabin_and_eng: tuple[tuple[str, CrewRole, str, int], ...] = (
        ("CC-P01", CrewRole.PURSER, "Purser", 30),
        ("CC-P02", CrewRole.PURSER, "Purser", 22),
        ("CC-01", CrewRole.CABIN_CREW, "Cabin Crew", 11),
        ("CC-02", CrewRole.CABIN_CREW, "Cabin Crew", 14),
        ("CC-03", CrewRole.CABIN_CREW, "Cabin Crew", 7),
        ("CC-04", CrewRole.CABIN_CREW, "Cabin Crew", 18),
        ("CC-05", CrewRole.CABIN_CREW, "Cabin Crew", 25),
        ("CC-06", CrewRole.CABIN_CREW, "Cabin Crew", 3),
        ("ENG-01", CrewRole.ENGINEER, "Engineer", 0),
        ("ENG-02", CrewRole.ENGINEER, "Engineer", 0),
    )
    for j, (emp, role, label, med_months) in enumerate(cabin_and_eng):
        number = emp.split("-")[-1]
        crew, created = _get_or_create(
            session,
            Crew,
            defaults={
                "first_name": label,
                "last_name": number,
                "role": role,
                "date_of_hire": date(
                    today.year - 3 - (j % 5), ((j * 3) % 12) + 1, ((j * 5) % 27) + 1
                ),
                "date_of_birth": date(1985 + (j % 12), ((j * 5) % 12) + 1, ((j * 7) % 27) + 1),
                "base_station": "HKJK",
                "contract_type": ContractType.FULL_TIME,
                "active": True,
                "languages": ["en", "sw"],
                "faith_observance_flags": {},
            },
            operator_id=operator.id,
            employee_no=emp,
        )
        if not created:
            continue
        if role is CrewRole.ENGINEER:
            _get_or_create(
                session,
                CrewDocument,
                defaults={
                    "document_number": f"AML-{number}",
                    "issuing_authority": "KCAA",
                    "issue_date": today - timedelta(days=400),
                    "expiry_date": today + timedelta(days=300 + j * 20),
                    "notes": "Aircraft maintenance type authorisation (Fokker F50/F70/F100)",
                },
                operator_id=operator.id,
                crew_id=crew.id,
                doc_type=DocumentType.MAINTENANCE_AUTH,
            )
            _get_or_create(
                session,
                CrewCurrency,
                defaults={
                    "last_completed_date": today - timedelta(days=200),
                    "expires_date": today + timedelta(days=160),
                    "evidence_ref": "DGR CAT",
                },
                operator_id=operator.id,
                crew_id=crew.id,
                currency_type=CurrencyType.DG,
            )
        else:
            _get_or_create(
                session,
                CrewDocument,
                defaults={
                    "document_number": f"MED-{emp}",
                    "issuing_authority": "KCAA",
                    "issue_date": today - timedelta(days=180),
                    "expiry_date": today + timedelta(days=med_months * 30),
                    "notes": "Class 2 medical certificate",
                },
                operator_id=operator.id,
                crew_id=crew.id,
                doc_type=DocumentType.MEDICAL,
            )
            for ct, days in (
                (CurrencyType.EMERG_PROC, med_months * 30),
                (CurrencyType.FIRST_AID, 60 + j * 20),
                (CurrencyType.CRM, 200 + j * 15),
            ):
                _get_or_create(
                    session,
                    CrewCurrency,
                    defaults={
                        "last_completed_date": today - timedelta(days=300),
                        "expires_date": today + timedelta(days=days),
                        "evidence_ref": "DEMO",
                    },
                    operator_id=operator.id,
                    crew_id=crew.id,
                    currency_type=ct,
                )

    # ── Operator FTL scheme (KCAR Part 8 hard limits over baseline) ──
    cset = session.scalar(select(ConstraintSet).where(ConstraintSet.operator_id == operator.id))
    if cset is None:
        cset = ConstraintSet(
            operator_id=operator.id,
            om_a_revision="JAL OM-A Part 7 / KCAR Part 8 (2025)",
            source_filename="JAL_OM-A_FTL.pdf",
            status=ConstraintSetStatus.ACCEPTED,
            model="seed",
            coverage_pct=Decimal("100.00"),
            rule_count=4,
            accepted_at=datetime.now(UTC),
        )
        session.add(cset)
        session.flush()
        ref = "KCAR Part 8 (L.N. 2025); ICAO Annex 6 Part I, 4.10"
        rules = [
            ("fdp_scheduled_ceiling_basic_h", 14.0, 13.0, "Max FDP 13h (multi-sector/night ops)"),
            ("cumul_block_365d_h", 1000.0, 900.0, "Max 900 block hrs / 12 months"),
            ("cumul_block_28d_h", 100.0, 100.0, "Max 100 block hrs / 28 days"),
            ("rest_away_floor_h", 10.0, 12.0, "12h minimum rest at MGQ layover (night duty)"),
        ]
        for key, base_v, final_v, excerpt in rules:
            session.add(
                ConstraintRule(
                    constraint_set_id=cset.id,
                    rule_key=key,
                    proposed_value=final_v,
                    baseline_value=base_v,
                    final_value=final_v,
                    review_status=ConstraintReviewStatus.ACCEPTED,
                    regulation_ref=ref,
                    source_excerpt=excerpt,
                    confidence=Decimal("0.950"),
                )
            )

    # ── Notices ──
    notices = [
        (
            NoticeCategory.OPERATIONAL,
            NoticeSeverity.CRITICAL,
            "Somalia Night Cargo Programme — security brief mandatory",
            "All crew on CGO-01 to CGO-05 (MGQ/KMU) must complete the current Somalia "
            "airspace security brief before sign-on. Acknowledge below.",
            True,
            True,
        ),
        (
            NoticeCategory.FLEET,
            NoticeSeverity.IMPORTANT,
            "5Y-JWF (F50) in C-check",
            "5Y-JWF is out of service for scheduled C-check; return planned Q3 2026. "
            "5Y-CMB (combi) is cargo cover if 5Y-CAR is unavailable.",
            False,
            False,
        ),
        (
            NoticeCategory.SAFETY,
            NoticeSeverity.IMPORTANT,
            "Fokker type currency is critical and non-substitutable",
            "The F50/F70/F100 type was discontinued in 1997 and the global type-rated "
            "pool is shrinking. Protect F70/F100 currency — a lost rating cannot be "
            "covered by an unrated crew member.",
            False,
            True,
        ),
        (
            NoticeCategory.SOCIAL,
            NoticeSeverity.INFO,
            "Welcome to the Jetways crew portal",
            "View your roster, training-expiry countdown, and submit duty-swap and "
            "leave requests here.",
            False,
            False,
        ),
    ]
    for cat, sev, title, body, ack, pinned in notices:
        _get_or_create(
            session,
            Notice,
            defaults={
                "category": cat,
                "severity": sev,
                "body": body,
                "requires_ack": ack,
                "pinned": pinned,
                "published": True,
                "published_at": datetime.now(UTC),
            },
            operator_id=operator.id,
            title=title,
        )

    # ── Leave + swap ──
    leave_specs = [
        ("FO-005", LeaveType.ANNUAL, LeaveStatus.APPROVED, 8, 14),
        ("CPT-009", LeaveType.ANNUAL, LeaveStatus.PENDING, 10, 17),
        ("FO-013", LeaveType.COMPASSIONATE, LeaveStatus.PENDING, 3, 5),
    ]
    for emp, ltype, status, d0, d1 in leave_specs:
        crew = crew_by_id.get(emp)
        if crew is None:
            continue
        _get_or_create(
            session,
            LeaveRequest,
            defaults={
                "type": ltype,
                "status": status,
                "approver_id": officer.id if status is LeaveStatus.APPROVED else None,
                "note": "Demo leave request",
            },
            operator_id=operator.id,
            crew_id=crew.id,
            date_from=today + timedelta(days=d0),
            date_to=today + timedelta(days=d1),
        )
    if "FO-001" in crew_by_id and "FO-004" in crew_by_id:
        _get_or_create(
            session,
            SwapRequest,
            defaults={
                "reason": "Family commitment — requesting swap",
                "status": SwapStatus.PENDING,
            },
            operator_id=operator.id,
            crew_id_initiator=crew_by_id["FO-001"].id,
            crew_id_counterparty=crew_by_id["FO-004"].id,
            fdp_or_sector_ref=f"5Y-CAR|{(today + timedelta(days=4)).isoformat()}",
        )

    # ── Outstation / ACMI wet-lease posting (3-week detachment) ──
    # A team (pilots + cabin + engineer) deployed to Entebbe for a lessee.
    # Each member gets a Uganda work permit valid through the posting so the
    # international-posting permit gate passes.
    if session.scalar(select(Posting).where(Posting.operator_id == operator.id)) is None:
        posting = postings_service.create_posting(
            session,
            operator_id=operator.id,
            user_id=officer.id,
            location_icao="HUEN",
            country="Uganda",
            type=PostingType.ACMI_WET_LEASE,
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=27),
            base_tz="Africa/Kampala",
            lessee_name="Nile Air (demo lessee)",
            notes="3-week ACMI wet-lease detachment — F70 5Y-JEA",
        )
        for emp in ("CPT-001", "CPT-002", "FO-001", "FO-004", "CC-P01", "CC-01", "ENG-01"):
            member = session.scalar(
                select(Crew).where(Crew.operator_id == operator.id).where(Crew.employee_no == emp)
            )
            if member is None:
                continue
            _get_or_create(
                session,
                CrewDocument,
                defaults={
                    "document_number": f"UG-WP-{emp}",
                    "issuing_authority": "Uganda CAA",
                    "issue_date": today,
                    "expiry_date": today + timedelta(days=120),
                    "notes": "Uganda work permit (ACMI detachment)",
                },
                operator_id=operator.id,
                crew_id=member.id,
                doc_type=DocumentType.WORK_PERMIT,
            )
            session.flush()
            postings_service.assign_crew(
                session,
                operator_id=operator.id,
                user_id=officer.id,
                posting_id=posting.id,
                crew_id=member.id,
            )

    # Commit the core workspace (operator, users, fleet, crew, currencies,
    # documents, FTL scheme, notices, leave/swap) up front so login and the
    # browseable demo survive even if the heavier roster-publish or audit-pack
    # steps below fail or run out of memory on a small free-tier instance.
    session.commit()

    # ── Published roster: 28 days, night cargo + daytime pax ──
    assignments_created = 0
    try:
        assignments_created = _publish_roster(session, officer, today)
    except Exception:  # roster is best-effort — never block the demo on it
        session.rollback()

    # ── 90-day audit pack ──
    # Generate ONE pack for Jetways so the demo's Audit packs page isn't empty.
    # A single WeasyPrint render is fine on the free instance; it was generating
    # one PER operator (3x) at boot that risked the OOM. Best-effort: a failure
    # here must never crash the seed (the core workspace is already committed).
    try:
        audit_pack.generate_pack(
            session, user=officer, period_from=today - timedelta(days=89), period_to=today
        )
    except Exception:  # audit pack is best-effort in the seed
        session.rollback()

    session.commit()
    return {
        "pilots": len(ALL_PILOTS),
        "cabin_eng": len(cabin_and_eng),
        "aircraft": len(FLEET),
        "assignments": assignments_created,
    }


def _publish_roster(session: Session, officer: User, today: date) -> int:
    captains_jet = [
        "CPT-001",
        "CPT-002",
        "CPT-003",
        "CPT-004",
        "CPT-005",
        "CPT-006",
        "CPT-010",
        "CPT-011",
        "CPT-012",
    ]
    captains_f50 = ["CPT-007", "CPT-008", "CPT-009"]
    fos_f5070 = ["FO-001", "FO-002", "FO-004", "FO-007", "FO-008"]
    fos_f50 = [
        "FO-003",
        "FO-005",
        "FO-006",
        "FO-009",
        "FO-010",
        "FO-011",
        "FO-012",
        "FO-013",
        "FO-014",
        "FO-015",
    ]
    all_fos = fos_f5070 + fos_f50

    sectors: list[SectorInputIn] = []
    assignments: list[AssignmentOut] = []
    counter = 0

    def add_pairing(
        d: date,
        reg: str,
        ac_type: str,
        legs: list[tuple[int, int, int, int, str]],
        captain: str,
        fo: str,
    ) -> None:
        nonlocal counter
        sector_ids: list[str] = []
        for sh, sm, eh, em, block in legs:
            counter += 1
            sid = f"JW{counter:05d}"
            std = _eat(d, sh, sm)
            sta = _eat(d, eh, em)
            sectors.append(
                SectorInputIn(
                    sector_id=sid,
                    date_local=d,
                    std=std,
                    sta=sta,
                    aircraft_reg=reg,
                    aircraft_type=ac_type,
                    block_hours=Decimal(block),
                )
            )
            sector_ids.append(sid)
        assignments.append(
            AssignmentOut(
                duty_day_key=f"{reg}|{d.isoformat()}",
                date_local=d,
                aircraft_reg=reg,
                aircraft_type=ac_type,
                sector_ids=sector_ids,
                captain_id=captain,
                fo_id=fo,
                legality_state=None,
            )
        )

    for i in range(28):
        d = today - timedelta(days=14) + timedelta(days=i)
        used_cap: set[str] = set()
        used_fo: set[str] = set()

        # Somalia night cargo — 5Y-CAR (F50), report ~01:00 EAT (WOCL).
        add_pairing(
            d,
            "5Y-CAR",
            "F50",
            [(2, 0, 3, 30, "1.50"), (4, 30, 6, 0, "1.50")],
            _pick(captains_f50, used_cap, i),
            _pick(fos_f5070, used_fo, i),
        )
        # Domestic pax F50 — 5Y-SKC, NBO–KIS–NBO daytime.
        add_pairing(
            d,
            "5Y-SKC",
            "F50",
            [(7, 30, 8, 24, "0.90"), (9, 30, 10, 24, "0.90")],
            _pick(captains_f50, used_cap, i, 1),
            _pick(fos_f50, used_fo, i),
        )
        # Regional pax F100 — 5Y-JET, NBO–MBA–NBO daytime (DAY_PEAK).
        add_pairing(
            d,
            "5Y-JET",
            "F100",
            [(8, 0, 9, 0, "1.00"), (10, 0, 11, 0, "1.00")],
            _pick(captains_jet, used_cap, i),
            _pick(all_fos, used_fo, i, 3),
        )
        # Regional pax F70 — 5Y-JEA, NBO–JUB–NBO daytime.
        add_pairing(
            d,
            "5Y-JEA",
            "F70",
            [(9, 0, 10, 45, "1.75"), (12, 0, 13, 45, "1.75")],
            _pick(captains_jet, used_cap, i, 2),
            _pick(all_fos, used_fo, i, 7),
        )

    payload = PublishRosterRequest(
        horizon_from=today - timedelta(days=14),
        horizon_to=today + timedelta(days=13),
        sectors=sectors,
        assignments=assignments,
    )
    resp = roster_service.publish_roster(session, user=officer, payload=payload)
    return resp.sector_assignments_created


def main() -> int:
    with SessionLocal() as session:
        summary = seed_jetways(session)
    print("Jetways Airlines demo workspace seeded.")
    print(f"  Operator : Jetways Airlines Limited (AOC {OPERATOR_AOC})")
    print(f"  Login    : {OFFICER_EMAIL} / {PASSWORD}  (Crewing Officer)")
    print(f"             {CHIEF_EMAIL} / {PASSWORD}  (Chief Pilot)")
    print(
        f"  Seeded   : {summary['pilots']} pilots + {summary['cabin_eng']} cabin/eng, "
        f"{summary['aircraft']} aircraft, {summary['assignments']} duty-day assignments"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
