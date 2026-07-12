// Flight & duty time (FTL) engine for the KCAA Flight Duty Time Scheme.
//
// Faithful TypeScript port of backend/app/services/ftl_engine.py (single
// source of truth for rule semantics — keep the two in lockstep, and see
// docs/ftl-rules.md for the human-readable rules). Kenya's prescriptive
// limits are set out in CAA-AC-OPS033 (CAP 371-derived) under the Civil
// Aviation (Operation of Aircraft) Regulations 2025, implementing ICAO
// Annex 6 Part I, 4.10. REQUIRES_FRMS_DEROGATION marks duties acceptable
// only under an approved FRMS (ICAO Doc 9966).
//
// Framework-free by design: every rule is a pure function over plain data,
// so it runs identically under Deno (edge function) and Node (parity tests).

export type LegalityState = "LEGAL" | "AT_LIMIT" | "REQUIRES_FRMS_DEROGATION" | "ILLEGAL";
export type FdpType = "FDP" | "STANDBY" | "OFF" | "LEAVE" | "TRAINING";
export type StandbyType = "NONE" | "SHORT_CALL" | "LONG_CALL";

// deno-lint-ignore no-explicit-any
export type Limits = Record<string, any>;

// CAP 371 / EASA Part-ORO-aligned baseline for CAA-AC-OPS033. Pending
// confirmation against the authoritative scheme tables — edit together with
// docs/ftl-rules.md and the Python engine.
export const LIMITS: Limits = {
  fdp_max_basic_by_band: { WOCL: 11.0, EARLY: 12.0, DAY_PEAK: 13.0, AFTERNOON: 12.0 },
  fdp_scheduled_ceiling_basic_h: 14.0,
  fdp_sector_reduction_per_extra: 0.5,
  fdp_sector_floor: 9.0,
  fdp_aug_3_pilot: { 1: 3.0, 2: 2.0, 3: 1.0 },
  fdp_aug_4_pilot: { 1: 4.0, 2: 3.0, 3: 2.0 },
  fdp_aug_absolute_cap: 18.0,
  rest_home_floor_h: 12.0,
  rest_away_floor_h: 10.0,
  min_sleep_opportunity_h: 8.0,
  rest_at_limit_window_h: 0.5,
  rest_derogation_window_h: 1.0,
  weekly_rest_floor_h: 36.0,
  weekly_rest_window_days: 7,
  cumul_duty_7d_h: 60.0,
  cumul_duty_28d_h: 190.0,
  cumul_duty_365d_h: 2000.0,
  cumul_block_28d_h: 100.0,
  cumul_block_365d_h: 1000.0,
  standby_short_call_max_h: 12.0,
  standby_long_call_max_h: 24.0,
  split_duty_qualifying_break_h: 3.0,
  split_duty_extension_factor: 0.5,
  split_duty_extension_cap_h: 2.0,
  tz_recovery: { 4: 36.0, 6: 48.0, 8: 72.0 },
  discretion_max_extension_h: 2.0,
  discretion_max_rest_reduction_h: 1.0,
  discretion_repeated_use_90d_threshold: 3,
  at_limit_margin_h: 0.5,
};

export const REGULATION_REF =
  "KCAA Flight Duty Time Scheme (CAA-AC-OPS033); ICAO Annex 6 Part I, 4.10";

const STATE_ORDER: LegalityState[] = ["LEGAL", "AT_LIMIT", "REQUIRES_FRMS_DEROGATION", "ILLEGAL"];

export interface CrewClassification {
  augmented?: boolean;
  pilots_on_flight_deck?: number; // 2 = basic, 3 or 4 = augmented
  rest_facility_class?: number; // 0=none, 1=full bunk, 2=lie-flat, 3=recliner
}

export interface FdpHistoryEntry {
  date_local: string; // ISO date of report (local at base)
  report_time: Date;
  off_duty_time: Date;
  duty_hours: number;
  flight_hours: number;
  sectors_count: number;
  fdp_type: FdpType;
  at_home_base: boolean;
  timezones_crossed?: number;
}

