# FTL rules — KCAA Flight Duty Time Scheme baseline

Single source of truth for the rule set enforced by `app.services.ftl_engine`.
Each rule below maps 1:1 to a pure function in that module, and to ≥1 test in
`backend/tests/ftl/`.

## Regulatory framework

- **ICAO Annex 6, Part I, §4.10** sets the *framework*: each State must
  establish fatigue-management regulations with defined limits for flight
  time, flight duty periods (FDP), duty periods and rest, and may permit an
  approved **Fatigue Risk Management System (FRMS)** (ICAO Doc 9966). ICAO
  does **not** prescribe universal numbers.
- **Kenya — how the numbers are set:** KCAA Advisory Circular
  **CAA-AC-OPS033 "Crew Flight and Duty Time Scheme" (June 2018)** is
  *guidance*. By regulation each **operator** must build its **own Flight &
  Duty Time scheme, approved by the Authority** and held in the OM-A; that
  approved scheme — not the AC — carries the binding numeric table. A scheme
  "may be more restrictive but not less restrictive" than the regulatory
  factors. Ratiba therefore ships a conservative **default baseline** that an
  operator overrides with its approved scheme via the OM-A parser
  (`app.services.constraint_parser` → `ftl_rules`).
- **Kenya — FRMS:** prescriptive FTLs are always required; FRMS is the
  performance-based enhancement (ICAO Doc 9966; ICAO/IATA/IFALPA *Fatigue
  Management Guide*). The engine's `REQUIRES_FRMS_DEROGATION` state marks
  duties acceptable only under an approved FRMS / fatigue safety case.

### Explicit figures stated in CAA-AC-OPS033 (baseline honours these)

| AC reference | Provision | Engine |
|---|---|---|
| §4.6.3 | Max FDP **14 consecutive hours in 24** | `fdp_scheduled_ceiling_basic_h = 14`, capped in `rule_max_fdp_basic` (band table is more restrictive at ≤13 h) |
| §4.6.1 | Min rest **typically 10 h**, protecting **8 h sleep opportunity** | `rest_away_floor_h = 10`, `min_sleep_opportunity_h = 8` (home floor 12 h is more restrictive) |
| §4.6.1 | Rest after an extended FDP **≥ preceding duty period** | `rule_min_rest`: `floor = max(floor, preceding_duty)` |
| §3.4 / §4.6.7 | Commander's discretion: report each use; **>2 h over limits → report to the Authority**; required rest increased by the overrun | `discretion_max_extension_h = 2`; >2 h flagged not-plannable |
| §4.6.8 | Reserve: **8 h protected sleep opportunity** in 24 h before the called flight | `rule_reserve_sleep_opportunity` → `KCAR-P8-RESERVE-SLEEP` (`min_sleep_opportunity_h`) |
| §4.6.2 | Weekly recovery emphasised (two nights restores alertness) | `rule_weekly_rest` → `KCAR-P8-WEEKLY-REST` (`weekly_rest_floor_h`, operator-overridable) |

> **Status:** working baseline aligned to CAP 371 / EASA conventions and to
> the explicit CAA-AC-OPS033 figures above. The **FDP table, cumulative
> caps, standby, split-duty and time-zone numbers are not fixed by the AC** —
> they come from each operator's approved scheme and must be loaded per
> operator before operational reliance. Rule IDs `KCAR-P8-*` are stable
> internal identifiers, **not** regulatory section numbers.

## Baseline decision

**Decided 2026-05-27** (Capt. Dan / Claude Code, Plan §11 Q3):
build the generic Kenyan baseline now; operator-specific OM-A / FTDS deltas
layer in via the `ftl_rules` table once an operator's approved scheme is in
hand.

## How to read this document

| Field            | Meaning                                                  |
|------------------|----------------------------------------------------------|
| **Rule ID**      | `KCAR-P8-<DOMAIN>-<METRIC>-<LIMIT>` — stable identifier  |
| **Function**     | Python function in `ftl_engine.py` that implements it    |
| **Citation**     | KCARs article — placeholder until Dan confirms           |
| **Inputs**       | Fields read from `FdpInput` and `FdpHistory`             |
| **Output**       | `LegalityState` returned (with rule-specific reasoning)  |

A verdict carries:

