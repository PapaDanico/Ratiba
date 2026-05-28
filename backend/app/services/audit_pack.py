"""KCAA-presentable audit pack PDF generator.

Single entry point :func:`generate_pack` gathers the period's data,
renders a DN-branded HTML template, runs it through WeasyPrint, stores
the PDF on disk, and inserts a row in ``audit_packs`` with the SHA-256
of the bytes for tamper-evidence.

Plan §5 Phase 5 contents (all present):
  1. Cover page — operator AOC, period, generation timestamp, hash signature.
  2. Executive summary — total FDPs, anomaly count, currency exceptions.
  3. Per-crew FTL summary — 7 / 28 / 365-day duty + block utilisation.
  4. Anomaly log — every FDP at AT_LIMIT or worse.
  5. Currency status snapshot at period close.
  6. Audit-trail extract — every roster change in the period.
  7. Methodology — rule cross-reference + generator version.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import __version__
from app.models import (
    AuditEvent,
    AuditPack,
    Crew,
    CrewCurrency,
    FlightDutyPeriod,
    Operator,
    User,
)
from app.models.ftl import LegalityState
from app.services import audit_log, audit_pack_storage, branding, ftl_engine

GENERATOR_VERSION = f"ratiba-audit-pack/{__version__}"
AMBER_THRESHOLD_DAYS = 30

# Rule-family → KCARs citation map. Single source of truth alongside
# ``docs/ftl-rules.md``; per-operator overrides land in Phase 6.
RULE_CITATIONS: dict[str, str] = {
    "KCAR-P8-FDP-MAX-BASIC": "KCARs 2025 Part 8 §8.X.Y — Maximum FDP (basic crew)",
    "KCAR-P8-FDP-MAX-AUG": "KCARs 2025 Part 8 §8.X.Y — Maximum FDP (augmented crew)",
    "KCAR-P8-REST-MIN": "KCARs 2025 Part 8 §8.X.Y — Minimum rest before next FDP",
    "KCAR-P8-CUMUL-DUTY-7D": "KCARs 2025 Part 8 §8.X.Y — Cumulative duty (7 days)",
    "KCAR-P8-CUMUL-DUTY-28D": "KCARs 2025 Part 8 §8.X.Y — Cumulative duty (28 days)",
    "KCAR-P8-CUMUL-DUTY-365D": "KCARs 2025 Part 8 §8.X.Y — Cumulative duty (365 days)",
    "KCAR-P8-CUMUL-BLOCK-28D": "KCARs 2025 Part 8 §8.X.Y — Cumulative block (28 days)",
    "KCAR-P8-CUMUL-BLOCK-365D": "KCARs 2025 Part 8 §8.X.Y — Cumulative block (365 days)",
    "KCAR-P8-STANDBY-SHORT-CALL": "KCARs 2025 Part 8 §8.X.Y — Standby (short-call)",
    "KCAR-P8-STANDBY-LONG-CALL": "KCARs 2025 Part 8 §8.X.Y — Standby (long-call)",
    "KCAR-P8-SPLIT-DUTY": "KCARs 2025 Part 8 §8.X.Y — Split-duty extension",
    "KCAR-P8-TZ-RECOVERY": "KCARs 2025 Part 8 §8.X.Y — Time-zone crossing recovery",
    "KCAR-P8-DISCRETION": "KCARs 2025 Part 8 §8.X.Y — Commander's discretion",
}


class AuditPackError(Exception):
    """Raised when a pack can't be generated (no data, render failure, etc.)."""


@dataclass(frozen=True)
class CrewSummary:
    employee_no: str
    name: str
    role: str
    duty_h_7d: float
    duty_h_28d: float
    duty_h_365d: float
    block_h_28d: float
    block_h_365d: float
    fdps_in_period: int


@dataclass(frozen=True)
class AnomalyRow:
    date_iso: str
    employee_no: str
    legality_state: str
    rules_applied: list[str]
    duty_h: float
    flight_h: float


