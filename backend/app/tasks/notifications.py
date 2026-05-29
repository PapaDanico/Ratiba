"""Async notification jobs (dispatched via the job queue).

Run in the Redis worker in production (or inline via the in-process queue in
dev/tests). Each task opens its own DB session — it must not assume a request
session — and reads the authoritative persisted state rather than trusting the
enqueue payload for anything beyond identifiers.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Crew, CrewCurrency, CrewDocument, CrewTypeRating, FlightDutyPeriod
from app.models.ftl import FdpType
from app.services import notify


def notify_roster_published(payload: dict[str, Any]) -> dict[str, Any]:
    """Message every crew member assigned a flight duty in the published
    horizon. Recipients are read back from the persisted FDP rows (crew UUIDs),
    so this is robust to whatever identifier the publish request used."""
    operator_id = uuid.UUID(payload["operator_id"])
    horizon_from = date.fromisoformat(payload["horizon_from"])
    horizon_to = date.fromisoformat(payload["horizon_to"])

    with SessionLocal() as session:
        crew_ids = set(
            session.scalars(
                select(FlightDutyPeriod.crew_id)
                .where(FlightDutyPeriod.operator_id == operator_id)
                .where(FlightDutyPeriod.date >= horizon_from)
                .where(FlightDutyPeriod.date <= horizon_to)
                .where(FlightDutyPeriod.type == FdpType.FDP)
            ).all()
        )
        deliveries = 0
        for crew_id in crew_ids:
            deliveries += notify.notify_crew_member(
                session,
                crew_id=crew_id,
                subject="Roster published",
                body=(
                    f"Your roster for {horizon_from.isoformat()} to "
                    f"{horizon_to.isoformat()} has been published."
                ),
            )

    return {"crew_notified": len(crew_ids), "deliveries": deliveries}


def _crew_name(session: Any, crew_id: uuid.UUID) -> str:
    c = session.get(Crew, crew_id)
    return f"{c.first_name} {c.last_name} ({c.employee_no})" if c else "—"


def notify_expiry_digest(payload: dict[str, Any]) -> dict[str, Any]:
    """Email the operator's crewing staff a digest of qualifications lapsing
    within ``within_days`` (or already expired): currencies, type ratings and
    documents. No email is sent when nothing is due."""
    operator_id = uuid.UUID(payload["operator_id"])
    within_days = int(payload.get("within_days", 30))
    today = date.today()
    horizon = today.toordinal() + within_days

    lines: list[str] = []
    with SessionLocal() as session:
        currencies = session.scalars(
            select(CrewCurrency).where(CrewCurrency.operator_id == operator_id)
        ).all()
        for cur in currencies:
            if cur.expires_date.toordinal() <= horizon:
                days = (cur.expires_date - today).days
                lines.append(
                    f"- {_crew_name(session, cur.crew_id)}: {cur.currency_type.value} "
                    f"{'expired' if days < 0 else f'in {days}d'} ({cur.expires_date.isoformat()})"
                )
        ratings = session.scalars(
            select(CrewTypeRating).where(CrewTypeRating.operator_id == operator_id)
        ).all()
        for r in ratings:
            if r.valid_until.toordinal() <= horizon:
                days = (r.valid_until - today).days
                lines.append(
                    f"- {_crew_name(session, r.crew_id)}: type rating {r.aircraft_type} "
                    f"{'expired' if days < 0 else f'in {days}d'} ({r.valid_until.isoformat()})"
                )
        documents = session.scalars(
            select(CrewDocument)
            .where(CrewDocument.operator_id == operator_id)
            .where(CrewDocument.expiry_date.is_not(None))
        ).all()
        for d in documents:
            if d.expiry_date is not None and d.expiry_date.toordinal() <= horizon:
                days = (d.expiry_date - today).days
                lines.append(
                    f"- {_crew_name(session, d.crew_id)}: document {d.doc_type.value} "
                    f"{'expired' if days < 0 else f'in {days}d'} ({d.expiry_date.isoformat()})"
                )

        if not lines:
            return {"items": 0, "emailed": 0}

        body = (
            f"{len(lines)} crew qualification(s) lapse within {within_days} days "
            f"(or already expired):\n\n" + "\n".join(sorted(lines))
        )
        emailed = notify.notify_staff(
            session,
            operator_id=operator_id,
            subject=f"Recurrency digest — {len(lines)} item(s) need attention",
            body=body,
        )
    return {"items": len(lines), "emailed": emailed}
