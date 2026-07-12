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

export async function buildAuditPackPdf(meta: AuditPackMeta, rows: AuditFdpRow[]): Promise<Uint8Array> {
  const doc = await PDFDocument.create();
  const created = new Date(meta.created_at);
  doc.setTitle(`Ratiba audit pack ${meta.period_from} to ${meta.period_to}`);
  doc.setProducer(`Ratiba ${meta.generator_version}`);
  doc.setCreationDate(created);
  doc.setModificationDate(created);

  const font = await doc.embedFont(StandardFonts.Helvetica);
  const bold = await doc.embedFont(StandardFonts.HelveticaBold);
  const W = 595.28, H = 841.89, M = 50; // A4 portrait

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
  text(`Crew covered: ${meta.crew_count}    FDPs evaluated: ${meta.fdp_count}    Anomalies: ${meta.anomaly_count}`, 11, bold);
  y -= 14;
  text("Methodology", 13, bold, STEEL);
  text("Every flight duty period in the reporting window was evaluated against the", 9, font);
  text("KCAA Flight Duty Time Scheme (CAA-AC-OPS033; ICAO Annex 6 Part I, 4.10)", 9, font);
  text("using the rule set below. Verdicts: LEGAL, AT_LIMIT,", 9, font);
  text("REQUIRES_FRMS_DEROGATION (acceptable only under an approved FRMS), ILLEGAL.", 9, font);
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
    LEGAL: "OK", AT_LIMIT: "AT-LIM", REQUIRES_FRMS_DEROGATION: "FRMS", ILLEGAL: "ILLEGAL",
  };
  let rowY = 0;
  const newTablePage = () => {
    page = doc.addPage([W, H]);
    rowY = H - 60;
    page.drawText(`FDP register  —  ${meta.period_from} to ${meta.period_to}`, {
      x: M, y: rowY, size: 11, font: bold, color: STEEL,
    });
    rowY -= 20;
    for (const c of cols) page.drawText(c.h, { x: c.x, y: rowY, size: 8, font: bold, color: INK });
    rowY -= 4;
    page.drawLine({ start: { x: M, y: rowY }, end: { x: W - M, y: rowY }, thickness: 0.7, color: STEEL });
    rowY -= 12;
  };
  newTablePage();
  const clip = (s: string, w: number, size: number) => {
    while (s.length > 1 && font.widthOfTextAtSize(s, size) > w - 4) s = s.slice(0, -1);
    return s;
  };
  for (const r of rows) {
    if (rowY < 60) newTablePage();
    const bad = r.legality_state !== "LEGAL";
    const cells = [
      r.date, r.crew_label, hhmm(r.report_time), hhmm(r.off_duty_time),
      r.duty_hours.toFixed(2), String(r.sectors_count),
      short[r.legality_state] ?? r.legality_state, bad ? r.worst_rule : "",
    ];
    cells.forEach((cell, i) => {
      page.drawText(clip(cell, cols[i].w, 8), {
        x: cols[i].x, y: rowY, size: 8, font: bad && i >= 6 ? bold : font, color: bad && i >= 6 ? RED : INK,
      });
    });
    rowY -= 12;
  }
  if (!rows.length) page.drawText("No FDPs recorded in this period.", { x: M, y: rowY, size: 10, font });

  return await doc.save({ useObjectStreams: false });
}

export async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const d = await crypto.subtle.digest("SHA-256", bytes as BufferSource);
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// ── crew monthly roster PDF ─────────────────────────────────────────────────

export interface CrewRosterDay {
  date: string;
  type: string; // FDP | STANDBY | OFF | LEAVE
  legality_state: string | null;
  sectors: { flight_no: string; origin: string; destination: string; std: string; sta: string }[];
}

export interface CrewRosterMeta {
  operator_name: string;
  crew_name: string;
  employee_no: string;
  role: string;
  year: number;
  month: number; // 1-12
  generated_at: string;
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export async function buildCrewRosterPdf(meta: CrewRosterMeta, days: CrewRosterDay[]): Promise<Uint8Array> {
  const doc = await PDFDocument.create();
  const created = new Date(meta.generated_at);
  doc.setTitle(`${meta.crew_name} roster ${meta.year}-${String(meta.month).padStart(2, "0")}`);
  doc.setProducer("Ratiba");
  doc.setCreationDate(created);
  doc.setModificationDate(created);

  const font = await doc.embedFont(StandardFonts.Helvetica);
  const bold = await doc.embedFont(StandardFonts.HelveticaBold);
  const W = 595.28, H = 841.89, M = 50;
  let page = doc.addPage([W, H]);
  let y = H - 70;

  const line = (s: string, size: number, f: PDFFont, color = INK) => {
    page.drawText(s, { x: M, y, size, font: f, color });
    y -= size + 7;
  };
  line(`${MONTH_NAMES[meta.month - 1]} ${meta.year} roster`, 18, bold, STEEL);
  line(`${meta.crew_name}  (${meta.employee_no}, ${meta.role})`, 12, bold);
  line(meta.operator_name, 10, font);
  line(`Generated: ${created.toISOString()}`, 8, font);
  y -= 6;

  const cols = [
    { h: "Date", x: M, w: 55 },
    { h: "Type", x: M + 55, w: 70 },
    { h: "Details", x: M + 125, w: 300 },
    { h: "Verdict", x: M + 425, w: 60 },
  ];
  const newPage = () => {
    page = doc.addPage([W, H]);
    y = H - 60;
    for (const c of cols) page.drawText(c.h, { x: c.x, y, size: 9, font: bold, color: INK });
    y -= 4;
    page.drawLine({ start: { x: M, y }, end: { x: W - M, y }, thickness: 0.7, color: STEEL });
    y -= 12;
  };
  newPage();
  const clip = (s: string, w: number, size = 8) => {
    while (s.length > 1 && font.widthOfTextAtSize(s, size) > w - 4) s = s.slice(0, -1);
    return s;
  };
  const hhmm = (iso: string) => iso.slice(11, 16) + "Z";
  for (const d of days) {
    if (y < 60) newPage();
    const bad = d.legality_state && d.legality_state !== "LEGAL";
    const detail = d.sectors.length
      ? d.sectors.map((s) => `${s.flight_no} ${s.origin}-${s.destination} ${hhmm(s.std)}/${hhmm(s.sta)}`).join("; ")
      : "";
    const cells = [d.date, d.type, detail, d.legality_state ?? ""];
    cells.forEach((cell, i) => {
      page.drawText(clip(cell, cols[i].w, 8), {
        x: cols[i].x, y, size: 8, font: bad && i === 3 ? bold : font, color: bad && i === 3 ? RED : INK,
      });
    });
    y -= 12;
  }
  if (!days.length) page.drawText("No duties recorded this month.", { x: M, y, size: 10, font });

  return await doc.save({ useObjectStreams: false });
}