export interface FdpInput {
  report_time: Date;
  off_duty_time: Date;
  sectors_count: number;
  flight_hours: number;
  duty_hours: number;
  base_tz?: string; // IANA tz of operating base (default Africa/Nairobi)
  fdp_type?: FdpType;
  crew_classification?: CrewClassification;
  discretion_extension_h?: number;
  split_duty_break_h?: number;
  timezones_crossed?: number;
  at_home_base?: boolean;
  prior_fdp?: FdpHistoryEntry | null;
  history?: FdpHistoryEntry[];
  discretion_uses_last_90d?: number;
  standby_hours_before_call?: number;
  standby_type?: StandbyType;
  // Protected sleep opportunity (h) in the 24 h before a reserve call-out
  // (§4.6.8). Defaults clearly compliant so unset input is never flagged.
  reserve_sleep_opportunity_h?: number;
}

export interface FtlVerdict {
  legality_state: LegalityState;
  rule_id: string;
  reason: string;
  regulation_ref: string;
  rules_applied: string[];
  // deno-lint-ignore no-explicit-any
  metadata: Record<string, any>;
}

// ── helpers ──────────────────────────────────────────────────────────────────

function hoursBetween(start: Date, end: Date): number {
  return Math.max(0, (end.getTime() - start.getTime()) / 3_600_000);
}

function stateForOvershoot(
  actualH: number,
  limitH: number,
  atLimitMarginH: number,
  derogationMarginH: number,
): LegalityState {
  if (actualH < limitH - atLimitMarginH) return "LEGAL";
  if (actualH <= limitH) return "AT_LIMIT";
  if (actualH <= limitH + derogationMarginH) return "REQUIRES_FRMS_DEROGATION";
  return "ILLEGAL";
}

function stateForUndershoot(
  actualH: number,
  floorH: number,
  atLimitMarginH: number,
  derogationMarginH: number,
): LegalityState {
  if (actualH > floorH + atLimitMarginH) return "LEGAL";
  if (actualH >= floorH) return "AT_LIMIT";
  if (actualH >= floorH - derogationMarginH) return "REQUIRES_FRMS_DEROGATION";
  return "ILLEGAL";
}

/** Minutes past local midnight for `utc` in IANA zone `tz`. */
function localMinutes(utc: Date, tz: string): number {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: tz,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(utc);
  const h = Number(parts.find((p) => p.type === "hour")?.value ?? "0") % 24;
  const m = Number(parts.find((p) => p.type === "minute")?.value ?? "0");
  return h * 60 + m;
}

/** Map local report time to a band key in LIMITS.fdp_max_basic_by_band. */
export function reportBand(reportUtc: Date, baseTz: string): string {
  const mins = localMinutes(reportUtc, baseTz);
  if (mins >= 17 * 60 || mins < 5 * 60) return "WOCL";
  if (mins < 6 * 60) return "EARLY";
  if (mins < 13 * 60 + 30) return "DAY_PEAK";
  return "AFTERNOON";
}

function fmt(n: number, digits: number): string {
  return n.toFixed(digits);
}

type Rule = (fdp: FdpInput, L: Limits) => FtlVerdict;

// ── rules ────────────────────────────────────────────────────────────────────

export const ruleMaxFdpBasic: Rule = (fdp, L) => {
  const rule_id = "KCAR-P8-FDP-MAX-BASIC";
  const band = reportBand(fdp.report_time, fdp.base_tz ?? "Africa/Nairobi");
  const baseLimit = Number(L.fdp_max_basic_by_band[band]);

  const extraSectors = Math.max(0, fdp.sectors_count - 2);
  const reduction = extraSectors * Number(L.fdp_sector_reduction_per_extra);
  let limit = Math.max(baseLimit - reduction, Number(L.fdp_sector_floor));
  // §4.6.3: basic-crew FDP may not be scheduled beyond the 14 h / 24 h
  // ceiling, whatever the band table says.
  limit = Math.min(limit, Number(L.fdp_scheduled_ceiling_basic_h ?? 14.0));

  const actual = fdp.duty_hours;
  const state = stateForOvershoot(
    actual,
    limit,
    Number(L.at_limit_margin_h),
    Number(L.discretion_max_extension_h),
  );

  return {
    legality_state: state,
    rule_id,
    reason:
      `basic-crew FDP limit for ${band} report and ${fdp.sectors_count} sectors ` +
      `is ${fmt(limit, 1)}h; actual duty is ${fmt(actual, 2)}h`,
    regulation_ref: REGULATION_REF,
    rules_applied: [rule_id],
    metadata: {
      limit_h: limit,
      actual_h: actual,
      margin_h: limit - actual,
      band,
      sectors_count: fdp.sectors_count,
      base_limit_h: baseLimit,
      sector_reduction_h: reduction,
    },
  };
};

