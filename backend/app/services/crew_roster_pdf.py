"""Per-crew monthly roster PDF generator.

Produces a branded A4 portrait PDF for a single crew member showing their
duty schedule for a calendar month: sectors, leave, standby, and off days
laid out in a Mon–Sun grid with FTL legality colour coding.

Entry point: :func:`generate_crew_roster_pdf`
"""

from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Crew, Sector, SectorAssignment
from app.models import FlightDutyPeriod as FDP
from app.models.ftl import FdpType, LegalityState
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.operator import Operator
from app.services import branding


class CrewRosterPdfError(Exception):
    pass


@dataclass
class DayCell:
    date: date
    in_month: bool
    fdp_type: str = ""  # FDP type label
    legality: str = ""  # LEGAL / AT_LIMIT / etc.
    duty_h: float = 0.0
    flight_h: float = 0.0
    sector_ids: list[str] = field(default_factory=list)
    leave_type: str = ""
    is_holiday: bool = False
    holiday_name: str = ""


def _gather(
    session: Session,
    *,
    operator_id: uuid.UUID,
    crew: Crew,
    year: int,
    month: int,
) -> tuple[list[list[DayCell]], dict[str, Any]]:
    """Build the weekly grid and summary stats for the PDF."""
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    # FDPs for the month
    fdps = session.scalars(
        select(FDP)
        .where(FDP.operator_id == operator_id)
        .where(FDP.crew_id == crew.id)
        .where(FDP.date >= first_day)
        .where(FDP.date <= last_day)
        .order_by(FDP.date)
    ).all()
    fdp_by_date = {f.date: f for f in fdps}

    # Sector assignments + sectors for the month
    assignments = session.scalars(
        select(SectorAssignment)
        .where(SectorAssignment.operator_id == operator_id)
        .where(SectorAssignment.crew_id == crew.id)
    ).all()
    sector_ids_in_month: dict[date, list[str]] = {}
    if assignments:
        sa_sector_ids = [a.sector_id for a in assignments]
        sectors = session.scalars(
            select(Sector)
            .where(Sector.id.in_(sa_sector_ids))
            .where(Sector.date >= first_day)
            .where(Sector.date <= last_day)
        ).all()
        for s in sectors:
            sector_ids_in_month.setdefault(s.date, []).append(s.flight_no)

    # Approved leave requests overlapping the month
    leave_rows = session.scalars(
        select(LeaveRequest)
        .where(LeaveRequest.operator_id == operator_id)
        .where(LeaveRequest.crew_id == crew.id)
        .where(LeaveRequest.status == LeaveStatus.APPROVED)
        .where(LeaveRequest.date_to >= first_day)
        .where(LeaveRequest.date_from <= last_day)
    ).all()
    leave_by_date: dict[date, str] = {}
    for lr in leave_rows:
        cur = lr.date_from
        while cur <= lr.date_to:
            if first_day <= cur <= last_day:
                leave_by_date[cur] = lr.type.value
            cur += timedelta(days=1)

    # Build calendar weeks (Mon=0 … Sun=6)
    # Pad to full weeks
    start_pad = first_day.weekday()  # 0=Mon
    end_pad = 6 - last_day.weekday()
    grid_start = first_day - timedelta(days=start_pad)
    grid_end = last_day + timedelta(days=end_pad)

    weeks: list[list[DayCell]] = []
    cur = grid_start
    while cur <= grid_end:
        week: list[DayCell] = []
        for _ in range(7):
            in_month = first_day <= cur <= last_day
            cell = DayCell(date=cur, in_month=in_month)
            if in_month:
                fdp = fdp_by_date.get(cur)
                if fdp:
                    cell.fdp_type = fdp.type.value
                    cell.legality = fdp.legality_state.value if fdp.legality_state else ""
                    cell.duty_h = float(fdp.duty_hours or 0)
                    cell.flight_h = float(fdp.flight_hours or 0)
                    cell.sector_ids = sector_ids_in_month.get(cur, [])
                elif cur in leave_by_date:
                    cell.fdp_type = leave_by_date[cur]
                    cell.leave_type = leave_by_date[cur]
            cur += timedelta(days=1)
            week.append(cell)
        weeks.append(week)

    # Summary stats
    total_duty_h = sum(f.duty_hours or 0 for f in fdps if f.type == FdpType.FDP)
    total_flight_h = sum(f.flight_hours or 0 for f in fdps if f.type == FdpType.FDP)
    fdp_count = sum(1 for f in fdps if f.type == FdpType.FDP)
    leave_days = len(leave_by_date)
    anomalies = sum(1 for f in fdps if f.legality_state and f.legality_state != LegalityState.LEGAL)

    summary = {
        "fdp_count": fdp_count,
        "total_duty_h": float(total_duty_h),
        "total_flight_h": float(total_flight_h),
        "leave_days": leave_days,
        "anomalies": anomalies,
    }
    return weeks, summary


