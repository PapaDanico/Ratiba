"""Compliance alerts: the dashboard's live risk sweep.

Mirrors the Supabase edge function's /alerts endpoint (the production
implementation) — keep the two in lockstep. Non-LEGAL FTL verdicts in the
recent-past/upcoming window plus every document, currency, and type rating
that is expired or inside the 30-day amber window, worst first.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import Crew, CrewCurrency, CrewDocument, CrewTypeRating, FlightDutyPeriod, User
from app.models.ftl import LegalityState

router = APIRouter()

EXPIRY_WINDOW_DAYS = 30
FDP_LOOKBACK_DAYS = 7


class Alert(BaseModel):
    severity: Literal["RED", "AMBER"]
    category: Literal["FTL", "DOCUMENT", "CURRENCY", "TYPE_RATING"]
    title: str
    detail: str
    date: date
    crew_id: uuid.UUID
    link: str


class AlertCounts(BaseModel):
    red: int
    amber: int


class AlertsResponse(BaseModel):
    generated_at: datetime
    counts: AlertCounts
    alerts: list[Alert]


@router.get("", response_model=AlertsResponse)
def alerts_summary(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> AlertsResponse:
    today = date.today()
    crew_by_id = {
        c.id: c
        for c in session.scalars(select(Crew).where(Crew.operator_id == user.operator_id)).all()
    }

    def name(crew_id: uuid.UUID) -> str:
        c = crew_by_id.get(crew_id)
        return f"{c.first_name} {c.last_name} ({c.employee_no})" if c else "Unknown crew"

    def is_active(crew_id: uuid.UUID) -> bool:
        c = crew_by_id.get(crew_id)
        return bool(c and c.active)

    alerts: list[Alert] = []

    fdps = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.operator_id == user.operator_id)
        .where(FlightDutyPeriod.legality_state != LegalityState.LEGAL)
        .where(FlightDutyPeriod.date >= today - timedelta(days=FDP_LOOKBACK_DAYS))
        .order_by(FlightDutyPeriod.date)
    ).all()
    for f in fdps:
        if not is_active(f.crew_id):
            continue
        state = f.legality_state.value
        worst = f.ftl_rules_applied[0] if f.ftl_rules_applied else "n/a"
        alerts.append(
            Alert(
                severity="AMBER" if state == "AT_LIMIT" else "RED",
                category="FTL",
                title=f"{state.replace('_', ' ')} duty — {name(f.crew_id)}",
                detail=f"{float(f.duty_hours):.1f}h duty on {f.date}; worst rule {worst}",
                date=f.date,
                crew_id=f.crew_id,
                link="/app/roster",
            )
        )

    def push_expiry(
        crew_id: uuid.UUID,
        category: Literal["DOCUMENT", "CURRENCY", "TYPE_RATING"],
        label: str,
        expires: date,
        link: str,
    ) -> None:
        if not is_active(crew_id):
            return
        days = (expires - today).days
        if days > EXPIRY_WINDOW_DAYS:
            return
        alerts.append(
            Alert(
                severity="RED" if days < 0 else "AMBER",
                category=category,
                title=(
                    f"{label} {'EXPIRED' if days < 0 else f'expires in {days}d'} — {name(crew_id)}"
                ),
                detail=(
                    f"Expired {expires} ({-days}d ago)" if days < 0 else f"Valid until {expires}"
                ),
                date=expires,
                crew_id=crew_id,
                link=link,
            )
        )

    for cur in session.scalars(
        select(CrewCurrency).where(CrewCurrency.operator_id == user.operator_id)
    ).all():
        push_expiry(
            cur.crew_id, "CURRENCY", cur.currency_type.value, cur.expires_date, "/app/currency"
        )
    for r in session.scalars(
        select(CrewTypeRating).where(CrewTypeRating.operator_id == user.operator_id)
    ).all():
        push_expiry(
            r.crew_id,
            "TYPE_RATING",
            f"Type rating {r.aircraft_type}",
            r.valid_until,
            "/app/training",
        )
    for d in session.scalars(
        select(CrewDocument)
        .where(CrewDocument.operator_id == user.operator_id)
        .where(CrewDocument.expiry_date.is_not(None))
    ).all():
        assert d.expiry_date is not None
        push_expiry(d.crew_id, "DOCUMENT", d.doc_type.value, d.expiry_date, "/app/documents")

    alerts.sort(key=lambda a: (a.severity != "RED", a.date))
    return AlertsResponse(
        generated_at=datetime.now(UTC),
        counts=AlertCounts(
            red=sum(1 for a in alerts if a.severity == "RED"),
            amber=sum(1 for a in alerts if a.severity == "AMBER"),
        ),
        alerts=alerts,
    )