export const ruleMaxFdpAugmented: Rule = (fdp, L) => {
  const rule_id = "KCAR-P8-FDP-MAX-AUG";
  const cc = fdp.crew_classification ?? {};
  const pilots = cc.pilots_on_flight_deck ?? 2;
  const restClass = cc.rest_facility_class ?? 0;

  const basicLimit = Number(ruleMaxFdpBasic(fdp, L).metadata.limit_h);

  if (!cc.augmented || pilots < 3 || restClass === 0) {
    return {
      legality_state: "LEGAL",
      rule_id,
      reason: "not augmented or no qualifying rest facility — basic limit applies",
      regulation_ref: REGULATION_REF,
      rules_applied: [rule_id],
      metadata: { applicable: false, basic_limit_h: basicLimit },
    };
  }

  const table = pilots === 3 ? L.fdp_aug_3_pilot : L.fdp_aug_4_pilot;
  const extension = Number(table[restClass] ?? 0.0);
  const limit = Math.min(basicLimit + extension, Number(L.fdp_aug_absolute_cap));
  const actual = fdp.duty_hours;
  const state = stateForOvershoot(
    actual,
    limit,
    Number(L.at_limit_margin_h),
    Number(L.discretion_max_extension_h),
  );

  return {
    legality_state: state,
    rule_id,
    reason:
      `augmented ${pilots}-pilot crew with class-${restClass} rest: ` +
      `extended limit ${fmt(limit, 1)}h; actual ${fmt(actual, 2)}h`,
    regulation_ref: REGULATION_REF,
    rules_applied: [rule_id],
    metadata: {
      applicable: true,
      limit_h: limit,
      actual_h: actual,
      margin_h: limit - actual,
      basic_limit_h: basicLimit,
      extension_h: extension,
      pilots_on_flight_deck: pilots,
      rest_facility_class: restClass,
    },
  };
};

export const ruleMinRest: Rule = (fdp, L) => {
  const rule_id = "KCAR-P8-REST-MIN";
  const prior = fdp.prior_fdp;
  if (!prior) {
    return {
      legality_state: "LEGAL",
      rule_id,
      reason: "no prior FDP recorded — rest rule not applicable",
      regulation_ref: REGULATION_REF,
      rules_applied: [rule_id],
      metadata: { applicable: false },
    };
  }

  const restH = hoursBetween(prior.off_duty_time, fdp.report_time);
  const precedingDutyH = prior.duty_hours;
  const atHome = fdp.at_home_base ?? true;
  const floorBase = Number(atHome ? L.rest_home_floor_h : L.rest_away_floor_h);
  const floor = Math.max(floorBase, precedingDutyH);

  const state = stateForUndershoot(
    restH,
    floor,
    Number(L.rest_at_limit_window_h),
    Number(L.rest_derogation_window_h),
  );

  const location = atHome ? "home base" : "away from base";
  return {
    legality_state: state,
    rule_id,
    reason:
      `rest at ${location}: ${fmt(restH, 2)}h actual against floor ${fmt(floor, 2)}h ` +
      `(prior duty ${fmt(precedingDutyH, 2)}h)`,
    regulation_ref: REGULATION_REF,
    rules_applied: [rule_id],
    metadata: {
      actual_rest_h: restH,
      floor_h: floor,
      preceding_duty_h: precedingDutyH,
      at_home_base: atHome,
    },
  };
};

function cumulativeInWindow(
  fdp: FdpInput,
  windowDays: number,
  pick: (h: { duty_hours: number; flight_hours: number }) => number,
): number {
  const start = fdp.report_time.getTime() - windowDays * 86_400_000;
  let total = pick(fdp);
  for (const h of fdp.history ?? []) {
    const t = h.report_time.getTime();
    if (start <= t && t < fdp.report_time.getTime()) total += pick(h);
  }
  return total;
}

function cumulativeVerdict(
  actualH: number,
  limitH: number,
  ruleId: string,
  windowLabel: string,
  L: Limits,
): FtlVerdict {
  const state = stateForOvershoot(
    actualH,
    limitH,
    Number(L.at_limit_margin_h),
    Number(L.discretion_max_extension_h),
  );
  return {
    legality_state: state,
    rule_id: ruleId,
    reason: `cumulative ${windowLabel}: ${fmt(actualH, 2)}h actual against limit ${fmt(limitH, 1)}h`,
    regulation_ref: REGULATION_REF,
    rules_applied: [ruleId],
    metadata: {
      actual_h: actualH,
      limit_h: limitH,
      margin_h: limitH - actualH,
      window_label: windowLabel,
    },
  };
}

