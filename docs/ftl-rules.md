# FTL rules — KCARs 2025 Part 8 baseline

> **Status:** Phase 0 placeholder. Phase 1 will populate this document with
> the full distilled rule set, with each rule mapped to a pure function in
> `app/services/ftl_engine.py` and ≥1 pytest test in `backend/tests/ftl/`.

This document is the single source of truth for the FTL rule set that the
Ratiba optimiser and validator enforce. It is intentionally written so that
a non-engineer regulator can read it end-to-end and trace every assertion
back to a KCARs 2025 Part 8 article.

## Rule identifier convention

`KCAR-P8-<DOMAIN>-<METRIC>-<LIMIT>`

Examples:

- `KCAR-P8-FDP-MAX-13H` — maximum flight duty period of 13 hours (basic crew)
- `KCAR-P8-REST-MIN-12H` — minimum 12-hour rest before next FDP
- `KCAR-P8-CUMUL-DUTY-7D-60H` — cumulative duty in any 7 days ≤ 60 h

## Baseline rule families (Phase 1 build set)

The minimum rule set to encode in Phase 1, per Plan §5 Phase 1:

1. **Max FDP by start time + sectors flown.** Table-driven, basic vs
   augmented crew. Reduction for early starts and high sector counts.
2. **Mandatory rest before next FDP.** Minimum rest hours, augmented vs
   basic, after long-range vs short-range duty.
3. **Cumulative duty hours.** Rolling 7-day, 28-day, and 365-day caps.
4. **Cumulative block hours.** Rolling 28-day and 365-day caps.
5. **Standby duty rules.** Short-call vs long-call; how standby counts
   toward FDP if called out.
6. **Split duty allowances.** When a break extends FDP; rest equivalence.
7. **Time-zone crossing recovery.** Extra rest after crossing ≥ N time
   zones; consecutive long-haul caps.
8. **Discretion / commander's discretion logging.** Use of discretion,
   reporting obligation, repeated-use audit triggers.

## Baseline decision

**Decided 2026-05-27** (Capt. Dan / Claude Code, Plan §11 Q3):
Phase 1 builds the **generic KCARs 2025 Part 8** baseline. Operator-specific
OM-A deltas will be layered in Phase 6 once the first operator is confirmed
and their OM-A FTL chapter is in hand.