- `legality_state` — `LEGAL` / `AT_LIMIT` / `REQUIRES_FRMS_DEROGATION` / `ILLEGAL`
- `rule_id` — e.g. `KCAR-P8-FDP-MAX-BASIC`
- `reason` — human-readable summary safe to show to the user
- `regulation_ref` — citation
- `rules_applied` — every rule_id evaluated
- `metadata` — numeric details (`limit_hours`, `actual_hours`, `margin_hours`)

## Rule families

### 1. Maximum flight duty period (basic crew)

**Rule ID:** `KCAR-P8-FDP-MAX-BASIC`
**Function:** `rule_max_fdp_basic`
**Citation:** KCARs 2025 Part 8 §8.X.Y *(to confirm)*

Maximum FDP for a 2-pilot basic crew complement, by report time (local at
base) and number of sectors. The table below is encoded in `LIMITS`:

| Report time (local) | 1–2 sectors | Per extra sector | Floor |
|---------------------|------------:|-----------------:|------:|
| 06:00–13:29         | **13:00 h** | −0:30 h          |  9:00 |
| 05:00–05:59         | **12:00 h** | −0:30 h          |  9:00 |
| 13:30–16:59         | **12:00 h** | −0:30 h          |  9:00 |
| 17:00–04:59 (WOCL)  | **11:00 h** | −0:30 h          |  9:00 |

States:

- **LEGAL** — actual duty ≤ limit − 30 min
- **AT_LIMIT** — actual duty within 30 min of the limit
- **REQUIRES_FRMS_DEROGATION** — exceeds limit, but ≤ limit + 2 h (discretion / FRMS)
- **ILLEGAL** — exceeds limit + 2 h

### 2. Maximum flight duty period (augmented crew)

**Rule ID:** `KCAR-P8-FDP-MAX-AUG`
**Function:** `rule_max_fdp_augmented`
**Citation:** KCARs 2025 Part 8 §8.X.Y *(to confirm)*

For 3- or 4-pilot crew with an in-flight rest facility, the basic limit is
extended:

| Crew complement | Rest facility class | Extension over basic |
|-----------------|---------------------|---------------------:|
| 3 pilots        | Class 3 (recliner)  | +1:00 h              |
| 3 pilots        | Class 2             | +2:00 h              |
| 3 pilots        | Class 1 (bunk)      | +3:00 h              |
| 4 pilots        | Class 1             | +4:00 h (cap 18:00)  |

Without a qualifying rest facility, the basic rule applies.

### 3. Minimum rest before next FDP

**Rule ID:** `KCAR-P8-REST-MIN`
**Function:** `rule_min_rest`
**Citation:** KCARs 2025 Part 8 §8.X.Y *(to confirm)*

Rest before the next FDP must be at least:

- **At home base:** `max(12:00, length of preceding duty)`
- **Away from base:** `max(10:00, length of preceding duty)`

`AT_LIMIT` when within 30 min of minimum, `REQUIRES_FRMS_DEROGATION` if
below minimum but within 1 h of it, `ILLEGAL` otherwise.

### 4. Cumulative duty hours — 7 / 28 / 365 days

**Rule IDs:**

- `KCAR-P8-CUMUL-DUTY-7D`
- `KCAR-P8-CUMUL-DUTY-28D`
- `KCAR-P8-CUMUL-DUTY-365D`

**Functions:** `rule_cumulative_duty_7d`, `..._28d`, `..._365d`
**Citation:** KCARs 2025 Part 8 §8.X.Y *(to confirm)*

| Window      | Max duty hours |
|-------------|---------------:|
| 7 days      |     60:00 h    |
| 28 days     |    190:00 h    |
| 365 days    |  2 000:00 h    |

### 5. Cumulative block (flight) hours — 28 / 365 days

**Rule IDs:**

- `KCAR-P8-CUMUL-BLOCK-28D`
- `KCAR-P8-CUMUL-BLOCK-365D`

**Functions:** `rule_cumulative_block_28d`, `..._365d`
**Citation:** KCARs 2025 Part 8 §8.X.Y *(to confirm)*

| Window      | Max block hours |
|-------------|----------------:|
| 28 days     |     100:00 h    |
| 365 days    |   1 000:00 h    |

### 6. Standby duty

**Rule IDs:**

- `KCAR-P8-STANDBY-SHORT-CALL`
- `KCAR-P8-STANDBY-LONG-CALL`