export const ruleCumulativeDuty7d: Rule = (fdp, L) =>
  cumulativeVerdict(
    cumulativeInWindow(fdp, 7, (h) => h.duty_hours),
    Number(L.cumul_duty_7d_h),
    "KCAR-P8-CUMUL-DUTY-7D",
    "duty hours in trailing 7 days",
    L,
  );

export const ruleCumulativeDuty28d: Rule = (fdp, L) =>
  cumulativeVerdict(
    cumulativeInWindow(fdp, 28, (h) => h.duty_hours),
    Number(L.cumul_duty_28d_h),
    "KCAR-P8-CUMUL-DUTY-28D",
    "duty hours in trailing 28 days",
    L,
  );

export const ruleCumulativeDuty365d: Rule = (fdp, L) =>
  cumulativeVerdict(
    cumulativeInWindow(fdp, 365, (h) => h.duty_hours),
    Number(L.cumul_duty_365d_h),
    "KCAR-P8-CUMUL-DUTY-365D",
    "duty hours in trailing 365 days",
    L,
  );

export const ruleCumulativeBlock28d: Rule = (fdp, L) =>
  cumulativeVerdict(
    cumulativeInWindow(fdp, 28, (h) => h.flight_hours),
    Number(L.cumul_block_28d_h),
    "KCAR-P8-CUMUL-BLOCK-28D",
    "block hours in trailing 28 days",
    L,
  );

export const ruleCumulativeBlock365d: Rule = (fdp, L) =>
  cumulativeVerdict(
    cumulativeInWindow(fdp, 365, (h) => h.flight_hours),
    Number(L.cumul_block_365d_h),
    "KCAR-P8-CUMUL-BLOCK-365D",
    "block hours in trailing 365 days",
    L,
  );

export const ruleStandbyShortCall: Rule = (fdp, L) => {
  const rule_id = "KCAR-P8-STANDBY-SHORT-CALL";
  if ((fdp.standby_type ?? "NONE") !== "SHORT_CALL") {
    return {
      legality_state: "LEGAL",
      rule_id,
      reason: "not on short-call standby",
      regulation_ref: REGULATION_REF,
      rules_applied: [rule_id],
      metadata: { applicable: false },
    };
  }

  const standbyH = fdp.standby_hours_before_call ?? 0;
  const standbyLimit = Number(L.standby_short_call_max_h);
  if (standbyH > standbyLimit) {
    return {
      legality_state: "ILLEGAL",
      rule_id,
      reason:
        `short-call standby duration ${fmt(standbyH, 2)}h exceeds maximum ${fmt(standbyLimit, 1)}h`,
      regulation_ref: REGULATION_REF,
      rules_applied: [rule_id],
      metadata: { standby_h: standbyH, standby_limit_h: standbyLimit },
    };
  }

  // When called out, standby + duty must respect the basic FDP limit.
  const basicLimit = Number(ruleMaxFdpBasic(fdp, L).metadata.limit_h);
  const combined = standbyH + fdp.duty_hours;
  const state = stateForOvershoot(
    combined,
    basicLimit,
    Number(L.at_limit_margin_h),
    Number(L.discretion_max_extension_h),
  );
  return {
    legality_state: state,
    rule_id,
    reason:
      `short-call standby ${fmt(standbyH, 2)}h + duty ${fmt(fdp.duty_hours, 2)}h ` +
      `= ${fmt(combined, 2)}h against FDP limit ${fmt(basicLimit, 1)}h`,
    regulation_ref: REGULATION_REF,
    rules_applied: [rule_id],
    metadata: {
      standby_h: standbyH,
      duty_h: fdp.duty_hours,
      combined_h: combined,
      fdp_limit_h: basicLimit,
    },
  };
};

