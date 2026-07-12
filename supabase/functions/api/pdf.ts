// Deterministic audit-pack PDF builder (KCAA FTL compliance pack).
//
// The pack is regenerated from the database on every download; only its
// SHA-256 is stored. Determinism matters: verify() recomputes the hash, so
// the same underlying rows must yield byte-identical PDFs. Hence fixed
// creation/modification dates (the pack's created_at) and standard fonts.

import { PDFDocument, PDFFont, StandardFonts, rgb } from "npm:pdf-lib@1.17.1";

export interface AuditFdpRow {
  date: string;
  crew_label: string;
  report_time: string | null;
  off_duty_time: string | null;
  duty_hours: number;
  sectors_count: number;
  legality_state: string;
  worst_rule: string;
}

export interface AuditPackMeta {
  id: string;
  operator_name: string;
  period_from: string;
  period_to: string;
  created_at: string;
  generator_version: string;
  rule_ids: string[];
  crew_count: number;
  fdp_count: number;
  anomaly_count: number;
}

const INK = rgb(0.11, 0.11, 0.11);
const STEEL = rgb(0.23, 0.4, 0.52);
const RED = rgb(0.75, 0.22, 0.17);

// DN Consultancy brand tokens (frontend/tailwind.config.ts is the source of
// truth — keep these two in lockstep).
const DARK = rgb(0.11, 0.11, 0.11); // #1C1C1C
const GOLD = rgb(0.788, 0.659, 0.298); // #C9A84C
const GOLD_LT = rgb(1, 0.973, 0.902); // #FFF8E6
const FOG = rgb(0.957, 0.957, 0.949); // #F4F4F2
const MUTED = rgb(0.357, 0.392, 0.447); // #5B6472
const GREEN_DEEP = rgb(0.086, 0.392, 0.216); // #166437
const GREEN_LT = rgb(0.902, 0.957, 0.914);
const AMBER_DEEP = rgb(0.478, 0.361, 0); // #7A5C00
const RED_LT = rgb(0.98, 0.91, 0.89);
const PURPLE_DEEP = rgb(0.38, 0.3, 0.56);
const PURPLE_LT = rgb(0.93, 0.91, 0.97);
const STEEL_LT = rgb(0.839, 0.894, 0.941); // #D6E4F0
const BORDER = rgb(0.85, 0.87, 0.89);

