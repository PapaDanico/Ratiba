# ADR 0007: Phase 7 — LLM-assisted OM-A constraint parser

* **Status:** Accepted — 2026-05-28
* **Deciders:** Capt. Dan Ng'ong'a, Claude Code
* **Reference:** Project Plan v1.0 §5 Phase 7

## Context

Onboarding operator #1 meant hand-coding their OM-A flight-time-limitation
(FTL) chapter into Ratiba's rule schema — a ~6-week analyst task. Phase 7's
goal is to collapse that to ~2 weeks by having Claude Sonnet propose the
operator's numeric limits, with a human reviewing every proposal before it
binds. The regulator-facing nature of FTL means the LLM can *propose* but
never *decide*: a crewing officer signs off each value.

## Decision

1. **Flat, baseline-diffed rule keys.** The parser emits a flat
   `rule_key -> value` map. Nested baseline groups in
   `ftl_engine.LIMITS` (e.g. `fdp_max_basic_by_band`) are flattened with
   dotted keys (`fdp_max_basic_by_band.WOCL`) so every limit is an
   independently reviewable, commentable unit. Each proposal is diffed
   against the KCARs 2025 baseline so reviewers see *changes*, not a wall
   of numbers.

2. **Three tables, append-only review trail.** `constraint_sets` (one per
   OM-A parse, tied to the OM-A revision), `constraint_rules` (per-limit
   proposal + baseline + per-rule verdict), and
   `constraint_review_comments` (decision trail). Migration
   `0006_constraint_sets`.

3. **Sonnet via the existing `llm_client`.** Reuses `parser_complete`
   (Sonnet) and its usage telemetry. The parser asks for strict JSON with a
   verbatim `source_excerpt` and a `confidence` per rule; output is parsed
   leniently (stray prose/fences tolerated) and unknown keys are dropped.

4. **Acceptance gate.** A set can only be accepted once every *proposed*
   rule (one the LLM actually returned a value for) has an explicit verdict
   — accept / edit / reject. Unmentioned rules silently keep the baseline.
   Acceptance is a status transition + audit event; it does not yet
   overwrite the engine's module-level `LIMITS`.

5. **JSONB `none_as_null=True`.** So "no proposal" is SQL `NULL`, letting the
   acceptance gate filter proposals with `IS NOT NULL` rather than tripping
   over JSON `'null'`.

## Consequences

* New `/api/v1/constraints/*` surface + a "FTL setup" dashboard page giving
  the diff/review workflow end to end.
* **Deferred:** binding an accepted set into the live FTL engine (the engine
  reads a module-global `LIMITS`; per-operator overrides need a limits-
  injection refactor) and full verdict-replay round-trip validation against
  a historical roster. Coverage % is the interim acceptance metric.
* Telemetry: each parse logs an `llm_usage` row (`call_site=parser_complete`).
