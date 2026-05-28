# KCAA audit pack — specification

> **Status:** Phase 0 placeholder. The pack is implemented in Phase 5 with
> WeasyPrint and the DN brand stylesheet.

A Ratiba audit pack is a PDF that an operator can hand to the KCAA Flight
Operations Inspectorate (FOI) as evidence of FTL compliance over a period.

## Contents (per Plan §5 Phase 5)

1. **Cover page** — operator AOC, period, generation timestamp, generator
   hash signature.
2. **Executive summary** — period overview, total FDPs, anomaly count,
   currency exceptions count.
3. **Per-crew FTL summary** — FDP utilisation vs limits over rolling 7 /
   28 / 365 days.
4. **Anomaly log** — every FDP flagged `AT_LIMIT` or worse, with corrective
   action notes.
5. **Currency status snapshot** at period close.
6. **Audit trail extract** — every roster change in the period with actor,
   timestamp, before/after.
7. **Methodology page** — which rules applied, regulatory references,
   generator version.

## Tamper-evidence

Every pack carries a SHA-256 hash of its canonical content. A verification
endpoint (`GET /api/v1/audit/packs/{id}/verify`) recomputes and compares.

## Critical dependency for Capt. Dan

Send the [KCAA sounding letter](kcaa-sounding-letter.md) before Phase 5 so
that the pack format can be co-designed with KCAA FOI feedback.