_CSS = """
@page {
  size: A4 portrait;
  margin: 14mm 14mm 16mm 14mm;
  @bottom-right {
    content: counter(page) " / " counter(pages);
    font-family: 'DM Sans', Helvetica, sans-serif;
    font-size: 8pt;
    color: #6B7280;
  }
}
* { box-sizing: border-box; }
html, body {
  font-family: 'DM Sans', Helvetica, Arial, sans-serif;
  font-size: 9pt;
  color: #1C1C1C;
  margin: 0;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 2pt solid #C9A84C;
  padding-bottom: 8pt;
  margin-bottom: 12pt;
}
.header-left h1 {
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-size: 22pt;
  margin: 0 0 2pt 0;
  color: #1C1C1C;
}
.header-left .sub {
  font-size: 9pt;
  color: #6B7280;
}
.header-right {
  text-align: right;
}
.eyebrow {
  font-family: 'JetBrains Mono', monospace;
  font-size: 7pt;
  letter-spacing: 2pt;
  text-transform: uppercase;
  color: #4A7FA5;
}
.brand-logo {
  width: 84px;
  height: auto;
  margin-bottom: 4pt;
}
.month-title {
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-size: 16pt;
  color: #1C1C1C;
  margin: 0;
}
table.cal {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
table.cal th {
  background: #1a1a1a;
  color: #C9A84C;
  font-family: 'DM Sans', Helvetica, sans-serif;
  font-size: 8pt;
  font-weight: 600;
  text-align: center;
  padding: 4pt 2pt;
  border: 0.5pt solid #333;
}
table.cal td {
  border: 0.5pt solid #D6E4F0;
  vertical-align: top;
  padding: 3pt;
  height: 52pt;
  width: 14.28%;
}
td.out-of-month {
  background: #F8F8F8;
}
td.in-month {
  background: #FFFFFF;
}
td.today {
  background: #FFF8E6;
  border-color: #C9A84C;
}
.day-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 8pt;
  color: #6B7280;
  font-weight: 600;
}
.duty-code {
  font-size: 7.5pt;
  font-family: 'JetBrains Mono', monospace;
  margin-top: 2pt;
  word-break: break-all;
  color: #1C1C1C;
}
.duty-hours {
  font-size: 7pt;
  color: #6B7280;
  margin-top: 1pt;
}
.badge {
  display: inline-block;
  font-size: 6pt;
  font-weight: 700;
  padding: 1pt 3pt;
  border-radius: 2pt;
  margin-top: 2pt;
  text-transform: uppercase;
  letter-spacing: 0.5pt;
}
.badge-LEGAL { background: #D1FAE5; color: #065F46; }
.badge-AT_LIMIT { background: #FEF3C7; color: #92400E; }
.badge-REQUIRES_FRMS_DEROGATION { background: #FEE2E2; color: #991B1B; }
.badge-ILLEGAL { background: #FEE2E2; color: #991B1B; font-weight: 900; }
.badge-leave { background: #E0E7FF; color: #3730A3; }
.badge-off { background: #F3F4F6; color: #6B7280; }
.badge-standby { background: #FEF9C3; color: #713F12; }
.summary-bar {
  margin-top: 14pt;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8pt;
}
.stat-box {
  border: 0.5pt solid #D6E4F0;
  background: #F4F4F2;
  padding: 6pt;
  text-align: center;
}
.stat-num {
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-size: 18pt;
  color: #1C1C1C;
}
.stat-label {
  font-size: 7pt;
  color: #6B7280;
  margin-top: 2pt;
}
.footer {
  margin-top: 12pt;
  border-top: 0.5pt solid #D6E4F0;
  padding-top: 6pt;
  display: flex;
  justify-content: space-between;
  font-size: 7.5pt;
  color: #9CA3AF;
}
.slogan {
  text-align: center;
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-style: italic;
  font-size: 9pt;
  color: #C9A84C;
  margin-top: 5pt;
}
.legend {
  margin-top: 10pt;
  display: flex;
  gap: 10pt;
  flex-wrap: wrap;
  font-size: 7.5pt;
  color: #6B7280;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4pt;
}
"""

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_MONTH_NAMES = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def _esc(s: object) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _duty_badge(cell: DayCell) -> str:
    if not cell.fdp_type:
        return ""
    t = cell.fdp_type
    # Leave types
    if t in ("ANNUAL", "SICK", "COMPASSIONATE", "FAITH", "OTHER"):
        label = {
            "ANNUAL": "Leave",
            "SICK": "Sick",
            "COMPASSIONATE": "Comp.",
            "FAITH": "Faith",
            "OTHER": "Leave",
        }.get(t, t)
        return f'<span class="badge badge-leave">{_esc(label)}</span>'
    if t == "OFF":
        return '<span class="badge badge-off">OFF</span>'
    if t in ("STANDBY",):
        return '<span class="badge badge-standby">SBY</span>'
    # FTL legality badge for active duty days
    if cell.legality:
        return f'<span class="badge badge-{_esc(cell.legality)}">{_esc(cell.legality.replace("_", " "))}</span>'
    return ""


