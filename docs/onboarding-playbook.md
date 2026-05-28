# Onboarding playbook — I-Fly Air Solutions (pilot operator)

> **Target operator:** I-Fly Air Solutions
> **Target deployment:** ADC Nairobi (Phase 6)
> **Owner:** Capt. Dan Ng'ong'a (relationship), Claude Code (execution)
> **Plan reference:** §5 Phase 6 — "Onboarding playbook for first operator"

The playbook below sequences a green-field onboarding from "operator
agrees to pilot" to "first roster published in Ratiba" in two weeks
elapsed. Subsequent operators get a copy of this document customised
to their AOC; once Phase 7's LLM constraint parser ships, the
constraint-config step collapses from days to hours.

## Pre-flight — before kick-off

- [ ] Pilot contract signed (90 days up-front; 6-month minimum
      commitment per Plan §9 risk-mitigation table).
- [ ] ODPC (KDPA 2019) registration confirmed in writing for the
      operator's data hosted at ADC Nairobi.
- [ ] KCAA sounding letter (see `docs/kcaa-sounding-letter.md`)
      delivered to KCAA FOI by Dan, with audit-pack format feedback
      received and incorporated.
- [ ] Operator has nominated:
  - One Crewing Officer (dashboard user — primary day-to-day operator)
  - One Chief Pilot (sign-off authority, also a dashboard user)
  - 1–3 pilots for the first wave of `/crew/me` + Telegram pairing.

## Week 1 — data + config

### Day 1: Operator + user creation

Run inside the production backend container:

```bash
docker compose exec backend python -c "
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Operator, User
from app.models.operator import OperatorTier
from app.models.user import UserRole

session = SessionLocal()
op = Operator(
    aoc_number='IFLY-AOC-001',  # confirm before running
    name='I-Fly Air Solutions',
    base='HKJK',                # confirm primary base ICAO
    contact_email='ops@ifly.example.aero',
    tier=OperatorTier.STANDARD,
)
session.add(op); session.commit(); session.refresh(op)

session.add(User(
    operator_id=op.id,
    email='crewingofficer@ifly.example.aero',
    hashed_password=hash_password('CHANGE-ME-ON-FIRST-LOGIN'),
    full_name='I-Fly Crewing Officer',
    role=UserRole.CREWING_OFFICER,
    is_active=True,
))
session.add(User(
    operator_id=op.id,
    email='chiefpilot@ifly.example.aero',
    hashed_password=hash_password('CHANGE-ME-ON-FIRST-LOGIN'),
    full_name='I-Fly Chief Pilot',
    role=UserRole.CHIEF_PILOT,
    is_active=True,
))
session.commit()
"
```

The Crewing Officer logs in to the dashboard, **changes their password
on first login** (Phase 6 — feature lands in the bundle below), and
verifies the operator record at `/settings`.

### Day 2–3: CSV imports

Four CSVs from the operator's current Excel sheets, uploaded via the
dashboard (Phase 6 will surface this as an Onboarding wizard; until
then use `curl` or the OpenAPI docs at `/docs`):

```bash
# Dry-run first so the Crewing Officer can preview row counts + errors.
curl -X POST "https://api.ratiba.aero/api/v1/onboarding/crew?commit=false" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@i-fly-crew.csv"

# Once errors are zero, commit:
curl -X POST "https://api.ratiba.aero/api/v1/onboarding/crew?commit=true" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@i-fly-crew.csv"
```

Required columns + sample headers:

| File | Required columns |
|------|------------------|
| `crew.csv` | `employee_no,first_name,last_name,role,date_of_hire,date_of_birth,base_station,contract_type` — optional `languages` (`;`-separated), `faith_observance_flags` (`key=value;…`) |
| `type-ratings.csv` | `employee_no,aircraft_type,valid_from,valid_until` (+ optional `evidence_ref`) |
| `currencies.csv` | `employee_no,currency_type,last_completed_date,expires_date` (+ optional `evidence_ref`) |
| `historical-fdps.csv` | `employee_no,date,report_time,off_duty_time,sectors_count,flight_hours,duty_hours` |

Currency types: `LANDINGS_90D · ROUTE_FAM · MEL_COMP · LINE_CHECK · OPC · LPC · EMERG_PROC · FIRST_AID · DG · CRM · SEC_TRAINING`.

The historical-FDP file should cover the **last 90 days** so the
cumulative-window FTL rules (7/28/365 d) have history on Day 1 of
live operation. Without it, the optimiser will under-count duty in
the first week.

### Day 4–5: Operator settings + soft weights

Crewing Officer reviews `/settings`:

- AOC number, base ICAO, contact email.
- Tier — `STANDARD` for I-Fly.
- **Soft weights** (`balance_block_hours`, `faith_violation`,
  `leave_violation`, `positioning_minimisation`) — start with the
  defaults; adjust after the first generated roster if the Crewing
  Officer wants different ergonomics.

### Day 6–7: Constraint set sign-off

Walk through `docs/ftl-rules.md` with the operator's Chief Pilot.
Mark every rule as:

- ✅ Generic KCARs 2025 Part 8 baseline matches the operator's OM-A
  FTL chapter.
- ⚠ Operator's OM-A is stricter — note the override values and the
  OM-A section that supports it; Phase 6 commits the override into
  the `ftl_rules` table.

This is the step Phase 7's LLM constraint parser will automate. For
the first operator, plan for ~6 hours of joint review.

## Week 2 — operate

### Day 8: First generated roster

Run the optimiser for the next 28 days, publish through the dashboard,
verify with the Chief Pilot. The roster calendar now shows the FTL
legality pill on each duty day; anything not `LEGAL` needs explicit
discussion before publication.

### Day 9: Bot + crew web view pairing

For each pilot in the first wave:

1. Crewing Officer clicks "Issue pairing code" on the crew page.
2. Pilot enters `/start <code>` in Telegram **or** opens
   `https://ratiba.aero/crew/me` and enters the code.
3. Pilot is paired in <60 s. Verify they can run `/duty` and `/roster`
   and get sensible answers.

### Day 10: KCAA audit pack rehearsal

Generate a 28-day pack via `/audit/generate`. Walk through every
section with the Chief Pilot — does the per-crew FTL summary match
their expectation? Are anomalies anomalous-for-good-reasons? Does the
audit trail tell a clean story?

This is the dress rehearsal for the real KCAA inspection.

### Day 11–14: Operate live

The Crewing Officer drives day-to-day work from the dashboard.
**Weekly check-ins** (per Plan §5 Phase 6) with Dan: what's working,
what isn't, what regressed.

Bug triage SLA (per Plan §5 Phase 6):

| Severity   | First response |
|-----------|---------------:|
| Critical  |          4 h   |
| High      |         24 h   |
| Medium    |          5 d   |

## Exit criteria — Phase 6 sign-off

Per Plan §5 Phase 6:

- [ ] One full roster cycle (28 days) generated, published, and
      operated **without manual override**.
- [ ] Zero critical bugs in production for 14 consecutive days.
- [ ] Crewing Officer self-reports ≥ 50 % reduction in rostering hours
      vs the Excel baseline.
- [ ] First audit pack presented (informally) to operator's KCAA contact.