**Functions:** `rule_standby_short_call`, `rule_standby_long_call`
**Citation:** KCARs 2025 Part 8 §8.X.Y *(to confirm)*

| Standby type   | Max duration | FDP impact when called out                              |
|----------------|-------------:|---------------------------------------------------------|
| Short-call     |       12:00  | Standby time counts toward FDP from time on standby     |
| Long-call      |       24:00  | Only the called-out FDP counts; rest before call required |

### 7. Split duty

**Rule ID:** `KCAR-P8-SPLIT-DUTY`
**Function:** `rule_split_duty`
**Citation:** KCARs 2025 Part 8 §8.X.Y *(to confirm)*

A qualifying ground break of ≥3 h between duty periods, with suitable
facilities, may extend the maximum FDP by up to 50 % of the break length,
to a cap of +2:00 h. Below the qualifying break threshold, no extension.

### 8. Time-zone crossing recovery

**Rule ID:** `KCAR-P8-TZ-RECOVERY`
**Function:** `rule_timezone_recovery`
**Citation:** KCARs 2025 Part 8 §8.X.Y *(to confirm)*

After an FDP that crossed ≥4 time zones:

- ≥4 zones: 36 h rest before next FDP at home base.
- ≥6 zones: 48 h.
- ≥8 zones: 72 h.

### 9. Commander's discretion

**Rule ID:** `KCAR-P8-DISCRETION`
**Function:** `rule_discretion`
**Citation:** KCARs 2025 Part 8 §8.X.Y *(to confirm)*

Commander's discretion may extend the maximum FDP by up to **2:00 h** or
reduce rest by up to **1:00 h**. Each use must be logged with reason.
Repeated use (>3 in any 90-day window) raises `AT_LIMIT` even when the
extension itself is permitted, surfaces in the audit pack, and triggers
Crewing Officer review.

### 10. Reserve sleep opportunity

**Rule ID:** `KCAR-P8-RESERVE-SLEEP`
**Function:** `rule_reserve_sleep_opportunity`
**Citation:** CAA-AC-OPS033 §4.6.8

A reserve (short- or long-call standby) crew member must have an **8 h
protected sleep opportunity** in the 24 h before the flight they are called
for (`min_sleep_opportunity_h`). Applicable only while on standby; a duty
that doesn't carry a sleep-opportunity figure is treated as compliant.

### 11. Weekly recovery rest

**Rule ID:** `KCAR-P8-WEEKLY-REST`
**Function:** `rule_weekly_rest`
**Citation:** CAA-AC-OPS033 §4.6.2

The preceding rolling **7-day** window must contain at least one rest period
of `weekly_rest_floor_h` (baseline **36 h** — an operator-scheme value). The
engine takes the longest continuous rest in the window (counting the implicit
rest at the window start) and grades it against the floor. Conservative: it
needs ≥2 duties in the window to evaluate, so a sparse roster is never
spuriously flagged. The optimiser validates each draft FDP without history, so
this rule only engages on published/validated rosters and in the audit pack.

## Aggregation

`check_fdp(input)` runs every applicable rule and returns the full list
of `FtlVerdict`s. `aggregate_verdicts(verdicts)` reduces them to a
single FDP-level verdict using **worst-state-wins**:

`ILLEGAL` ≻ `REQUIRES_FRMS_DEROGATION` ≻ `AT_LIMIT` ≻ `LEGAL`.

## Operator overrides (Phase 6+)

The `ftl_rules` table stores per-operator rule overrides keyed by
`rule_id`. At evaluation time the engine prefers the operator's override
(when `source = OM_A_REVISION_X`) over the generic baseline. Phase 7's
LLM parser writes overrides with `source = LLM_PARSED` for human review
before they're promoted to active.

## Open items pending Dan's review

1. Confirm article numbers (`§8.X.Y` placeholders) against the KCARs 2025
   Part 8 published text.
2. Confirm numeric limits in `LIMITS` against the published text — in
   particular: 7/28/365-day cumulative caps, augmented crew extensions,
   and standby durations, which vary most across regulators.
3. Confirm window-of-circadian-low (WOCL) bounds — current encoding is
   17:00–04:59 local; KCARs may use 02:00–06:00 (ICAO).
4. Confirm time-zone recovery thresholds (≥4/6/8) — these are the most
   variable between EASA, FAA, ICAO and likely KCARs.