def _render_html(
    crew: Crew,
    operator: Operator,
    year: int,
    month: int,
    weeks: list[list[DayCell]],
    summary: dict[str, Any],
) -> str:
    today = date.today()

    header_row = "".join(f"<th>{n}</th>" for n in _DAY_NAMES)

    body_rows = ""
    for week in weeks:
        body_rows += "<tr>"
        for cell in week:
            if not cell.in_month:
                body_rows += '<td class="out-of-month"></td>'
                continue
            today_cls = " today" if cell.date == today else ""
            body_rows += f'<td class="in-month{today_cls}">'
            body_rows += f'<div class="day-num">{cell.date.day}</div>'
            # Sector codes (flight numbers)
            if cell.sector_ids:
                codes = " ".join(_esc(s) for s in cell.sector_ids[:3])
                if len(cell.sector_ids) > 3:
                    codes += f" +{len(cell.sector_ids) - 3}"
                body_rows += f'<div class="duty-code">{codes}</div>'
            elif cell.fdp_type and cell.fdp_type not in (
                "ANNUAL",
                "SICK",
                "COMPASSIONATE",
                "FAITH",
                "OTHER",
                "OFF",
            ):
                body_rows += f'<div class="duty-code">{_esc(cell.fdp_type)}</div>'
            # Duty hours
            if cell.duty_h > 0:
                body_rows += f'<div class="duty-hours">{cell.duty_h:.1f}h duty · {cell.flight_h:.1f}h block</div>'
            body_rows += _duty_badge(cell)
            body_rows += "</td>"
        body_rows += "</tr>"

    month_label = f"{_MONTH_NAMES[month]} {year}"
    anom_color = "#C0392B" if summary["anomalies"] > 0 else "#065F46"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Roster — {_esc(crew.first_name)} {_esc(crew.last_name)} — {_esc(month_label)}</title>
  <style>{_CSS}</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <img class="brand-logo" src="{branding.logo_data_uri()}" alt="DN Consultancy" />
    <p class="eyebrow">Ratiba · crew roster card</p>
    <h1>{_esc(crew.first_name)} {_esc(crew.last_name)}</h1>
    <div class="sub">
      {_esc(crew.role.value)} · Employee {_esc(crew.employee_no)} · Base {_esc(crew.base_station)}
      · {_esc(operator.name)} (AOC {_esc(operator.aoc_number)})
    </div>
  </div>
  <div class="header-right">
    <p class="eyebrow">Period</p>
    <p class="month-title">{_esc(month_label)}</p>
    <div class="sub">KCARs 2025 Part 8</div>
  </div>
