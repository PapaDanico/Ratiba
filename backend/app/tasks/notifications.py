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
from app.models import FlightDutyPeriod
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