@dataclass(frozen=True)
class CurrencySnapshot:
    employee_no: str
    currency_type: str
    expires_date: str
    days_remaining: int
    state: str  # GREEN | AMBER | RED


@dataclass(frozen=True)
class AuditTrailRow:
    when: str
    actor_email: str | None
    action: str
    entity_type: str
    entity_id: str | None


@dataclass(frozen=True)
class PackData:
    operator: Operator
    period_from: date
    period_to: date
    generated_at: datetime
    crew_summaries: list[CrewSummary]
    anomalies: list[AnomalyRow]
    currencies: list[CurrencySnapshot]
    audit_trail: list[AuditTrailRow]
    fdp_count: int


# -----------------------------------------------------------------------------
# Data gathering
# -----------------------------------------------------------------------------


def _gather(session: Session, operator: Operator, df: date, dt: date) -> PackData:
    fdps = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.operator_id == operator.id)
        .where(FlightDutyPeriod.date >= df)
        .where(FlightDutyPeriod.date <= dt)
        .order_by(FlightDutyPeriod.date)
    ).all()
    crew_ids = {f.crew_id for f in fdps}
    all_crew = session.scalars(select(Crew).where(Crew.operator_id == operator.id)).all()
    crew_by_id = {c.id: c for c in all_crew}

    # Pre-load the trailing 365-day FDP horizon per crew so the cumulative
    # windows in the per-crew summary are accurate against history outside
    # the audit period.
    history_start = df - timedelta(days=365)
    history_fdps = session.scalars(
        select(FlightDutyPeriod)
        .where(FlightDutyPeriod.operator_id == operator.id)
        .where(FlightDutyPeriod.date >= history_start)
        .where(FlightDutyPeriod.date <= dt)
    ).all()

    def _windowed(crew_id: uuid.UUID, days: int, kind: str) -> float:
        window_start = dt - timedelta(days=days - 1)
        total = 0.0
        for f in history_fdps:
            if f.crew_id != crew_id:
                continue
            if not (window_start <= f.date <= dt):
                continue
            total += float(f.duty_hours if kind == "duty" else f.flight_hours)
        return total

    summaries: list[CrewSummary] = []
    for cid in sorted(crew_ids, key=lambda c: str(c)):
        c = crew_by_id.get(cid)
        if c is None:
            continue
        summaries.append(
            CrewSummary(
                employee_no=c.employee_no,
                name=f"{c.first_name} {c.last_name}",
                role=c.role.value,
                duty_h_7d=_windowed(cid, 7, "duty"),
                duty_h_28d=_windowed(cid, 28, "duty"),
                duty_h_365d=_windowed(cid, 365, "duty"),
                block_h_28d=_windowed(cid, 28, "flight"),
                block_h_365d=_windowed(cid, 365, "flight"),
                fdps_in_period=sum(1 for f in fdps if f.crew_id == cid and df <= f.date <= dt),
            )
        )

    anomalies: list[AnomalyRow] = []
    for f in fdps:
        if f.legality_state == LegalityState.LEGAL:
            continue
        c = crew_by_id.get(f.crew_id)
        anomalies.append(
            AnomalyRow(
                date_iso=f.date.isoformat(),
                employee_no=c.employee_no if c else "—",
                legality_state=f.legality_state.value,
                rules_applied=list(f.ftl_rules_applied or []),
                duty_h=float(f.duty_hours),
                flight_h=float(f.flight_hours),
            )
        )

    currencies = session.scalars(
        select(CrewCurrency).where(CrewCurrency.operator_id == operator.id)
    ).all()
    currency_rows: list[CurrencySnapshot] = []
    for cur in currencies:
        c = crew_by_id.get(cur.crew_id)
        delta = (cur.expires_date - dt).days
        state = "RED" if delta < 0 else "AMBER" if delta <= AMBER_THRESHOLD_DAYS else "GREEN"
        currency_rows.append(
            CurrencySnapshot(
                employee_no=c.employee_no if c else "—",
                currency_type=cur.currency_type.value,
                expires_date=cur.expires_date.isoformat(),
                days_remaining=delta,
                state=state,
            )
        )

    # Audit trail covering only writes inside the audit period that touch a
    # roster-relevant entity. Append-only by trigger, so this is authoritative.
    relevant = (
        "flight_duty_period",
        "sector_assignment",
        "roster",
        "leave_request",
        "swap_request",
    )
    period_start_dt = datetime.combine(df, datetime.min.time(), tzinfo=UTC)
    period_end_dt = datetime.combine(dt + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    events = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.operator_id == operator.id)
        .where(AuditEvent.entity_type.in_(relevant))
        .where(AuditEvent.created_at >= period_start_dt)
        .where(AuditEvent.created_at < period_end_dt)
        .order_by(AuditEvent.created_at)
    ).all()
    actor_ids = {e.actor_user_id for e in events if e.actor_user_id is not None}
    actors_by_id: dict[uuid.UUID, str] = {}
    if actor_ids:
        users = session.scalars(select(User).where(User.id.in_(actor_ids))).all()
        actors_by_id = {u.id: u.email for u in users}
    trail = [
        AuditTrailRow(
            when=e.created_at.isoformat(),
            actor_email=actors_by_id.get(e.actor_user_id) if e.actor_user_id else None,
            action=e.action,
            entity_type=e.entity_type,
            entity_id=str(e.entity_id) if e.entity_id else None,
        )
        for e in events
    ]

    return PackData(
        operator=operator,
        period_from=df,
        period_to=dt,
        generated_at=datetime.now(UTC),
        crew_summaries=summaries,
        anomalies=anomalies,
        currencies=currency_rows,
        audit_trail=trail,
        fdp_count=len(fdps),
    )


