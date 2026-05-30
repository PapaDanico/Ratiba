"""CSV importers for crew, type ratings, currencies, and historical FDPs.

Designed for the Plan §5 Phase 6 onboarding flow: a Crewing Officer
exports four CSVs from their current Excel sheets and uploads them via
``POST /api/v1/onboarding/{kind}``. Each importer is dry-run-friendly
(``commit=False``) so the dashboard can preview row counts + validation
errors before the actual write.

Every successful import generates an ``ONBOARDING_IMPORT_<kind>`` audit
event with the row count, so the audit pack reflects how the data got
there.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Crew,
    CrewCurrency,
    CrewTypeRating,
    FlightDutyPeriod,
    User,
)
from app.models.crew import ContractType, CrewRole
from app.models.ftl import FdpType, LegalityState
from app.models.training import CurrencyType
from app.services import audit_log


class ImportError_(Exception):
    """Raised for whole-file errors (missing columns, malformed CSV)."""


@dataclass
class RowError:
    row_number: int
    message: str


@dataclass
class ImportResult:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[RowError] = field(default_factory=list)

    def as_dict(self) -> dict[str, int | list[dict[str, str | int]]]:
        return {
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": [{"row": e.row_number, "message": e.message} for e in self.errors],
        }


# Cap parsed rows so a pathological upload can't exhaust memory/time. Far
# above any realistic sub-scale operator onboarding batch.
MAX_ROWS = 20_000


def _read_csv(content: bytes, required: tuple[str, ...]) -> list[dict[str, str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportError_("file is not valid UTF-8 text — upload a CSV") from exc
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ImportError_("CSV is empty")
    missing = [c for c in required if c not in reader.fieldnames]
    if missing:
        raise ImportError_(f"missing required columns: {', '.join(missing)}")
    rows: list[dict[str, str]] = []
    for row in reader:
        if len(rows) >= MAX_ROWS:
            raise ImportError_(f"CSV exceeds the {MAX_ROWS:,}-row limit — split it into batches")
        rows.append(row)
    return rows


def _parse_date(value: str, *, row: int, field_name: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(f"row {row}: {field_name!r} must be ISO date (YYYY-MM-DD)") from exc


def _parse_datetime(value: str, *, row: int, field_name: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.strip())
        if dt.tzinfo is None:
            raise ValueError(f"row {row}: {field_name!r} must include timezone (e.g. +00:00)")
        return dt
    except ValueError as exc:
        raise ValueError(f"row {row}: {field_name!r} must be ISO 8601 with timezone") from exc


# -----------------------------------------------------------------------------
# Crew importer
# -----------------------------------------------------------------------------

CREW_COLUMNS = (
    "employee_no",
    "first_name",
    "last_name",
    "role",
    "date_of_hire",
    "date_of_birth",
    "base_station",
    "contract_type",
)


def import_crew(
    session: Session, *, user: User, content: bytes, commit: bool = True
) -> ImportResult:
    rows = _read_csv(content, CREW_COLUMNS)
    result = ImportResult()
    existing = {
        c.employee_no: c
        for c in session.scalars(select(Crew).where(Crew.operator_id == user.operator_id)).all()
    }
    for i, row in enumerate(rows, start=2):
        try:
            emp = row["employee_no"].strip()
            if not emp:
                raise ValueError(f"row {i}: employee_no is empty")
            role = CrewRole(row["role"].strip().upper())
            contract = ContractType(row["contract_type"].strip().upper())
            doh = _parse_date(row["date_of_hire"], row=i, field_name="date_of_hire")
            dob = _parse_date(row["date_of_birth"], row=i, field_name="date_of_birth")
            base = row["base_station"].strip().upper()
            languages = [s.strip() for s in (row.get("languages") or "").split(";") if s.strip()]
            faith_str = (row.get("faith_observance_flags") or "").strip()
            faith_flags: dict[str, bool] = {}
            if faith_str:
                for token in faith_str.split(";"):
                    token = token.strip()
                    if "=" in token:
                        k, v = token.split("=", 1)
                        faith_flags[k.strip()] = v.strip().lower() in ("1", "true", "yes")
            email = (row.get("email") or "").strip() or None
            phone = (row.get("phone_number") or "").strip() or None
            whatsapp = (row.get("whatsapp_number") or "").strip() or None
            if emp in existing:
                crew = existing[emp]
                crew.first_name = row["first_name"].strip()
                crew.last_name = row["last_name"].strip()
                crew.role = role
                crew.date_of_hire = doh
                crew.date_of_birth = dob
                crew.base_station = base
                crew.contract_type = contract
                if languages:
                    crew.languages = languages
                if faith_flags:
                    crew.faith_observance_flags = faith_flags
                if email is not None:
                    crew.email = email
                if phone is not None:
                    crew.phone_number = phone
                if whatsapp is not None:
                    crew.whatsapp_number = whatsapp
                result.updated += 1
            else:
                session.add(
                    Crew(
                        operator_id=user.operator_id,
                        created_by_user_id=user.id,
                        employee_no=emp,
                        first_name=row["first_name"].strip(),
                        last_name=row["last_name"].strip(),
                        role=role,
                        date_of_hire=doh,
                        date_of_birth=dob,
                        base_station=base,
                        contract_type=contract,
                        active=True,
                        languages=languages,
                        faith_observance_flags=faith_flags,
                        email=email,
                        phone_number=phone,
                    )
                )
                result.inserted += 1
        except (ValueError, KeyError) as exc:
            result.errors.append(RowError(row_number=i, message=str(exc)))

    if commit and not result.errors:
        session.flush()
        audit_log.record(
            session,
            operator_id=user.operator_id,
            actor_user_id=user.id,
            action="ONBOARDING_IMPORT_CREW",
            entity_type="crew",
            entity_id=None,
            before_state=None,
            after_state=result.as_dict(),
        )
        session.commit()
    elif not commit:
        session.rollback()
    return result


# -----------------------------------------------------------------------------
# Type rating importer
# -----------------------------------------------------------------------------

TYPE_RATING_COLUMNS = ("employee_no", "aircraft_type", "valid_from", "valid_until")


def import_type_ratings(
    session: Session, *, user: User, content: bytes, commit: bool = True
) -> ImportResult:
    rows = _read_csv(content, TYPE_RATING_COLUMNS)
    result = ImportResult()
    crew_by_emp = {
        c.employee_no: c
        for c in session.scalars(select(Crew).where(Crew.operator_id == user.operator_id)).all()
    }
    for i, row in enumerate(rows, start=2):
        try:
            emp = row["employee_no"].strip()
            crew = crew_by_emp.get(emp)
            if crew is None:
                raise ValueError(f"row {i}: crew {emp!r} not found")
            session.add(
                CrewTypeRating(
                    operator_id=user.operator_id,
                    created_by_user_id=user.id,
                    crew_id=crew.id,
                    aircraft_type=row["aircraft_type"].strip().upper(),
                    valid_from=_parse_date(row["valid_from"], row=i, field_name="valid_from"),
                    valid_until=_parse_date(row["valid_until"], row=i, field_name="valid_until"),
                    evidence_ref=(row.get("evidence_ref") or "").strip() or None,
                )
            )
            result.inserted += 1
        except (ValueError, KeyError) as exc:
            result.errors.append(RowError(row_number=i, message=str(exc)))

    if commit and not result.errors:
        session.flush()
        audit_log.record(
            session,
            operator_id=user.operator_id,
            actor_user_id=user.id,
            action="ONBOARDING_IMPORT_TYPE_RATINGS",
            entity_type="crew_type_rating",
            entity_id=None,
            before_state=None,
            after_state=result.as_dict(),
        )
        session.commit()
    elif not commit:
        session.rollback()
    return result


# -----------------------------------------------------------------------------
# Currency importer
# -----------------------------------------------------------------------------

CURRENCY_COLUMNS = (
    "employee_no",
    "currency_type",
    "last_completed_date",
    "expires_date",
)


def import_currencies(
    session: Session, *, user: User, content: bytes, commit: bool = True
) -> ImportResult:
    rows = _read_csv(content, CURRENCY_COLUMNS)
    result = ImportResult()
    crew_by_emp = {
        c.employee_no: c
        for c in session.scalars(select(Crew).where(Crew.operator_id == user.operator_id)).all()
    }
    for i, row in enumerate(rows, start=2):
        try:
            emp = row["employee_no"].strip()
            crew = crew_by_emp.get(emp)
            if crew is None:
                raise ValueError(f"row {i}: crew {emp!r} not found")
            ctype = CurrencyType(row["currency_type"].strip().upper())
            session.add(
                CrewCurrency(
                    operator_id=user.operator_id,
                    created_by_user_id=user.id,
                    crew_id=crew.id,
                    currency_type=ctype,
                    last_completed_date=_parse_date(
                        row["last_completed_date"],
                        row=i,
                        field_name="last_completed_date",
                    ),
                    expires_date=_parse_date(row["expires_date"], row=i, field_name="expires_date"),
                    evidence_ref=(row.get("evidence_ref") or "").strip() or None,
                )
            )
            result.inserted += 1
        except (ValueError, KeyError) as exc:
            result.errors.append(RowError(row_number=i, message=str(exc)))

    if commit and not result.errors:
        session.flush()
        audit_log.record(
            session,
            operator_id=user.operator_id,
            actor_user_id=user.id,
            action="ONBOARDING_IMPORT_CURRENCIES",
            entity_type="crew_currency",
            entity_id=None,
            before_state=None,
            after_state=result.as_dict(),
        )
        session.commit()
    elif not commit:
        session.rollback()
    return result


# -----------------------------------------------------------------------------
# Historical FDP importer — for the "last 90 days of context" Plan §5 Phase 6 import
# -----------------------------------------------------------------------------

HISTORICAL_FDP_COLUMNS = (
    "employee_no",
    "date",
    "report_time",
    "off_duty_time",
    "sectors_count",
    "flight_hours",
    "duty_hours",
)


def import_historical_fdps(
    session: Session, *, user: User, content: bytes, commit: bool = True
) -> ImportResult:
    rows = _read_csv(content, HISTORICAL_FDP_COLUMNS)
    result = ImportResult()
    crew_by_emp = {
        c.employee_no: c
        for c in session.scalars(select(Crew).where(Crew.operator_id == user.operator_id)).all()
    }
    for i, row in enumerate(rows, start=2):
        try:
            emp = row["employee_no"].strip()
            crew = crew_by_emp.get(emp)
            if crew is None:
                raise ValueError(f"row {i}: crew {emp!r} not found")
            session.add(
                FlightDutyPeriod(
                    operator_id=user.operator_id,
                    created_by_user_id=user.id,
                    crew_id=crew.id,
                    date=_parse_date(row["date"], row=i, field_name="date"),
                    report_time=_parse_datetime(
                        row["report_time"], row=i, field_name="report_time"
                    ),
                    off_duty_time=_parse_datetime(
                        row["off_duty_time"], row=i, field_name="off_duty_time"
                    ),
                    sectors_count=int(row["sectors_count"]),
                    flight_hours=Decimal(row["flight_hours"]),
                    duty_hours=Decimal(row["duty_hours"]),
                    type=FdpType.FDP,
                    legality_state=LegalityState.LEGAL,
                    ftl_rules_applied=["IMPORTED-HISTORICAL"],
                )
            )
            result.inserted += 1
        except (ValueError, KeyError) as exc:
            result.errors.append(RowError(row_number=i, message=str(exc)))

    if commit and not result.errors:
        session.flush()
        audit_log.record(
            session,
            operator_id=user.operator_id,
            actor_user_id=user.id,
            action="ONBOARDING_IMPORT_HISTORICAL_FDPS",
            entity_type="flight_duty_period",
            entity_id=None,
            before_state=None,
            after_state=result.as_dict(),
        )
        session.commit()
    elif not commit:
        session.rollback()
    return result
