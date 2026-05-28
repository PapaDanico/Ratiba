# Onboarding playbook (operator-agnostic)

> **Plan reference:** §5 Phase 6 — "Onboarding playbook for first
> operator". ADR 0006 paused the I-Fly-specific commitment until at
> least one round of prospective-user feedback has shaped the product;
> this document is now the generic template every operator's
> onboarding starts from.

The playbook below sequences a green-field onboarding from "operator
agrees to evaluate" to "first roster published in Ratiba" in two
calendar weeks. The first operator's onboarding is treated as a
working session — gaps it surfaces feed back into this template for
subsequent operators.

## Pre-flight — before kick-off

- [ ] Evaluation agreement signed (no-cost trial; conversion terms
      to be agreed after the first 30 days).
- [ ] Operator-specific KDPA paperwork sketched, even if not yet
      filed. We can run the trial against operator-supplied data in a
      KDPA-resident environment without formal ODPC registration as
      long as the trial is short and the data is anonymisable on
      request.
- [ ] Operator has nominated:
  - One Crewing Officer (dashboard primary).
  - One Chief Pilot (sign-off authority, dashboard user).
  - 1–3 pilots for the first `/crew/me` + Telegram pairing wave.
- [ ] (Optional but recommended) KCAA sounding letter
      (`docs/kcaa-sounding-letter.md`) delivered by the operator's
      DFO or POC to KCAA FOI before the first audit pack is shown to
      KCAA personnel.

## Week 1 — data + config

### Day 1: Operator + user creation

Substitute the operator's AOC number, name, base, and contacts:

```bash
docker compose exec backend python -c "
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Operator, User
from app.models.operator import OperatorTier
from app.models.user import UserRole

session = SessionLocal()
op = Operator(
    aoc_number='<AOC>',           # operator's KCAA AOC number
    name='<Operator Name>',
    base='<ICAO>',                # primary base, e.g. HKJK
    contact_email='<ops email>',
    tier=OperatorTier.STANDARD,
)
session.add(op); session.commit(); session.refresh(op)

session.add(User(
    operator_id=op.id,
    email='<crewing-officer email>',
    hashed_password=hash_password('CHANGE-ME-ON-FIRST-LOGIN'),
    full_name='<Crewing Officer name>',
    role=UserRole.CREWING_OFFICER,
    is_active=True,
))
session.add(User(
    operator_id=op.id,
    email='<chief pilot email>',
    hashed_password=hash_password('CHANGE-ME-ON-FIRST-LOGIN'),
    full_name='<Chief Pilot name>',
    role=UserRole.CHIEF_PILOT,
    is_active=True,
))
session.commit()
"
```

The Crewing Officer logs in to the dashboard, changes their password,
and verifies the operator record at `/settings`.

### Day 2–3: CSV imports

Four CSVs from the operator's current Excel sheets, uploaded via the
dashboard's Onboarding endpoints (preview in dry-run, then commit):

```bash
# Dry-run preview — surface row counts + per-row errors first.
curl -X POST "$BASE/api/v1/onboarding/crew?commit=false" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@crew.csv"

# Commit once errors are zero.
curl -X POST "$BASE/api/v1/onboarding/crew?commit=true" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@crew.csv"
```

Required columns by file:

| File | Required columns |
|------|------------------|
| `crew.csv` | `employee_no, first_name, last_name, role, date_of_hire, date_of_birth, base_station, contract_type` — optional `languages` (`;`-separated), `faith_observance_flags` (`key=value;…`) |
| `type-ratings.csv` | `employee_no, aircraft_type, valid_from, valid_until` (+ optional `evidence_ref`) |
| `currencies.csv` | `employee_no, currency_type, last_completed_date, expires_date` (+ optional `evidence_ref`) |
| `historical-fdps.csv` | `employee_no, date, report_time, off_duty_time, sectors_count, flight_hours, duty_hours` |

Currency types accepted by the schema:
`LANDINGS_90D · ROUTE_FAM · MEL_COMP · LINE_CHECK · OPC · LPC ·
EMERG_PROC · FIRST_AID · DG · CRM · SEC_TRAINING`.

Sample CSVs that match these schemas are in `docs/sample-csvs/` — use
them as templates.

The historical-FDP file should cover the **last 90 days** so the
cumulative-window FTL rules (7/28/365 d) have history on Day 1 of
live operation.

### Day 4–5: Operator settings + soft weights

Crewing Officer reviews `/settings`:

- AOC number, base ICAO, contact email.
- Tier — `STANDARD` is the default; `ENTRY` if it's a smaller setup
  on a trial; `PLUS` if the operator wants the full SLA.
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
  OM-A section that supports it; commit the override into the
  `ftl_rules` table.

This is the step Phase 7's LLM constraint parser will automate. For
the first operator we manually walk it; plan for ~6 hours of joint
review.

## Week 2 — operate

### Day 8: First generated roster

Run the optimiser for the next 28 days
(`POST /api/v1/roster/generate`), publish through the dashboard,
verify with the Chief Pilot. The roster calendar shows the FTL
legality pill on each duty day; anything not `LEGAL` needs explicit
discussion before publication.

### Day 9: Bot + crew web view pairing

For each pilot in the first wave:

1. Crewing Officer issues a pairing code on the crew page
   (`POST /api/v1/crew/{id}/pairing-token`).
2. Pilot sends `/start <code>` in Telegram **or** opens
   `https://<your-host>/crew/me` and enters the code.
3. Verify the pilot can run `/duty` and `/roster` and get sensible
   answers.

### Day 10: KCAA audit pack rehearsal

Generate a 28-day pack via `/audit/generate`. Walk through every
section with the Chief Pilot — does the per-crew FTL summary match
their expectation? Are anomalies anomalous-for-good-reasons? Does the
audit trail tell a clean story?

This is the dress rehearsal for the real KCAA inspection.

### Day 11–14: Operate live

The Crewing Officer drives day-to-day work from the dashboard.
**Weekly check-ins** with the DN Consultancy team: what's working,
what isn't, what regressed.

Bug triage SLA:

| Severity   | First response |
|-----------|---------------:|
| Critical  |          4 h   |
| High      |         24 h   |
| Medium    |          5 d   |

## Exit criteria — first 30-day stability watch

Per Plan §5 Phase 6, the gate for moving from evaluation to commit:

- [ ] One full roster cycle (28 days) generated, published, and
      operated **without manual override**.
- [ ] Zero critical bugs in production for 14 consecutive days.
- [ ] Crewing Officer self-reports ≥ 50 % reduction in rostering hours
      vs the Excel baseline.
- [ ] First audit pack presented (informally) to operator's KCAA
      contact.

## After the first operator

Each subsequent operator gets a copy of this template with their
specifics filled in. Lessons from operator #1 — column-naming quirks,
currency-type extensions, OM-A-specific FTL rules — feed back into
this document and into Phase 7's LLM constraint parser.