export const ruleStandbyLongCall: Rule = (fdp, L) => {
  const rule_id = "KCAR-P8-STANDBY-LONG-CALL";
  if ((fdp.standby_type ?? "NONE") !== "LONG_CALL") {
    return {
      legality_state: "LEGAL",
      rule_id,
      reason: "not on long-call standby",
      regulation_ref: REGULATION_REF,
      rules_applied: [rule_id],
      metadata: { applicable: false },
    };
  }

  const standbyH = fdp.standby_hours_before_call ?? 0;
  const standbyLimit = Number(L.standby_long_call_max_h);
  const state = stateForOvershoot(
    standbyH,
    standbyLimit,
    Number(L.at_limit_margin_h),
    Number(L.discretion_max_extension_h),
  );
  return {
    legality_state: state,
    rule_id,
    reason: `long-call standby ${fmt(standbyH, 2)}h against maximum ${fmt(standbyLimit, 1)}h`,
    regulation_ref: REGULATION_REF,
    rules_applied: [rule_id],
    metadata: { standby_h: standbyH, standby_limit_h: standbyLimit },
  };
};

export const ruleSplitDuty: Rule = (fdp, L) => {
  const rule_id = "KCAR-P8-SPLIT-DUTY";
  const breakH = fdp.split_duty_break_h ?? 0;
  const threshold = Number(L.split_duty_qualifying_break_h);

  if (breakH < threshold) {
    return {
      legality_state: "LEGAL",
      rule_id,
      reason:
        `break ${fmt(breakH, 2)}h below qualifying threshold ${fmt(threshold, 1)}h — no extension`,
      regulation_ref: REGULATION_REF,
      rules_applied: [rule_id],
      metadata: { applicable: false, break_h: breakH },
    };
  }

  const extension = Math.min(
    breakH * Number(L.split_duty_extension_factor),
    Number(L.split_duty_extension_cap_h),
  );
  const basicLimit = Number(ruleMaxFdpBasic(fdp, L).metadata.limit_h);
  const effectiveLimit = basicLimit + extension;
  const actual = fdp.duty_hours;
  const state = stateForOvershoot(
    actual,
    effectiveLimit,
    Number(L.at_limit_margin_h),
    Number(L.discretion_max_extension_h),
  );

  return {
    legality_state: state,
    rule_id,
    reason:
      `qualifying break ${fmt(breakH, 2)}h extends FDP by ${fmt(extension, 2)}h ` +
      `to ${fmt(effectiveLimit, 2)}h; actual ${fmt(actual, 2)}h`,
    regulation_ref: REGULATION_REF,
    rules_applied: [rule_id],
    metadata: {
      applicable: true,
      break_h: breakH,
      extension_h: extension,
      basic_limit_h: basicLimit,
      effective_limit_h: effectiveLimit,
      actual_h: actual,
    },
  };
};

export const ruleTimezoneRecovery: Rule = (fdp, L) => {
  const rule_id = "KCAR-P8-TZ-RECOVERY";
  const prior = fdp.prior_fdp;
  if (!prior || (prior.timezones_crossed ?? 0) < 4) {
    return {
      legality_state: "LEGAL",
      rule_id,
      reason: "no qualifying time-zone-crossing prior FDP",
      regulation_ref: REGULATION_REF,
      rules_applied: [rule_id],
      metadata: { applicable: false },
    };
  }

  const zones = prior.timezones_crossed ?? 0;
  let floor = Number(L.tz_recovery[4]);
  if (zones >= 8) floor = Number(L.tz_recovery[8]);
  else if (zones >= 6) floor = Number(L.tz_recovery[6]);

  const restH = hoursBetween(prior.off_duty_time, fdp.report_time);
  const state = stateForUndershoot(
    restH,
    floor,
    Number(L.rest_at_limit_window_h),
    Number(L.rest_derogation_window_h),
  );
  return {
    legality_state: state,
    rule_id,
    reason:
      `prior FDP crossed ${zones} time zones; recovery rest ` +
      `${fmt(restH, 2)}h against floor ${fmt(floor, 1)}h`,
    regulation_ref: REGULATION_REF,
    rules_applied: [rule_id],
    metadata: { zones_crossed: zones, actual_rest_h: restH, floor_h: floor },
  };
};