export async function buildAuditPackPdf(
  meta: AuditPackMeta,
  rows: AuditFdpRow[],
): Promise<Uint8Array> {
  const doc = await PDFDocument.create();
  const created = new Date(meta.created_at);
  doc.setTitle(`Ratiba audit pack ${meta.period_from} to ${meta.period_to}`);
  doc.setProducer(`Ratiba ${meta.generator_version}`);
  doc.setCreationDate(created);
  doc.setModificationDate(created);

  const font = await doc.embedFont(StandardFonts.Helvetica);
  const bold = await doc.embedFont(StandardFonts.HelveticaBold);
  const W = 595.28,
    H = 841.89,
    M = 50; // A4 portrait

  // ── cover / methodology page ──
  let page = doc.addPage([W, H]);
  let y = H - 80;
  const text = (s: string, size: number, f: PDFFont, color = INK, x = M) => {
    page.drawText(s, { x, y, size, font: f, color });
    y -= size + 8;
  };
  text("FTL Compliance Audit Pack", 22, bold, STEEL);
  text(meta.operator_name, 14, bold);
  y -= 6;
  text(`Period: ${meta.period_from} to ${meta.period_to}`, 11, font);
  // Normalised so the string is identical whether created_at comes from the
  // in-memory pack (…Z) or back from Postgres (…+00:00) — determinism.
  text(`Generated: ${created.toISOString()}   Pack ID: ${meta.id}`, 9, font);
  text(`Generator: Ratiba ${meta.generator_version}`, 9, font);
  y -= 10;
  text(
    `Crew covered: ${meta.crew_count}    FDPs evaluated: ${meta.fdp_count}    Anomalies: ${meta.anomaly_count}`,
    11,
    bold,
  );
  y -= 14;
  text("Methodology", 13, bold, STEEL);
  text(
    "Every flight duty period in the reporting window was evaluated against the",
    9,
    font,
  );
  text(
    "KCAA Flight Duty Time Scheme (CAA-AC-OPS033; ICAO Annex 6 Part I, 4.10)",
    9,
    font,
  );
  text("using the rule set below. Verdicts: LEGAL, AT_LIMIT,", 9, font);
  text(
    "REQUIRES_FRMS_DEROGATION (acceptable only under an approved FRMS), ILLEGAL.",
    9,
    font,
  );
  y -= 6;
  for (const r of meta.rule_ids) text(`•  ${r}`, 9, font);

  // ── FDP table pages ──
  const cols = [
    { h: "Date", x: M, w: 58 },
    { h: "Crew", x: M + 58, w: 150 },
    { h: "Report", x: M + 208, w: 52 },
    { h: "Off duty", x: M + 260, w: 52 },
    { h: "Duty h", x: M + 312, w: 40 },
    { h: "Sect", x: M + 352, w: 32 },
    { h: "Verdict", x: M + 384, w: 40 },
    { h: "Worst rule", x: M + 424, w: 120 },
  ];
  const hhmm = (iso: string | null) => (iso ? iso.slice(11, 16) + "Z" : "—");
  const short: Record<string, string> = {
    LEGAL: "OK",
    AT_LIMIT: "AT-LIM",
    REQUIRES_FRMS_DEROGATION: "FRMS",
    ILLEGAL: "ILLEGAL",
  };
  let rowY = 0;
  const newTablePage = () => {
    page = doc.addPage([W, H]);
    rowY = H - 60;
    page.drawText(`FDP register  —  ${meta.period_from} to ${meta.period_to}`, {
      x: M,
      y: rowY,
      size: 11,
      font: bold,
      color: STEEL,
    });
    rowY -= 20;
    for (const c of cols)
      page.drawText(c.h, { x: c.x, y: rowY, size: 8, font: bold, color: INK });
    rowY -= 4;
    page.drawLine({
      start: { x: M, y: rowY },
      end: { x: W - M, y: rowY },
      thickness: 0.7,
      color: STEEL,
    });
    rowY -= 12;
  };
  newTablePage();
  const clip = (s: string, w: number, size: number) => {
    while (s.length > 1 && font.widthOfTextAtSize(s, size) > w - 4)
      s = s.slice(0, -1);
    return s;
  };
  for (const r of rows) {
    if (rowY < 60) newTablePage();
    const bad = r.legality_state !== "LEGAL";
    const cells = [
      r.date,
      r.crew_label,
      hhmm(r.report_time),
      hhmm(r.off_duty_time),
      r.duty_hours.toFixed(2),
      String(r.sectors_count),
      short[r.legality_state] ?? r.legality_state,
      bad ? r.worst_rule : "",
    ];
    cells.forEach((cell, i) => {
      page.drawText(clip(cell, cols[i].w, 8), {
        x: cols[i].x,
        y: rowY,
        size: 8,
        font: bad && i >= 6 ? bold : font,
        color: bad && i >= 6 ? RED : INK,
      });
    });
    rowY -= 12;
  }
  if (!rows.length)
    page.drawText("No FDPs recorded in this period.", {
      x: M,
      y: rowY,
      size: 10,
      font,
    });

  return await doc.save({ useObjectStreams: false });
}