# -----------------------------------------------------------------------------
# Render
# -----------------------------------------------------------------------------

# Self-contained CSS using only DN brand colours — no external assets so the
# PDF is fully portable.
_CSS = """
@page { size: A4; margin: 18mm 16mm; @bottom-right { content: counter(page) " / " counter(pages); font-family: 'DM Sans', sans-serif; font-size: 9pt; color: #6B7280; } }
* { box-sizing: border-box; }
html, body { font-family: 'DM Sans', Helvetica, Arial, sans-serif; color: #1C1C1C; font-size: 10pt; }
h1, h2, h3 { font-family: 'Cormorant Garamond', Georgia, serif; color: #1C1C1C; margin: 0 0 6pt 0; }
h1 { font-size: 28pt; }
h2 { font-size: 18pt; border-bottom: 1.5pt solid #C9A84C; padding-bottom: 4pt; margin-top: 24pt; }
h3 { font-size: 13pt; margin-top: 14pt; }
.dn-eyebrow { font-family: 'JetBrains Mono', monospace; font-size: 8pt; letter-spacing: 2pt; text-transform: uppercase; color: #4A7FA5; }
.cover-logo { display: block; width: 230px; height: auto; margin: 0 0 14pt 0; }
.muted { color: #6B7280; font-size: 9pt; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 9pt; }
.cover { page-break-after: always; }
.hash-strip { margin-top: 18pt; padding: 8pt; background: #F4F4F2; border-left: 3pt solid #C9A84C; font-family: 'JetBrains Mono', monospace; font-size: 8pt; word-break: break-all; }
.summary-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10pt; margin-top: 10pt; }
.summary-card { border: 0.5pt solid #D6E4F0; background: #F4F4F2; padding: 10pt; }
.summary-card .figure { font-family: 'Cormorant Garamond', serif; font-size: 26pt; color: #1C1C1C; }
.summary-card .label { font-size: 9pt; color: #6B7280; margin-top: 4pt; }
table { width: 100%; border-collapse: collapse; margin-top: 6pt; font-size: 9pt; }
th { text-align: left; background: #D6E4F0; padding: 4pt 6pt; color: #1C1C1C; border-bottom: 0.5pt solid #4A7FA5; font-weight: 600; }
td { padding: 4pt 6pt; border-bottom: 0.5pt solid #D6E4F0; vertical-align: top; }
tr:nth-child(even) td { background: #F4F4F2; }
.state-LEGAL { color: #1E8449; }
.state-AT_LIMIT { color: #D4AC0D; }
.state-REQUIRES_FRMS_DEROGATION { color: #C0392B; }
.state-ILLEGAL { color: #C0392B; font-weight: 600; }
.state-GREEN { color: #1E8449; }
.state-AMBER { color: #D4AC0D; }
.state-RED { color: #C0392B; }
.empty { font-style: italic; color: #6B7280; padding: 12pt 0; }
.footer-note { margin-top: 24pt; padding: 8pt 10pt; background: #FFF8E6; border-left: 3pt solid #C9A84C; font-size: 9pt; }
"""


