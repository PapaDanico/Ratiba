# ADR 0005: First pilot operator + hosting region

* **Status:** Accepted — 2026-05-28
* **Deciders:** Capt. Dan Ng'ong'a (delegated to Claude Code under "your
  discretion within our current operational framework"), Claude Code
* **Reference:** Project Plan v1.0 §11 Q2, §2, §5 Phase 6

## Context

Plan §11 Q2 left the first pilot operator open between two candidates;
Plan §2 + §5 Phase 6 left the hosting region open between AWS Cape Town
(`af-south-1`) and Africa Data Centres / Liquid (Nairobi). Both calls
need to land before Phase 6 can do useful work (the onboarding playbook
references the operator; the deployment runbook references the region).

## Decisions

### Pilot operator — **I-Fly Air Solutions**

Selected over Jubba Airways for the first deployment because:

- I-Fly is a Kenyan-AOC operator, so KCAA is unambiguously the primary
  regulator. Jubba's regulatory primary lies elsewhere in the EAC.
  Plan §5 Phase 5's KCAA sounding letter and Phase 6's regulatory
  hand-shake both run more smoothly through a Kenyan AOC.
- The smaller scale of I-Fly maps better to Plan §1's target segment
  (3–10 aircraft, 15–60 flight crew) — fewer simultaneous moving parts
  on the first 30-day stability watch.
- The conversational distance to KCAA Flight Operations Inspectorate
  for ad-hoc questions during the pilot is shortest with a Kenyan
  operator + Kenyan regulator + Nairobi hosting.

This decision is reversible at low cost: the seed data references the
operator by AOC + name, and Ratiba's multi-tenancy means a second
operator can be onboarded in parallel without schema changes.

### Hosting region — **Africa Data Centres Nairobi (Liquid)**

Selected over AWS Cape Town (`af-south-1`) for the first deployment
because:

- KDPA 2019 data residency: ADC keeps personal data within Kenya
  without needing the cross-border-transfer safeguards an `af-south-1`
  deployment would require. Cleanest story for the first
  ODPC registration and the first KCAA conversation.
- KCAA's expectation (per Plan §2): Kenyan operators with personal
  data + safety records hosted in Kenya. ADC Nairobi matches.
- Lower latency to the East African pilot operator and to KCAA FOI
  endpoints than `af-south-1`.

Trade-offs accepted:

- ADC Nairobi has a smaller managed-services catalogue than
  `af-south-1`. We'll run PostgreSQL on VMs with point-in-time
  backups rather than a managed-RDS-style offering for the pilot.
- Migrating to `af-south-1` post-pilot is an upgrade path, not a
  blocker. The application stack (Postgres + Redis + Docker) is
  cloud-agnostic.

## Consequences

- `scripts/seed.py` updated to default to I-Fly Air Solutions for
  fresh dev environments.
- `docs/onboarding-playbook.md` is the I-Fly-specific runbook for the
  first deployment; subsequent operators get their own runbook seeded
  from this one.
- `docs/deployment-runbook.md` targets ADC Nairobi infrastructure
  shape (VM-hosted Postgres + Redis + Docker Compose; TLS via Let's
  Encrypt; off-site encrypted backups to a separate ADC tenant).
- Phase 7's LLM constraint parser ingests the **I-Fly OM-A FTL chapter**
  as its first real test corpus once it lands.
- The KCAA sounding letter draft (`docs/kcaa-sounding-letter.md`)
  remains generic; we'll add the I-Fly operator-specific paragraph
  when Dan signs and sends it.