export async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const d = await crypto.subtle.digest("SHA-256", bytes as BufferSource);
  return [...new Uint8Array(d)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

// ── crew monthly roster PDF ─────────────────────────────────────────────────

export interface CrewRosterDay {
  date: string;
  type: string; // FDP | STANDBY | OFF | LEAVE
  legality_state: string | null;
  duty_hours: number;
  flight_hours: number;
  sectors: {
    flight_no: string;
    origin: string;
    destination: string;
    std: string;
    sta: string;
  }[];
}

export interface CrewRosterMeta {
  operator_name: string;
  operator_aoc: string | null;
  crew_name: string;
  employee_no: string;
  role: string;
  base_station: string | null;
  year: number;
  month: number; // 1-12
  generated_at: string;
}

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

type Badge = {
  label: string;
  fg: ReturnType<typeof rgb>;
  bg: ReturnType<typeof rgb>;
};
const BADGES: Record<string, Badge> = {
  LEGAL: { label: "LEGAL", fg: GREEN_DEEP, bg: GREEN_LT },
  AT_LIMIT: { label: "AT LIMIT", fg: AMBER_DEEP, bg: GOLD_LT },
  REQUIRES_FRMS_DEROGATION: { label: "FRMS", fg: PURPLE_DEEP, bg: PURPLE_LT },
  ILLEGAL: { label: "ILLEGAL", fg: RED, bg: RED_LT },
  LEAVE: { label: "LEAVE", fg: STEEL, bg: STEEL_LT },
  SBY: { label: "SBY", fg: AMBER_DEEP, bg: GOLD_LT },
};

function centered(
  text: string,
  font: PDFFont,
  size: number,
  cx: number,
): number {
  return cx - font.widthOfTextAtSize(text, size) / 2;
}

/**
 * Monthly crew roster card: a calendar grid (one cell per day, flight
 * numbers + duty/block hours + FTL verdict badge) plus summary tiles,
 * modelled on the DN Consultancy roster-card reference design.
 */
export async function buildCrewRosterPdf(
  meta: CrewRosterMeta,
  days: CrewRosterDay[],
): Promise<Uint8Array> {
  const doc = await PDFDocument.create();
  const created = new Date(meta.generated_at);
  const monthLabel = `${MONTH_NAMES[meta.month - 1]} ${meta.year}`;
  doc.setTitle(
    `${meta.crew_name} roster ${meta.year}-${String(meta.month).padStart(2, "0")}`,
  );
  doc.setProducer("Ratiba · DN Consultancy");
  doc.setCreationDate(created);
  doc.setModificationDate(created);

  const font = await doc.embedFont(StandardFonts.Helvetica);
  const bold = await doc.embedFont(StandardFonts.HelveticaBold);
  const italic = await doc.embedFont(StandardFonts.HelveticaOblique);
  const W = 595.28,
    H = 841.89,
    M = 40;
  const page = doc.addPage([W, H]);
  const byDate: Record<string, CrewRosterDay> = {};
  for (const d of days) byDate[d.date] = d;

  // ── header ──────────────────────────────────────────────────────────────
  const logoCx = M + 20,
    logoCy = H - 52;
  page.drawEllipse({
    x: logoCx,
    y: logoCy,
    xScale: 18,
    yScale: 18,
    borderColor: GOLD,
    borderWidth: 1.3,
  });
  page.drawText("DN", {
    x: centered("DN", bold, 13, logoCx),
    y: logoCy - 5,
    size: 13,
    font: bold,
    color: DARK,
  });
  page.drawText("CONSULTANCY", {
    x: centered("CONSULTANCY", font, 5, logoCx),
    y: logoCy - 30,
    size: 5,
    font,
    color: MUTED,
  });

  const rightX = W - M;
  page.drawText("PERIOD", {
    x: rightX - font.widthOfTextAtSize("PERIOD", 8) - 1,
    y: H - 42,
    size: 8,
    font: bold,
    color: STEEL,
  });
  page.drawText(monthLabel, {
    x: rightX - bold.widthOfTextAtSize(monthLabel, 22),
    y: H - 62,
    size: 22,
    font: bold,
    color: DARK,
  });
  const scheme = "KCAA FTL Scheme · ICAO Annex 6";
  page.drawText(scheme, {
    x: rightX - font.widthOfTextAtSize(scheme, 8),
    y: H - 76,
    size: 8,
    font,
    color: MUTED,
  });

  let y = H - 110;
  const label = "RATIBA  ·  CREW ROSTER CARD";
  page.drawText(label, { x: M, y, size: 8, font: bold, color: GOLD });
  y -= 26;
  page.drawText(meta.crew_name, { x: M, y, size: 20, font: bold, color: DARK });
  y -= 18;
  const sub = [
    meta.role,
    `Employee ${meta.employee_no}`,
    meta.base_station ? `Base ${meta.base_station}` : null,
    meta.operator_aoc
      ? `${meta.operator_name} (AOC ${meta.operator_aoc})`
      : meta.operator_name,
  ]
    .filter(Boolean)
    .join("  ·  ");
  const clip = (s: string, f: PDFFont, size: number, maxWidth: number) => {
    while (s.length > 1 && f.widthOfTextAtSize(s, size) > maxWidth)
      s = s.slice(0, -1);
    return s;
  };
  page.drawText(clip(sub, font, 9.5, W - 2 * M), {
    x: M,
    y,
    size: 9.5,
    font,
    color: MUTED,
  });
  y -= 12;
  page.drawLine({
    start: { x: M, y },
    end: { x: W - M, y },
    thickness: 1.2,
    color: GOLD,
  });

  // ── calendar grid ───────────────────────────────────────────────────────
  const gridTop = y - 14;
  const dowHeaderH = 18;
  const daysInMonth = new Date(Date.UTC(meta.year, meta.month, 0)).getUTCDate();
  const firstDow =
    (new Date(Date.UTC(meta.year, meta.month - 1, 1)).getUTCDay() + 6) % 7; // Mon=0
  const rows = Math.ceil((firstDow + daysInMonth) / 7);
  const reservedBottom = 205; // stats + legend + footer
  const available = gridTop - dowHeaderH - reservedBottom - M;
  const cellH = Math.max(42, Math.min(72, available / rows));
  const colW = (W - 2 * M) / 7;

  for (let c = 0; c < 7; c++) {
    const x = M + c * colW;
    page.drawRectangle({
      x,
      y: gridTop - dowHeaderH,
      width: colW,
      height: dowHeaderH,
      color: DARK,
    });
    page.drawText(WEEKDAYS[c]!, {
      x: centered(WEEKDAYS[c]!, bold, 8, x + colW / 2),
      y: gridTop - dowHeaderH + 6,
      size: 8,
      font: bold,
      color: rgb(1, 1, 1),
    });
  }

  const badgeFor = (d: CrewRosterDay): Badge | null => {
    if (d.type === "LEAVE") return BADGES.LEAVE!;
    if (d.type === "STANDBY") return BADGES.SBY!;
    if (d.type === "FDP" && d.legality_state)
      return BADGES[d.legality_state] ?? null;
    return null;
  };

  let gridBottom = gridTop - dowHeaderH;
  for (let day = 1; day <= daysInMonth; day++) {
    const cellIdx = firstDow + day - 1;
    const row = Math.floor(cellIdx / 7);
    const col = cellIdx % 7;
    const x = M + col * colW;
    const cellTop = gridTop - dowHeaderH - row * cellH;
    const cellBottom = cellTop - cellH;
    gridBottom = Math.min(gridBottom, cellBottom);
    page.drawRectangle({
      x,
      y: cellBottom,
      width: colW,
      height: cellH,
      borderColor: BORDER,
      borderWidth: 0.6,
      color: rgb(1, 1, 1),
    });
    page.drawText(String(day), {
      x: x + 5,
      y: cellTop - 12,
      size: 8.5,
      font: bold,
      color: DARK,
    });

    const dateIso = `${meta.year}-${String(meta.month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const d = byDate[dateIso];
    if (!d) continue;
    let ty = cellTop - 24;
    const lh = 8.5;
    const cellClip = (s: string, f: PDFFont, size: number) => {
      while (s.length > 1 && f.widthOfTextAtSize(s, size) > colW - 8)
        s = s.slice(0, -1);
      return s;
    };
    for (const s of d.sectors.slice(0, 2)) {
      page.drawText(cellClip(s.flight_no, font, 7), {
        x: x + 5,
        y: ty,
        size: 7,
        font,
        color: INK,
      });
      ty -= lh;
    }
    if (d.type === "FDP" || d.type === "STANDBY") {
      const hrs =
        d.type === "FDP"
          ? `${d.duty_hours.toFixed(1)}h duty · ${d.flight_hours.toFixed(1)}h block`
          : `${d.duty_hours.toFixed(1)}h duty`;
      page.drawText(cellClip(hrs, font, 6.2), {
        x: x + 5,
        y: ty,
        size: 6.2,
        font,
        color: MUTED,
      });
      ty -= lh;
    }
    const badge = badgeFor(d);
    if (badge) {
      const bw = bold.widthOfTextAtSize(badge.label, 6.5) + 8;
      page.drawRectangle({
        x: x + 5,
        y: cellBottom + 5,
        width: bw,
        height: 11,
        color: badge.bg,
      });
      page.drawText(badge.label, {
        x: x + 9,
        y: cellBottom + 8.5,
        size: 6.5,
        font: bold,
        color: badge.fg,
      });
    }
  }

  // ── summary tiles ───────────────────────────────────────────────────────
  const fdpCount = days.filter((d) => d.type === "FDP").length;
  const totalDuty = days.reduce(
    (a, d) => a + (d.type !== "LEAVE" ? d.duty_hours : 0),
    0,
  );
  const blockHours = days.reduce((a, d) => a + d.flight_hours, 0);
  const leaveDays = days.filter((d) => d.type === "LEAVE").length;
  const anomalies = days.filter(
    (d) => d.legality_state && d.legality_state !== "LEGAL",
  ).length;

  const tiles: [string, string][] = [
    [String(fdpCount), "FDPs"],
    [`${Math.round(totalDuty)}h`, "Total duty"],
    [`${Math.round(blockHours)}h`, "Block hours"],
    [String(leaveDays), "Leave days"],
    [String(anomalies), "FTL anomalies"],
  ];
  const tileW = (W - 2 * M) / 5;
  const tileTop = gridBottom - 20;
  const tileH = 56;
  for (let i = 0; i < tiles.length; i++) {
    const x = M + i * tileW;
    page.drawRectangle({
      x: x + 3,
      y: tileTop - tileH,
      width: tileW - 6,
      height: tileH,
      color: FOG,
    });
    const [big, small] = tiles[i]!;
    page.drawText(big, {
      x: centered(big, bold, 20, x + tileW / 2),
      y: tileTop - 30,
      size: 20,
      font: bold,
      color: anomalies > 0 && small === "FTL anomalies" ? RED : DARK,
    });
    page.drawText(small, {
      x: centered(small, font, 7.5, x + tileW / 2),
      y: tileTop - tileH + 10,
      size: 7.5,
      font,
      color: MUTED,
    });
  }

  // ── legend ──────────────────────────────────────────────────────────────
  const legendItems: [string, string][] = [
    ["LEGAL", "within limits"],
    ["AT LIMIT", "at regulatory cap"],
    ["FRMS", "derogation required"],
    ["ILLEGAL", "regulatory breach"],
    ["LEAVE", "approved leave"],
    ["SBY", "standby duty"],
  ];
  const legendKeyByLabel: Record<string, string> = {
    LEGAL: "LEGAL",
    "AT LIMIT": "AT_LIMIT",
    FRMS: "REQUIRES_FRMS_DEROGATION",
    ILLEGAL: "ILLEGAL",
    LEAVE: "LEAVE",
    SBY: "SBY",
  };
  let ly = tileTop - tileH - 26;
  const legendColW = (W - 2 * M) / 3;
  legendItems.forEach(([lbl, desc], i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = M + col * legendColW;
    const yy = ly - row * 22;
    const badge = BADGES[legendKeyByLabel[lbl]!]!;
    const bw = bold.widthOfTextAtSize(lbl, 6.5) + 10;
    page.drawRectangle({
      x,
      y: yy - 8,
      width: bw,
      height: 12,
      color: badge.bg,
    });
    page.drawText(lbl, {
      x: x + 5,
      y: yy - 5,
      size: 6.5,
      font: bold,
      color: badge.fg,
    });
    page.drawText(desc, {
      x: x + bw + 6,
      y: yy - 5,
      size: 7.5,
      font,
      color: MUTED,
    });
  });

  // ── footer ──────────────────────────────────────────────────────────────
  const footerY = M - 10;
  page.drawLine({
    start: { x: M, y: footerY + 24 },
    end: { x: W - M, y: footerY + 24 },
    thickness: 0.5,
    color: BORDER,
  });
  page.drawText("Generated by Ratiba · DN Consultancy", {
    x: M,
    y: footerY + 10,
    size: 7,
    font,
    color: MUTED,
  });
  const right = "KCAA Flight Duty Time Scheme aligned · Confidential";
  page.drawText(right, {
    x: W - M - font.widthOfTextAtSize(right, 7),
    y: footerY + 10,
    size: 7,
    font,
    color: MUTED,
  });
  const tagline = "Shaping Africa's Future, Together.";
  page.drawText(tagline, {
    x: centered(tagline, italic, 8, W / 2),
    y: footerY - 4,
    size: 8,
    font: italic,
    color: GOLD,
  });
  const pageNum = "1 / 1";
  page.drawText(pageNum, {
    x: W - M - font.widthOfTextAtSize(pageNum, 7),
    y: M - 24,
    size: 7,
    font,
    color: MUTED,
  });

  return await doc.save({ useObjectStreams: false });
}