export const ruleDiscretion: Rule = (fdp, L) => {
  const rule_id = "KCAR-P8-DISCRETION";
  const extension = fdp.discretion_extension_h ?? 0;
  const cap = Number(L.discretion_max_extension_h);
  const uses = fdp.discretion_uses_last_90d ?? 0;
  const threshold = Number(L.discretion_repeated_use_90d_threshold);

  if (extension <= 0) {
    if (uses >= threshold) {
      return {
        legality_state: "AT_LIMIT",
        rule_id,
        reason:
          `commander has used discretion ${uses} times in last 90 days — review required`,
        regulation_ref: REGULATION_REF,
        rules_applied: [rule_id],
        metadata: { extension_h: 0.0, uses_last_90d: uses, repeated_use_threshold: threshold },
      };
    }
    return {
      legality_state: "LEGAL",
      rule_id,
      reason: "no commander's discretion applied",
      regulation_ref: REGULATION_REF,
      rules_applied: [rule_id],
      metadata: { extension_h: 0.0, uses_last_90d: uses },
    };
  }

  if (extension > cap) {
    return {
      legality_state: "ILLEGAL",
      rule_id,
      reason:
        `discretion extension ${fmt(extension, 2)}h exceeds ${fmt(cap, 1)}h: exceeding normal ` +
        `limits by more than 2 h must be reported to the Authority ` +
        `(CAA-AC-OPS033 §3.4) and cannot be planned`,
      regulation_ref: REGULATION_REF,
      rules_applied: [rule_id],
      metadata: { extension_h: extension, max_extension_h: cap },
    };
  }

  return {
    legality_state: "REQUIRES_FRMS_DEROGATION",
    rule_id,
    reason:
      `commander's discretion of ${fmt(extension, 2)}h applied (cap ` +
      `${fmt(cap, 1)}h); 90-day uses ${uses}`,
    regulation_ref: REGULATION_REF,
    rules_applied: [rule_id],
    metadata: { extension_h: extension, max_extension_h: cap, uses_last_90d: uses },
  };
};

export const ruleReserveSleepOpportunity: Rule = (fdp, L) => {
  const rule_id = "KCAR-P8-RESERVE-SLEEP";
  const standbyType = fdp.standby_type ?? "NONE";
  if (standbyType === "NONE") {
    return {
      legality_state: "LEGAL",
      rule_id,
      reason: "not on reserve/standby — sleep-opportunity rule not applicable",
      regulation_ref: REGULATION_REF,
      rules_applied: [rule_id],
      metadata: { applicable: false },
    };
  }

  const floor = Number(L.min_sleep_opportunity_h);
  const actual = fdp.reserve_sleep_opportunity_h ?? 10;
  const state = stateForUndershoot(
    actual,
    floor,
    Number(L.rest_at_limit_window_h),
    Number(L.rest_derogation_window_h),
  );
  return {
    legality_state: state,
    rule_id,
    reason:
      `reserve (${standbyType.toLowerCase().replace(/_/g, "-")}) sleep opportunity ` +
      `${fmt(actual, 2)}h against protected floor ${fmt(floor, 1)}h`,
    regulation_ref: REGULATION_REF,
    rules_applied: [rule_id],
    metadata: {
      applicable: true,
      standby_type: standbyType,
      sleep_opportunity_h: actual,
      floor_h: floor,
    },
  };
};

export const ruleWeeklyRest: Rule = (fdp, L) => {
  const rule_id = "KCAR-P8-WEEKLY-REST";
  const floor = Number(L.weekly_rest_floor_h);
  const windowDays = Number(L.weekly_rest_window_days);
  const windowStart = new Date(fdp.report_time.getTime() - windowDays * 86_400_000);

  const duties: [Date, Date][] = [
    ...(fdp.history ?? []).map((h) => [h.report_time, h.off_duty_time] as [Date, Date]),
    [fdp.report_time, fdp.off_duty_time],
  ].sort((a, b) => a[0].getTime() - b[0].getTime() || a[1].getTime() - b[1].getTime());
  const inWindow = duties.filter((d) => d[1].getTime() >= windowStart.getTime());
  if (inWindow.length < 2) {
    return {
      legality_state: "LEGAL",
      rule_id,
      reason: "insufficient duty history in the 7-day window — rule not applicable",
      regulation_ref: REGULATION_REF,
      rules_applied: [rule_id],
      metadata: { applicable: false },
    };
  }

  // Longest continuous rest in the window: the implicit gap from the window
  // start to the first duty, plus every gap between consecutive duties.
  const gaps = [hoursBetween(windowStart, inWindow[0][0])];
  for (let i = 1; i < inWindow.length; i++) {
    gaps.push(hoursBetween(inWindow[i - 1][1], inWindow[i][0]));
  }
  const longest = Math.max(...gaps);

  const state = stateForUndershoot(
    longest,
    floor,
    Number(L.rest_at_limit_window_h),
    Number(L.rest_derogation_window_h),
  );
  return {
    legality_state: state,
    rule_id,
    reason:
      `longest rest in the ${windowDays}-day window ${fmt(longest, 2)}h ` +
      `against weekly-recovery floor ${fmt(floor, 1)}h`,
    regulation_ref: REGULATION_REF,
    rules_applied: [rule_id],
    metadata: {
      applicable: true,
      longest_rest_h: longest,
      floor_h: floor,
      window_days: windowDays,
      duties_in_window: inWindow.length,
    },
  };
};

