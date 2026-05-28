"""Render backend API payloads into bot-friendly text."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _hour(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%H:%M")
    except ValueError:
        return iso


def format_duty_day(d: dict[str, Any]) -> str:
    sectors = ", ".join(d.get("sector_ids", []) or ["—"])
    lines = [
        f"📅 {d.get('date_local')} · {d.get('aircraft_reg')} ({d.get('aircraft_type')})",
        f"   Role: {d.get('role_on_duty')} · Sectors: {sectors}",
        f"   Report {_hour(d.get('report_time'))} · Off {_hour(d.get('off_duty_time'))}",
    ]
    legality = d.get("legality_state")
    if legality:
        lines.append(f"   FTL state: {legality}")
    return "\n".join(lines)


def format_roster(payload: dict[str, Any]) -> str:
    days = payload.get("duty_days") or []
    if not days:
        return (
            f"No duty days scheduled between {payload.get('date_from')} and "
            f"{payload.get('date_to')}."
        )
    header = f"🗓 Roster {payload.get('date_from')} → {payload.get('date_to')}"
    body = "\n\n".join(format_duty_day(d) for d in days)
    return f"{header}\n\n{body}"


def format_today(payload: dict[str, Any]) -> str:
    if not payload.get("has_duty"):
        return "✅ No duty scheduled for today. Rest well."
    return "Today:\n" + format_duty_day(payload["duty_day"])


def format_currency(payload: dict[str, Any]) -> str:
    rows = payload.get("currencies") or []
    if not rows:
        return "No currencies on record."
    icons = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}
    body = "\n".join(
        f"{icons.get(r['state'], '⚪')} {r['currency_type']:<14} expires {r['expires_date']} "
        f"({r['days_remaining']:+d}d)"
        for r in rows
    )
    return "Currency:\n" + body


HELP_TEXT = (
    "Ratiba — pilot bot. Commands I understand:\n"
    "  /start <code>  — pair this chat with your crew record\n"
    "  /roster        — your duty days for the next 14 days\n"
    "  /duty          — today's duty (if any)\n"
    "  /currency      — your currency / recency status\n"
    "  /leave         — submit a leave request (guided)\n"
    "  /swap          — request a duty swap (guided)\n"
    "  /help          — show this list\n\n"
    "You can also just ask me in plain language —\n"
    '  e.g. "do I fly tuesday?" or "when does my OPC expire?"'
)