</div>

<table class="cal">
  <thead><tr>{header_row}</tr></thead>
  <tbody>{body_rows}</tbody>
</table>

<div class="summary-bar">
  <div class="stat-box">
    <div class="stat-num">{summary["fdp_count"]}</div>
    <div class="stat-label">FDPs</div>
  </div>
  <div class="stat-box">
    <div class="stat-num">{summary["total_duty_h"]:.0f}h</div>
    <div class="stat-label">Total duty</div>
  </div>
  <div class="stat-box">
    <div class="stat-num">{summary["total_flight_h"]:.0f}h</div>
    <div class="stat-label">Block hours</div>
  </div>
  <div class="stat-box">
    <div class="stat-num">{summary["leave_days"]}</div>
    <div class="stat-label">Leave days</div>
  </div>
  <div class="stat-box">
    <div class="stat-num" style="color:{anom_color}">{summary["anomalies"]}</div>
    <div class="stat-label">FTL anomalies</div>
  </div>
</div>

<div class="legend">
  <span class="legend-item"><span class="badge badge-LEGAL">LEGAL</span> within limits</span>
  <span class="legend-item"><span class="badge badge-AT_LIMIT">AT LIMIT</span> at regulatory cap</span>
  <span class="legend-item"><span class="badge badge-REQUIRES_FRMS_DEROGATION">FRMS</span> derogation required</span>
  <span class="legend-item"><span class="badge badge-ILLEGAL">ILLEGAL</span> regulatory breach</span>
  <span class="legend-item"><span class="badge badge-leave">Leave</span> approved leave</span>
  <span class="legend-item"><span class="badge badge-standby">SBY</span> standby duty</span>
</div>

<div class="footer">
  <span>Generated by Ratiba · DN Consultancy</span>
  <span>KCARs 2025 Part 8 compliant · Confidential</span>
</div>
<p class="slogan">Shaping Africa&apos;s Future, Together.</p>

</body>
</html>
"""


def _render_pdf(html: str) -> bytes:
    from weasyprint import HTML

    return bytes(HTML(string=html).write_pdf() or b"")


def generate_crew_roster_pdf(
    session: Session,
    *,
    operator_id: uuid.UUID,
    crew_id: uuid.UUID,
    year: int,
    month: int,
) -> bytes:
    """Generate and return a monthly roster PDF for a single crew member."""
    if not (1 <= month <= 12):
        raise CrewRosterPdfError(f"Invalid month: {month}")
    if year < 2020 or year > 2040:
        raise CrewRosterPdfError(f"Invalid year: {year}")

    crew = session.scalar(
        select(Crew).where(Crew.id == crew_id).where(Crew.operator_id == operator_id)
    )
    if crew is None:
        raise CrewRosterPdfError("crew member not found")

    operator = session.get(Operator, operator_id)
    if operator is None:
        raise CrewRosterPdfError("operator not found")

    weeks, summary = _gather(session, operator_id=operator_id, crew=crew, year=year, month=month)
    html = _render_html(crew, operator, year, month, weeks, summary)
    return _render_pdf(html)
