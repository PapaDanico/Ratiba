# ADR 0004: Phase 1 kick-off decisions

* **Status:** Accepted — 2026-05-27
* **Deciders:** Capt. Dan Ng'ong'a, Claude Code
* **Reference:** Project Plan v1.0 §11 (three questions before Phase 1)

## Context

Plan §11 asked three questions whose answers gate the start of Phase 1
(FTL engine + core data model). Dan's response on 2026-05-27 settled all
three.

## Decisions

1. **Working name = Ratiba** — proceed. A formal KE trademark check is
   still advisable before any external launch but does not block
   engineering.

2. **First pilot operator — undetermined; two candidates.** Either
   **Jubba Airways** or **I-Fly Air Solutions** will be the Phase 6
   deployment target. Final selection deferred to Dan; does not block
   Phase 1 because we have chosen the generic baseline (decision 3).

3. **FTL rule baseline = generic KCARs 2025 Part 8** (Dan's call given to
   Claude Code). Operator-specific OM-A deltas will be layered in Phase 6
   once the operator and their OM-A FTL chapter are confirmed.

## Consequences

- Phase 1 can begin immediately on the generic baseline without waiting
  for any operator artefacts.
- `docs/ftl-rules.md` is the working document for the generic baseline.
- Operator customisation is bounded inside Phase 6 — Phase 1's `ftl_rules`
  table already supports it through `source` (`MANUAL_REVIEW` /
  `LLM_PARSED` / `OM_A_REVISION_X`) and per-rule overrides.
- Phase 7's LLM constraint parser eventually subsumes the Phase 6
  customisation step.