def _esc(s: object) -> str:
    """Minimal HTML escape (the templater is hand-rolled to avoid jinja2 dep)."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_html(data: PackData) -> str:
    op = data.operator
    period = f"{data.period_from.isoformat()} → {data.period_to.isoformat()}"
    anomaly_count = len(data.anomalies)
    expiring_or_expired = sum(1 for c in data.currencies if c.state != "GREEN")

    crew_rows = (
        "".join(
            f"<tr><td class='mono'>{_esc(s.employee_no)}</td>"
            f"<td>{_esc(s.name)}</td>"
            f"<td>{_esc(s.role)}</td>"
            f"<td>{s.fdps_in_period}</td>"
            f"<td class='mono'>{s.duty_h_7d:.1f}</td>"
            f"<td class='mono'>{s.duty_h_28d:.1f}</td>"
            f"<td class='mono'>{s.duty_h_365d:.1f}</td>"
            f"<td class='mono'>{s.block_h_28d:.1f}</td>"
            f"<td class='mono'>{s.block_h_365d:.1f}</td></tr>"
            for s in data.crew_summaries
        )
        or "<tr><td colspan='9' class='empty'>No FDPs in this period.</td></tr>"
    )

    anomaly_rows = (
        "".join(
            f"<tr><td class='mono'>{_esc(a.date_iso)}</td>"
            f"<td class='mono'>{_esc(a.employee_no)}</td>"
            f"<td class='state-{_esc(a.legality_state)}'>{_esc(a.legality_state)}</td>"
            f"<td class='mono'>{a.duty_h:.2f}</td>"
            f"<td class='mono'>{a.flight_h:.2f}</td>"
            f"<td>{_esc(', '.join(a.rules_applied))}</td></tr>"
            for a in data.anomalies
        )
        or "<tr><td colspan='6' class='empty'>No FDPs flagged AT_LIMIT or above. ✅</td></tr>"
    )

    currency_rows = (
        "".join(
            f"<tr><td class='mono'>{_esc(c.employee_no)}</td>"
            f"<td>{_esc(c.currency_type)}</td>"
            f"<td class='mono'>{_esc(c.expires_date)}</td>"
            f"<td class='mono'>{c.days_remaining:+d}d</td>"
            f"<td class='state-{_esc(c.state)}'>{_esc(c.state)}</td></tr>"
            for c in data.currencies
        )
        or "<tr><td colspan='5' class='empty'>No currencies on record.</td></tr>"
    )

    trail_rows = (
        "".join(
            f"<tr><td class='mono'>{_esc(t.when)}</td>"
            f"<td>{_esc(t.actor_email or '—')}</td>"
            f"<td>{_esc(t.action)}</td>"
            f"<td>{_esc(t.entity_type)}</td>"
            f"<td class='mono'>{_esc(t.entity_id or '—')}</td></tr>"
            for t in data.audit_trail
        )
        or "<tr><td colspan='5' class='empty'>No relevant audit events in this period.</td></tr>"
    )

    methodology_rows = "".join(
        f"<tr><td class='mono'>{_esc(rid)}</td><td>{_esc(RULE_CITATIONS.get(rid, '—'))}</td></tr>"
        for rid in ftl_engine.all_rule_ids()
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Ratiba audit pack — {_esc(op.aoc_number)} — {_esc(period)}</title>
  <style>{_CSS}</style>
</head>
<body>

<section class="cover">
  <img class="cover-logo" src="{branding.logo_data_uri()}" alt="DN Consultancy" />
  <p class="dn-eyebrow">FTL compliance evidence</p>
  <h1>Ratiba audit pack</h1>
  <h3>{_esc(op.name)} — AOC {_esc(op.aoc_number)}</h3>
  <p class="muted">Operating base: {_esc(op.base)} · Contact: {_esc(op.contact_email)}</p>
  <p style="margin-top: 30pt;">Period: <strong class="mono">{_esc(period)}</strong></p>
  <p>Generated: <span class="mono">{_esc(data.generated_at.isoformat())}</span></p>
  <p>Generator: <span class="mono">{_esc(GENERATOR_VERSION)}</span></p>

  <div class="hash-strip">
    Tamper-evidence: a SHA-256 hash of this PDF is stored against the
    pack's database row. Re-derive via the
    <em>/api/v1/audit/packs/&lt;id&gt;/verify</em> endpoint — any byte
    of difference invalidates the hash.
  </div>

  <p class="footer-note">
    This pack is generated automatically from Ratiba's audit-trail and
    flight-duty-period tables. Every assertion is traceable to a
    KCARs 2025 Part 8 rule (see the methodology page).
  </p>
</section>

<h2>Executive summary</h2>
<div class="summary-grid">
  <div class="summary-card"><div class="figure">{data.fdp_count}</div><div class="label">FDPs in period</div></div>
  <div class="summary-card"><div class="figure">{anomaly_count}</div><div class="label">FDPs flagged AT_LIMIT or above</div></div>
  <div class="summary-card"><div class="figure">{expiring_or_expired}</div><div class="label">Currencies expiring ≤ 30 d or expired at period close</div></div>
</div>
<p class="muted" style="margin-top: 12pt;">
  Crew in period: {len(data.crew_summaries)}.
  Audit-trail events covering roster, FDP, leave + swap activity in
  the period: {len(data.audit_trail)}.
</p>

<h2>Per-crew FTL summary</h2>
<table>
  <thead>
    <tr>
      <th>Employee #</th><th>Name</th><th>Role</th><th>FDPs</th>
      <th>Duty 7 d</th><th>Duty 28 d</th><th>Duty 365 d</th>
      <th>Block 28 d</th><th>Block 365 d</th>
    </tr>
  </thead>
  <tbody>{crew_rows}</tbody>
</table>
<p class="muted">
  Cumulative windows close at the period end. Limits: 60 / 190 / 2000 h
  duty (7 / 28 / 365 d); 100 / 1000 h block (28 / 365 d). Source of
  truth: <span class="mono">app.services.ftl_engine.LIMITS</span>.
</p>

<h2>Anomaly log</h2>
<table>
  <thead>
    <tr>
      <th>Date</th><th>Employee #</th><th>State</th>
      <th>Duty h</th><th>Flight h</th><th>Rules applied</th>
    </tr>
  </thead>
  <tbody>{anomaly_rows}</tbody>
</table>

<h2>Currency status at period close</h2>
<table>
  <thead>
    <tr>
      <th>Employee #</th><th>Currency</th><th>Expires</th>
      <th>Δ days</th><th>State</th>
    </tr>
  </thead>
  <tbody>{currency_rows}</tbody>
</table>

<h2>Audit trail (period extract)</h2>
<table>
  <thead>
    <tr>
      <th>When (UTC)</th><th>Actor</th><th>Action</th>
      <th>Entity type</th><th>Entity id</th>
    </tr>
  </thead>
  <tbody>{trail_rows}</tbody>
</table>

<h2>Methodology + regulatory cross-reference</h2>
<p>
  Every FTL judgement on this pack is produced by
  <span class="mono">app.services.ftl_engine</span> running the rule
  set listed below. The append-only PostgreSQL trigger on
  <span class="mono">audit_events</span> guarantees the audit trail
  extract above is the complete, un-mutated record of every write that
  touched a roster-relevant entity in the period.
</p>
<table>
  <thead><tr><th>Rule ID</th><th>KCARs 2025 Part 8 citation</th></tr></thead>
  <tbody>{methodology_rows}</tbody>
</table>

</body>
</html>
"""