// ── orchestration ────────────────────────────────────────────────────────────

const ALL_RULES: Rule[] = [
  ruleMaxFdpBasic,
  ruleMaxFdpAugmented,
  ruleMinRest,
  ruleCumulativeDuty7d,
  ruleCumulativeDuty28d,
  ruleCumulativeDuty365d,
  ruleCumulativeBlock28d,
  ruleCumulativeBlock365d,
  ruleStandbyShortCall,
  ruleStandbyLongCall,
  ruleSplitDuty,
  ruleTimezoneRecovery,
  ruleDiscretion,
  ruleReserveSleepOpportunity,
  ruleWeeklyRest,
];

/** Run every rule against `fdp`. Stable order so audit packs can rely on it. */
export function checkFdp(fdp: FdpInput, limits?: Limits): FtlVerdict[] {
  const L = limits ?? LIMITS;
  return ALL_RULES.map((rule) => rule(fdp, L));
}

/** Reduce per-rule verdicts to a single FDP-level verdict (worst state wins). */
export function aggregateVerdicts(verdicts: FtlVerdict[]): FtlVerdict {
  if (!verdicts.length) throw new Error("aggregateVerdicts requires at least one verdict");
  let worst = verdicts[0];
  for (const v of verdicts) {
    if (STATE_ORDER.indexOf(v.legality_state) > STATE_ORDER.indexOf(worst.legality_state)) {
      worst = v;
    }
  }
  const allRules = verdicts.flatMap((v) => v.rules_applied);
  return {
    legality_state: worst.legality_state,
    rule_id: worst.rule_id,
    reason: worst.reason,
    regulation_ref: worst.regulation_ref,
    rules_applied: allRules,
    metadata: { per_rule: verdicts.map((v) => v.metadata) },
  };
}

export function validateFdp(fdp: FdpInput, limits?: Limits): [FtlVerdict, FtlVerdict[]] {
  const verdicts = checkFdp(fdp, limits);
  return [aggregateVerdicts(verdicts), verdicts];
}

/** Deep copy of LIMITS with dotted-key overrides applied (operator sets). */
// deno-lint-ignore no-explicit-any
export function applyOverrides(overrides: Record<string, any>, base?: Limits): Limits {
  const merged: Limits = structuredClone(base ?? LIMITS);
  for (const [dottedKey, value] of Object.entries(overrides)) {
    if (dottedKey.includes(".")) {
      const idx = dottedKey.indexOf(".");
      const parent = dottedKey.slice(0, idx);
      const child = dottedKey.slice(idx + 1);
      const group = merged[parent];
      if (group && typeof group === "object") group[child] = value;
    } else if (dottedKey in merged) {
      merged[dottedKey] = value;
    }
  }
  return merged;
}

export function allRuleIds(): string[] {
  return [
    "KCAR-P8-FDP-MAX-BASIC",
    "KCAR-P8-FDP-MAX-AUG",
    "KCAR-P8-REST-MIN",
    "KCAR-P8-CUMUL-DUTY-7D",
    "KCAR-P8-CUMUL-DUTY-28D",
    "KCAR-P8-CUMUL-DUTY-365D",
    "KCAR-P8-CUMUL-BLOCK-28D",
    "KCAR-P8-CUMUL-BLOCK-365D",
    "KCAR-P8-STANDBY-SHORT-CALL",
    "KCAR-P8-STANDBY-LONG-CALL",
    "KCAR-P8-SPLIT-DUTY",
    "KCAR-P8-TZ-RECOVERY",
    "KCAR-P8-DISCRETION",
    "KCAR-P8-RESERVE-SLEEP",
    "KCAR-P8-WEEKLY-REST",
  ];
}
