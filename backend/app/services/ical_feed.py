"""Per-crew iCalendar (.ics) roster feed.

Renders a crew member's published flight-duty periods as a VCALENDAR so
they can subscribe their roster in Google / Apple / Outlook calendars.
Read-only; served behind a long-lived capability token in the URL.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import __version__
from app.models import Crew, FlightDutyPeriod, Sector, SectorAssignment
from app.models.ftl import FdpType

# How much history / look-ahead to publish in the feed.
_PAST_DAYS = 30
_FUTURE_DAYS = 180


def _esc(text: str) -> str:
    """Escape per RFC 5545 (commas, semicolons, backslashes, newlines)."""
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fmt(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def build_feed(session: Session, *, crew: Crew) -> str:
    today = date.today()
    window_from = today - timedelta(days=_PAST_DAYS)
    window_to = today + timedelta(days=_FUTURE_DAYS)

    fdps = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.operator_id == crew.operator_id)
        .where(FlightDutyPeriod.crew_id == crew.id)
        .where(FlightDutyPeriod.date >= window_from)
        .where(FlightDutyPeriod.date <= window_to)
        .order_by(FlightDutyPeriod.date)
    ).all()

    # Sector codes per date for this crew, to enrich the duty event summary.
    routes_by_date: dict[date, list[str]] = {}
    assignments = session.scalars(
        select(SectorAssignment)
        .where(SectorAssignment.operator_id == crew.operator_id)
        .where(SectorAssignment.crew_id == crew.id)
    ).all()
    if assignments:
        sectors = session.scalars(
            select(Sector)
            .where(Sector.id.in_([a.sector_id for a in assignments]))
            .where(Sector.date >= window_from)
            .where(Sector.date <= window_to)
        ).all()
        for s in sectors:
            routes_by_date.setdefault(s.date, []).append(f"{s.origin}-{s.destination}")

    now_stamp = _fmt(datetime.now(UTC))
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//DN Consultancy//Ratiba {__version__}//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_esc(f'Ratiba roster — {crew.first_name} {crew.last_name}')}",
    ]

    type_labels = {
        FdpType.FDP: "Flight duty",
        FdpType.STANDBY: "Standby",
        FdpType.POSITIONING: "Positioning",
        FdpType.TRAINING: "Training",
        FdpType.OFF: "Day off",
        FdpType.LEAVE: "Leave",
        FdpType.SICK: "Sick",
    }

    for f in fdps:
        label = type_labels.get(f.type, "Duty")
        routes = routes_by_date.get(f.date, [])
        summary = label
        if f.type == FdpType.FDP and routes:
            summary = f"{label}: {' '.join(routes[:4])}"
        desc_parts = [f"Type: {f.type.value}"]
        if f.type == FdpType.FDP:
            desc_parts.append(f"Duty {float(f.duty_hours or 0):.1f}h")
            desc_parts.append(f"Block {float(f.flight_hours or 0):.1f}h")
            if f.legality_state:
                desc_parts.append(f"FTL: {f.legality_state.value}")
        uid = f"{f.id}@ratiba"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART:{_fmt(f.report_time)}",
            f"DTEND:{_fmt(f.off_duty_time)}",
            f"SUMMARY:{_esc(summary)}",
            f"DESCRIPTION:{_esc(' · '.join(desc_parts))}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    # RFC 5545 wants CRLF line endings.
    return "\r\n".join(lines) + "\r\n"


def crew_for_feed(session: Session, *, crew_id: uuid.UUID) -> Crew | None:
    return session.scalar(select(Crew).where(Crew.id == crew_id))