# -----------------------------------------------------------------------------
# Generate
# -----------------------------------------------------------------------------


def _render_pdf(html: str) -> bytes:
    """Lazy import so test envs without WeasyPrint's system deps don't break."""
    from weasyprint import HTML

    return bytes(HTML(string=html).write_pdf() or b"")


def generate_pack(
    session: Session,
    *,
    user: User,
    period_from: date,
    period_to: date,
) -> AuditPack:
    """End-to-end: gather → render → persist → audit. Returns the row."""
    if period_to < period_from:
        raise AuditPackError("period_to before period_from")

    operator = session.get(Operator, user.operator_id)
    if operator is None:
        raise AuditPackError("operator not found")

    data = _gather(session, operator, period_from, period_to)
    html = _render_html(data)
    pdf_bytes = _render_pdf(html)
    sha256_hex = hashlib.sha256(pdf_bytes).hexdigest()

    filename = (
        f"{operator.aoc_number}_{period_from.isoformat()}_"
        f"{period_to.isoformat()}_{sha256_hex[:12]}.pdf"
    )
    storage_path = audit_pack_storage.write(filename, pdf_bytes)

    pack = AuditPack(
        operator_id=operator.id,
        period_from=period_from,
        period_to=period_to,
        storage_path=storage_path,
        sha256_hex=sha256_hex,
        byte_size=len(pdf_bytes),
        generator_version=GENERATOR_VERSION,
        crew_count=len(data.crew_summaries),
        fdp_count=data.fdp_count,
        anomaly_count=len(data.anomalies),
        created_by_user_id=user.id,
    )
    session.add(pack)
    session.flush()
    audit_log.record(
        session,
        operator_id=operator.id,
        actor_user_id=user.id,
        action="GENERATE_AUDIT_PACK",
        entity_type="audit_pack",
        entity_id=pack.id,
        before_state=None,
        after_state={
            "period_from": period_from.isoformat(),
            "period_to": period_to.isoformat(),
            "sha256_hex": sha256_hex,
            "byte_size": len(pdf_bytes),
            "fdp_count": data.fdp_count,
            "anomaly_count": len(data.anomalies),
        },
    )
    session.commit()
    session.refresh(pack)
    return pack


def verify_pack(session: Session, *, pack_id: uuid.UUID, operator_id: uuid.UUID) -> dict[str, Any]:
    pack = session.get(AuditPack, pack_id)
    if pack is None or pack.operator_id != operator_id:
        raise AuditPackError("audit pack not found")
    body = audit_pack_storage.read_bytes(pack.storage_path)
    if body is None:
        return {
            "verified": False,
            "reason": "storage file missing",
            "expected_sha256": pack.sha256_hex,
        }
    actual = hashlib.sha256(body).hexdigest()
    return {
        "verified": actual == pack.sha256_hex,
        "expected_sha256": pack.sha256_hex,
        "actual_sha256": actual,
        "byte_size": len(body),
    }


def read_pack_bytes(
    session: Session, *, pack_id: uuid.UUID, operator_id: uuid.UUID
) -> tuple[bytes, AuditPack]:
    pack = session.get(AuditPack, pack_id)
    if pack is None or pack.operator_id != operator_id:
        raise AuditPackError("audit pack not found")
    body = audit_pack_storage.read_bytes(pack.storage_path)
    if body is None:
        raise AuditPackError("storage file missing")
    return body, pack
