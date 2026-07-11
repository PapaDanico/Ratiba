// Ratiba API — Supabase Edge Function port of the FastAPI backend.
//
// Phase 1: health/readiness, cookie+CSRF auth, dashboard reads.
// Phase 2: crew/fleet/notices/sectors CRUD, duties, leave, swaps, users,
//          settings, training, FTL limits, roster (list/publish/amend) and a
//          TypeScript auto-generate heuristic (the OR-Tools optimiser cannot
//          run in Deno; see autoGenerate()).
//
// Still 501: imports, audit-pack/roster PDFs, constraints (LLM parsing),
// IROP, fatigue/payroll reports, postings, pilot pairing / crew-me views.
//
// FDP legality here is a simplified port of the Python ftl_engine: the
// day-peak basic-crew limit with sector reductions (CAA-AC-OPS033 §4.6.3
// ceiling respected). The full band/rest/cumulative engine follows later;
// rows written by this port carry rules_applied=["SIMPLIFIED_TS_PORT"].

import { createClient } from "npm:@supabase/supabase-js@2";
import * as jose from "npm:jose@5";
import bcrypt from "npm:bcryptjs@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const db = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, { auth: { persistSession: false } });

const encoder = new TextEncoder();
const keyPromise = crypto.subtle
  .digest("SHA-256", encoder.encode(SERVICE_ROLE_KEY + ":ratiba-jwt-v1"))
  .then((d) => new Uint8Array(d));

const ACCESS_MINUTES = 30;
const REFRESH_DAYS = 30;
const AMBER_THRESHOLD_DAYS = 30;
const MAX_GENERATED_SECTORS = 366;

const ACCESS_COOKIE = "rt_access";
const REFRESH_COOKIE = "rt_refresh";
const PILOT_COOKIE = "rt_pilot";
const CSRF_COOKIE = "rt_csrf";
const CSRF_SAFE = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);
const CSRF_EXEMPT = new Set([
  "/api/v1/auth/login",
  "/api/v1/auth/pilot-pair",
  "/api/v1/auth/demo-workspace",
]);
const WRITER_ROLES = new Set(["CREWING_OFFICER", "CHIEF_PILOT", "ADMIN"]);

// ── generic helpers ─────────────────────────────────────────────────────────

class ApiError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

function json(body: unknown, status = 200, headers: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

function parseCookies(req: Request): Record<string, string> {
  const out: Record<string, string> = {};
  for (const part of (req.headers.get("cookie") ?? "").split(/;\s*/)) {
    const i = part.indexOf("=");
    if (i > 0) out[part.slice(0, i)] = decodeURIComponent(part.slice(i + 1));
  }
  return out;
}

function cookie(name: string, value: string, maxAge: number, httpOnly: boolean): string {
  return `${name}=${value}; Max-Age=${maxAge}; Path=/; SameSite=Lax; Secure${httpOnly ? "; HttpOnly" : ""}`;
}

function authCookies(access: string, refresh: string): string[] {
  const csrf = crypto.randomUUID().replaceAll("-", "") + crypto.randomUUID().replaceAll("-", "");
  return [
    cookie(ACCESS_COOKIE, access, ACCESS_MINUTES * 60, true),
    cookie(REFRESH_COOKIE, refresh, REFRESH_DAYS * 86400, true),
    cookie(CSRF_COOKIE, csrf, REFRESH_DAYS * 86400, false),
  ];
}

async function signToken(
  sub: string,
  type: "access" | "refresh",
  extra: Record<string, unknown> = {},
): Promise<string> {
  const key = await keyPromise;
  const now = Math.floor(Date.now() / 1000);
  const exp = type === "access" ? now + ACCESS_MINUTES * 60 : now + REFRESH_DAYS * 86400;
  return await new jose.SignJWT({ sub, type, iat: now, exp, jti: crypto.randomUUID(), ...extra })
    .setProtectedHeader({ alg: "HS256" })
    .sign(key);
}

async function decodeToken(token: string): Promise<jose.JWTPayload | null> {
  try {
    const key = await keyPromise;
    const { payload } = await jose.jwtVerify(token, key);
    return payload;
  } catch {
    return null;
  }
}

type DbUser = {
  id: string;
  operator_id: string;
  email: string;
  hashed_password: string;
  full_name: string;
  role: string;
  is_active: boolean;
};

async function currentUser(req: Request): Promise<DbUser | null> {
  const auth = req.headers.get("authorization") ?? "";
  const raw = auth.toLowerCase().startsWith("bearer ")
    ? auth.slice(7).trim()
    : parseCookies(req)[ACCESS_COOKIE];
  if (!raw) return null;
  const payload = await decodeToken(raw);
  if (!payload || payload.type !== "access" || !payload.sub) return null;
  const { data } = await db.from("users").select("*").eq("id", payload.sub).maybeSingle();
  if (!data || !data.is_active) return null;
  return data as DbUser;
}

function requireWriter(user: DbUser) {
  if (!WRITER_ROLES.has(user.role)) {
    throw new ApiError(403, "your role cannot perform this action");
  }
}

function requireAdmin(user: DbUser) {
  if (user.role !== "ADMIN") throw new ApiError(403, "administrator role required");
}

async function readJson(req: Request): Promise<Record<string, unknown>> {
  try {
    return await req.json();
  } catch {
    throw new ApiError(422, "invalid JSON body");
  }
}

function need<T>(v: T | undefined | null, field: string): T {
  if (v === undefined || v === null || v === "") throw new ApiError(422, `${field} is required`);
  return v;
}

async function one<T = Record<string, unknown>>(q: Promise<{ data: unknown; error: unknown }>): Promise<T> {
  const { data, error } = await q;
  if (error) throw new ApiError(500, String((error as { message?: string }).message ?? error));
  return data as T;
}

async function auditLog(
  operatorId: string,
  actorUserId: string | null,
  action: string,
  entityType: string,
  entityId: string | null,
  before: unknown,
  after: unknown,
) {
  await db.from("audit_events").insert({
    operator_id: operatorId,
    actor_user_id: actorUserId,
    action,
    entity_type: entityType,
    entity_id: entityId,
    before_state: before ?? null,
    after_state: after ?? null,
  });
}

function daysBetween(expires: string, today: Date): number {
  return Math.round((new Date(expires + "T00:00:00Z").getTime() - today.getTime()) / 86400000);
}

function ragState(days: number): string {
  return days < 0 ? "RED" : days <= AMBER_THRESHOLD_DAYS ? "AMBER" : "GREEN";
}

function todayUTC(): Date {
  const t = new Date();
  t.setUTCHours(0, 0, 0, 0);
  return t;
}

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

// ── static reference data ───────────────────────────────────────────────────

const ROLE_CATEGORY: Record<string, string> = {
  CAPT: "FLIGHT_DECK",
  FO: "FLIGHT_DECK",
  SO: "FLIGHT_DECK",
  PURSER: "CABIN",
  CABIN_CREW: "CABIN",
  ENGINEER: "ENGINEERING",
};

const AIRCRAFT_TYPES: [string, string, string, string, number][] = [
  ["DH8D", "De Havilland Canada", "Dash 8 Q400", "turboprop", 78],
  ["DH8C", "De Havilland Canada", "Dash 8-300", "turboprop", 50],
  ["DH8B", "De Havilland Canada", "Dash 8-200", "turboprop", 37],
  ["DH8A", "De Havilland Canada", "Dash 8-100", "turboprop", 37],
  ["AT76", "ATR", "ATR 72-600", "turboprop", 70],
  ["AT75", "ATR", "ATR 72-500", "turboprop", 70],
  ["AT72", "ATR", "ATR 72-200", "turboprop", 66],
  ["AT46", "ATR", "ATR 42-600", "turboprop", 48],
  ["AT45", "ATR", "ATR 42-500", "turboprop", 48],
  ["AT43", "ATR", "ATR 42-300", "turboprop", 48],
  ["B190", "Beechcraft", "1900D", "turboprop", 19],
  ["F50", "Fokker", "50", "turboprop", 56],
  ["SF34", "Saab", "340", "turboprop", 34],
  ["JS41", "BAe", "Jetstream 41", "turboprop", 29],
  ["D228", "Dornier", "228", "turboprop", 19],
  ["L410", "Let", "L-410 Turbolet", "turboprop", 19],
  ["C208", "Cessna", "208 Caravan", "light", 12],
  ["C208B", "Cessna", "208B Grand Caravan", "light", 14],
  ["DHC6", "De Havilland Canada", "DHC-6 Twin Otter", "light", 19],
  ["PC12", "Pilatus", "PC-12", "light", 9],
  ["C404", "Cessna", "404 Titan", "light", 10],
  ["C402", "Cessna", "402", "light", 9],
  ["BN2P", "Britten-Norman", "BN-2 Islander", "light", 9],
  ["E145", "Embraer", "ERJ 145", "regional_jet", 50],
  ["E170", "Embraer", "E170", "regional_jet", 76],
  ["E190", "Embraer", "E190", "regional_jet", 100],
  ["CRJ2", "Bombardier", "CRJ200", "regional_jet", 50],
  ["CRJ9", "Bombardier", "CRJ900", "regional_jet", 90],
  ["F100", "Fokker", "100", "regional_jet", 100],
  ["F70", "Fokker", "70", "regional_jet", 79],
  ["F28", "Fokker", "F28 Fellowship", "regional_jet", 65],
  ["B733", "Boeing", "737-300", "narrowbody", 140],
  ["B738", "Boeing", "737-800", "narrowbody", 162],
  ["B737", "Boeing", "737-700", "narrowbody", 130],
  ["B732", "Boeing", "737-200", "narrowbody", 120],
  ["A319", "Airbus", "A319", "narrowbody", 128],
  ["A320", "Airbus", "A320", "narrowbody", 150],
  ["A321", "Airbus", "A321", "narrowbody", 180],
];
const KNOWN_TYPES = new Set(AIRCRAFT_TYPES.map((t) => t[0]));

// Mirrors app/services/ftl_engine.LIMITS (generic baseline).
const FTL_LIMITS = {
  fdp_max_basic_by_band: { WOCL: 11.0, EARLY: 12.0, DAY_PEAK: 13.0, AFTERNOON: 12.0 },
  fdp_scheduled_ceiling_basic_h: 14.0,
  fdp_sector_reduction_per_extra: 0.5,
  fdp_sector_floor: 9.0,
  fdp_aug_3_pilot: { 1: 3.0, 2: 2.0, 3: 1.0 },
  fdp_aug_4_pilot: { 1: 4.0, 2: 3.0, 3: 2.0 },
  fdp_aug_absolute_cap: 18.0,
  rest_home_floor_h: 12.0,
};
const REGULATION_REF = "KCAA CAA-AC-OPS033 (generic baseline)";

// Fixed-date Kenyan public holidays (variable Islamic dates omitted).
const KE_HOLIDAYS: [string, string][] = [
  ["01-01", "New Year's Day"],
  ["05-01", "Labour Day"],
  ["06-01", "Madaraka Day"],
  ["10-10", "Huduma Day"],
  ["10-20", "Mashujaa Day"],
  ["12-12", "Jamhuri Day"],
  ["12-25", "Christmas Day"],
  ["12-26", "Boxing Day"],
];

// ── serializers ─────────────────────────────────────────────────────────────

function userOut(u: DbUser) {
  return {
    id: u.id,
    email: u.email,
    full_name: u.full_name,
    role: u.role,
    operator_id: u.operator_id,
    is_active: u.is_active,
  };
}

// deno-lint-ignore no-explicit-any
function crewOut(r: any) {
  return {
    id: r.id,
    employee_no: r.employee_no,
    first_name: r.first_name,
    last_name: r.last_name,
    role: r.role,
    crew_category: ROLE_CATEGORY[r.role] ?? "FLIGHT_DECK",
    base_station: r.base_station,
    contract_type: r.contract_type,
    active: r.active,
    languages: r.languages ?? [],
    faith_observance_flags: r.faith_observance_flags ?? {},
    email: r.email,
    phone_number: r.phone_number,
    whatsapp_number: r.whatsapp_number,
    person_ref: r.person_ref,
  };
}

// deno-lint-ignore no-explicit-any
function sectorOut(s: any) {
  return {
    id: s.id,
    flight_no: s.flight_no,
    date: s.date,
    origin: s.origin,
    destination: s.destination,
    std: s.std,
    sta: s.sta,
    aircraft_reg: s.aircraft_reg,
    aircraft_type: s.aircraft_type,
    status: s.status,
    block_hours: Math.round(((new Date(s.sta).getTime() - new Date(s.std).getTime()) / 3600000) * 100) / 100,
  };
}

// deno-lint-ignore no-explicit-any
function leaveOut(r: any) {
  return {
    id: r.id,
    crew_id: r.crew_id,
    type: r.type,
    date_from: r.date_from,
    date_to: r.date_to,
    status: r.status,
    note: r.note,
    approver_id: r.approver_id,
  };
}

// deno-lint-ignore no-explicit-any
function swapOut(r: any) {
  return {
    id: r.id,
    crew_id_initiator: r.crew_id_initiator,
    crew_id_counterparty: r.crew_id_counterparty,
    fdp_or_sector_ref: r.fdp_or_sector_ref,
    reason: r.reason,
    status: r.status,
    approver_id: r.approver_id,
  };
}

// deno-lint-ignore no-explicit-any
function noticeOut(n: any) {
  return {
    id: n.id,
    category: n.category,
    severity: n.severity,
    title: n.title,
    body: n.body,
    image_url: n.image_url,
    requires_ack: n.requires_ack,
    published: n.published,
    pinned: n.pinned,
    published_at: n.published_at,
    expires_at: n.expires_at,
    created_at: n.created_at,
  };
}

// ── FDP legality (simplified port) ──────────────────────────────────────────

type SectorInput = {
  sector_id: string;
  date_local: string;
  std: string;
  sta: string;
  aircraft_reg: string;
  aircraft_type: string;
};

function computeFdp(daySectors: SectorInput[]) {
  const stds = daySectors.map((s) => new Date(s.std).getTime());
  const stas = daySectors.map((s) => new Date(s.sta).getTime());
  const report = new Date(Math.min(...stds) - 60 * 60000);
  const off = new Date(Math.max(...stas) + 30 * 60000);
  const flightH =
    Math.round(
      daySectors.reduce((acc, s) => acc + (new Date(s.sta).getTime() - new Date(s.std).getTime()) / 3600000, 0) * 100,
    ) / 100;
  const dutyH = Math.round(((off.getTime() - report.getTime()) / 3600000) * 100) / 100;
  const sectors = daySectors.length;
  const reduction = Math.max(0, sectors - 2) * FTL_LIMITS.fdp_sector_reduction_per_extra;
  const limit = Math.max(FTL_LIMITS.fdp_sector_floor, FTL_LIMITS.fdp_max_basic_by_band.DAY_PEAK - reduction);
  let legality = "LEGAL";
  if (dutyH > FTL_LIMITS.fdp_scheduled_ceiling_basic_h) legality = "ILLEGAL";
  else if (dutyH > limit) legality = "REQUIRES_FRMS_DEROGATION";
  else if (dutyH > limit - 1) legality = "AT_LIMIT";
  return { report, off, sectors, flightH, dutyH, legality };
}

const LEGALITY_ORDER = ["LEGAL", "AT_LIMIT", "REQUIRES_FRMS_DEROGATION", "ILLEGAL"];
function worstLegality(states: (string | null)[]): string | null {
  const known = states.filter((s): s is string => !!s);
  if (!known.length) return null;
  return known.sort((a, b) => LEGALITY_ORDER.indexOf(a) - LEGALITY_ORDER.indexOf(b)).at(-1)!;
}

// ── auth handlers ───────────────────────────────────────────────────────────

async function tokenResponse(user: DbUser): Promise<Response> {
  const access = await signToken(user.id, "access", { operator_id: user.operator_id });
  const refresh = await signToken(user.id, "refresh");
  const headers = new Headers({ "content-type": "application/json" });
  for (const c of authCookies(access, refresh)) headers.append("set-cookie", c);
  return new Response(
    JSON.stringify({ access_token: access, refresh_token: refresh, token_type: "bearer" }),
    { status: 200, headers },
  );
}

async function handleLogin(req: Request): Promise<Response> {
  const body = await readJson(req);
  const email = body.email as string | undefined;
  const password = body.password as string | undefined;
  if (!email || !password) return json({ detail: "invalid body" }, 422);
  const { data: user } = await db.from("users").select("*").eq("email", email).maybeSingle();
  if (!user || !user.is_active || !bcrypt.compareSync(password.slice(0, 72), user.hashed_password)) {
    return json({ detail: "invalid email or password" }, 401);
  }
  return tokenResponse(user as DbUser);
}

async function handleRefresh(req: Request): Promise<Response> {
  let raw: string | undefined;
  try {
    raw = ((await req.json()) as { refresh_token?: string })?.refresh_token;
  } catch { /* cookie fallback */ }
  raw = raw || parseCookies(req)[REFRESH_COOKIE];
  if (!raw) return json({ detail: "missing refresh token" }, 401);
  const payload = await decodeToken(raw);
  if (!payload || payload.type !== "refresh" || !payload.sub || !payload.jti) {
    return json({ detail: "invalid refresh token" }, 401);
  }
  const { data: revoked } = await db.from("revoked_tokens").select("jti").eq("jti", payload.jti).maybeSingle();
  if (revoked) return json({ detail: "refresh token already used or revoked" }, 401);
  const { data: user } = await db.from("users").select("*").eq("id", payload.sub).maybeSingle();
  if (!user || !user.is_active) return json({ detail: "user not found" }, 401);
  await db.from("revoked_tokens").insert({
    jti: payload.jti,
    expires_at: new Date((payload.exp ?? 0) * 1000).toISOString(),
  });
  return tokenResponse(user as DbUser);
}

async function handleLogout(req: Request): Promise<Response> {
  let raw: string | undefined;
  try {
    raw = ((await req.json()) as { refresh_token?: string })?.refresh_token;
  } catch { /* cookie fallback */ }
  raw = raw || parseCookies(req)[REFRESH_COOKIE];
  if (raw) {
    const payload = await decodeToken(raw);
    if (payload?.type === "refresh" && payload.jti) {
      await db.from("revoked_tokens").upsert({
        jti: payload.jti,
        expires_at: new Date((payload.exp ?? 0) * 1000).toISOString(),
      });
    }
  }
  const headers = new Headers();
  for (const n of [ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE]) {
    headers.append("set-cookie", `${n}=; Max-Age=0; Path=/`);
  }
  return new Response(null, { status: 204, headers });
}

// ── crew ────────────────────────────────────────────────────────────────────

async function crewList(user: DbUser, url: URL): Promise<Response> {
  const data = await one<Record<string, unknown>[]>(
    db.from("crew").select("*").eq("operator_id", user.operator_id).order("last_name").order("first_name"),
  );
  const category = url.searchParams.get("category");
  return json((data ?? []).map(crewOut).filter((r) => !category || r.crew_category === category));
}

async function crewCreate(user: DbUser, req: Request): Promise<Response> {
  requireWriter(user);
  const b = await readJson(req);
  const row = {
    operator_id: user.operator_id,
    created_by_user_id: user.id,
    employee_no: need(b.employee_no, "employee_no"),
    first_name: need(b.first_name, "first_name"),
    last_name: need(b.last_name, "last_name"),
    role: need(b.role, "role"),
    date_of_hire: need(b.date_of_hire, "date_of_hire"),
    date_of_birth: need(b.date_of_birth, "date_of_birth"),
    base_station: need(b.base_station, "base_station"),
    contract_type: need(b.contract_type, "contract_type"),
    active: b.active ?? true,
    languages: b.languages ?? [],
    faith_observance_flags: b.faith_observance_flags ?? {},
    email: b.email ?? null,
    phone_number: b.phone_number ?? null,
    whatsapp_number: b.whatsapp_number ?? null,
    person_ref: b.person_ref ?? null,
  };
  const created = await one(db.from("crew").insert(row).select().single());
  await auditLog(user.operator_id, user.id, "CREATE_CREW", "crew", (created as { id: string }).id, null, b);
  return json(crewOut(created), 201);
}

async function crewGetOrPatch(user: DbUser, req: Request, crewId: string): Promise<Response> {
  const existing = await one<Record<string, unknown> | null>(
    db.from("crew").select("*").eq("id", crewId).eq("operator_id", user.operator_id).maybeSingle(),
  );
  if (!existing) return json({ detail: "crew not found" }, 404);
  if (req.method === "GET") return json(crewOut(existing));
  requireWriter(user);
  const b = await readJson(req);
  const allowed = [
    "first_name", "last_name", "base_station", "contract_type", "active", "languages",
    "faith_observance_flags", "email", "phone_number", "whatsapp_number", "person_ref",
  ];
  const updates: Record<string, unknown> = {};
  for (const k of allowed) if (k in b) updates[k] = b[k];
  const updated = await one(
    db.from("crew").update(updates).eq("id", crewId).eq("operator_id", user.operator_id).select().single(),
  );
  await auditLog(user.operator_id, user.id, "UPDATE_CREW", "crew", crewId, crewOut(existing), crewOut(updated));
  return json(crewOut(updated));
}

async function crewCurrency(user: DbUser, req: Request, crewId: string): Promise<Response> {
  if (req.method === "GET") {
    const rows = await one<Record<string, unknown>[]>(
      db.from("crew_currencies").select("*").eq("crew_id", crewId).eq("operator_id", user.operator_id)
        .order("expires_date"),
    );
    return json(
      (rows ?? []).map((r) => ({
        id: r.id, crew_id: r.crew_id, currency_type: r.currency_type,
        last_completed_date: r.last_completed_date, expires_date: r.expires_date, evidence_ref: r.evidence_ref,
      })),
    );
  }
  requireWriter(user);
  const b = await readJson(req);
  const crew = await one<Record<string, unknown> | null>(
    db.from("crew").select("id").eq("id", crewId).eq("operator_id", user.operator_id).maybeSingle(),
  );
  if (!crew) return json({ detail: "crew not found" }, 404);
  const created = await one(
    db.from("crew_currencies").insert({
      operator_id: user.operator_id, created_by_user_id: user.id, crew_id: crewId,
      currency_type: need(b.currency_type, "currency_type"),
      last_completed_date: need(b.last_completed_date, "last_completed_date"),
      expires_date: need(b.expires_date, "expires_date"),
      evidence_ref: b.evidence_ref ?? null,
    }).select().single(),
  );
  const c = created as Record<string, unknown>;
  await auditLog(user.operator_id, user.id, "RECORD_CURRENCY", "crew_currency", c.id as string, null, b);
  return json({
    id: c.id, crew_id: c.crew_id, currency_type: c.currency_type,
    last_completed_date: c.last_completed_date, expires_date: c.expires_date, evidence_ref: c.evidence_ref,
  }, 201);
}

async function currencyDashboard(user: DbUser): Promise<Response> {
  const data = await one<Record<string, unknown>[]>(
    db.from("crew_currencies").select("*").eq("operator_id", user.operator_id),
  );
  const today = todayUTC();
  return json(
    (data ?? []).map((r) => {
      const days = daysBetween(r.expires_date as string, today);
      return {
        crew_id: r.crew_id, currency_type: r.currency_type, expires_date: r.expires_date,
        days_remaining: days, state: ragState(days),
      };
    }),
  );
}

// ── fleet ───────────────────────────────────────────────────────────────────

// deno-lint-ignore no-explicit-any
function aircraftOut(a: any) {
  return {
    id: a.id, registration: a.registration, aircraft_type: a.aircraft_type, active: a.active,
    aircraft_type_known: KNOWN_TYPES.has(a.aircraft_type),
  };
}

async function fleet(user: DbUser, req: Request): Promise<Response> {
  if (req.method === "GET") {
    const data = await one<Record<string, unknown>[]>(
      db.from("aircraft").select("*").eq("operator_id", user.operator_id).order("registration"),
    );
    return json((data ?? []).map(aircraftOut));
  }
  requireWriter(user);
  const b = await readJson(req);
  const reg = String(need(b.registration, "registration")).trim().toUpperCase();
  const { data: existing } = await db.from("aircraft").select("id")
    .eq("operator_id", user.operator_id).eq("registration", reg).maybeSingle();
  if (existing) return json({ detail: `${reg} already registered` }, 409);
  const created = await one(
    db.from("aircraft").insert({
      operator_id: user.operator_id, created_by_user_id: user.id, registration: reg,
      aircraft_type: String(need(b.aircraft_type, "aircraft_type")).trim().toUpperCase(),
      active: b.active ?? true,
    }).select().single(),
  );
  await auditLog(user.operator_id, user.id, "ADD_AIRCRAFT", "aircraft", (created as { id: string }).id, null, {
    registration: reg,
  });
  return json(aircraftOut(created), 201);
}

async function fleetPatch(user: DbUser, req: Request, id: string): Promise<Response> {
  requireWriter(user);
  const existing = await one<Record<string, unknown> | null>(
    db.from("aircraft").select("*").eq("id", id).eq("operator_id", user.operator_id).maybeSingle(),
  );
  if (!existing) return json({ detail: "aircraft not found" }, 404);
  const b = await readJson(req);
  const updates: Record<string, unknown> = {};
  if (typeof b.aircraft_type === "string" && b.aircraft_type) {
    updates.aircraft_type = b.aircraft_type.trim().toUpperCase();
  }
  if (typeof b.active === "boolean") updates.active = b.active;
  const updated = await one(db.from("aircraft").update(updates).eq("id", id).select().single());
  await auditLog(user.operator_id, user.id, "UPDATE_AIRCRAFT", "aircraft", id, aircraftOut(existing), aircraftOut(updated));
  return json(aircraftOut(updated));
}

// ── notices ─────────────────────────────────────────────────────────────────

async function notices(user: DbUser, req: Request, url: URL): Promise<Response> {
  if (req.method === "GET") {
    const category = url.searchParams.get("category");
    let q = db.from("notices").select("*").eq("operator_id", user.operator_id);
    if (category) q = q.eq("category", category);
    const [notice_rows, { count }] = await Promise.all([
      one<Record<string, unknown>[]>(q.order("pinned", { ascending: false }).order("created_at", { ascending: false })),
      db.from("crew").select("id", { count: "exact", head: true }).eq("operator_id", user.operator_id).eq("active", true),
    ]);
    const ids = (notice_rows ?? []).map((n) => n.id as string);
    const ackCounts: Record<string, number> = {};
    if (ids.length) {
      const { data: acks } = await db.from("notice_acknowledgements").select("notice_id").in("notice_id", ids);
      for (const a of acks ?? []) ackCounts[a.notice_id] = (ackCounts[a.notice_id] ?? 0) + 1;
    }
    return json(
      (notice_rows ?? []).map((n) => ({
        ...noticeOut(n),
        ack_count: ackCounts[n.id as string] ?? 0,
        crew_total: count ?? 0,
      })),
    );
  }
  requireWriter(user);
  const b = await readJson(req);
  const published = b.published ?? true;
  const created = await one(
    db.from("notices").insert({
      operator_id: user.operator_id, created_by_user_id: user.id,
      category: need(b.category, "category"),
      severity: b.severity ?? "INFO",
      title: need(b.title, "title"),
      body: need(b.body, "body"),
      image_url: b.image_url ?? null,
      requires_ack: b.requires_ack ?? false,
      pinned: b.pinned ?? false,
      published,
      published_at: published ? new Date().toISOString() : null,
      expires_at: b.expires_at ?? null,
    }).select().single(),
  );
  await auditLog(user.operator_id, user.id, "CREATE_NOTICE", "notice", (created as { id: string }).id, null, {
    title: b.title, published,
  });
  return json(noticeOut(created), 201);
}

async function noticePatch(user: DbUser, req: Request, id: string): Promise<Response> {
  requireWriter(user);
  const existing = await one<Record<string, unknown> | null>(
    db.from("notices").select("*").eq("id", id).eq("operator_id", user.operator_id).maybeSingle(),
  );
  if (!existing) return json({ detail: "notice not found" }, 404);
  const b = await readJson(req);
  const updates: Record<string, unknown> = {};
  for (const k of ["title", "body", "severity", "image_url", "requires_ack", "pinned", "published", "expires_at"]) {
    if (k in b) updates[k] = b[k];
  }
  if (updates.published === true && !existing.published_at) updates.published_at = new Date().toISOString();
  const updated = await one(db.from("notices").update(updates).eq("id", id).select().single());
  await auditLog(user.operator_id, user.id, "UPDATE_NOTICE", "notice", id, noticeOut(existing), noticeOut(updated));
  return json(noticeOut(updated));
}

// ── sectors (routings) ──────────────────────────────────────────────────────

async function sectors(user: DbUser, req: Request, url: URL): Promise<Response> {
  if (req.method === "GET") {
    const dateFrom = need(url.searchParams.get("date_from"), "date_from");
    const dateTo = need(url.searchParams.get("date_to"), "date_to");
    const rows = await one<Record<string, unknown>[]>(
      db.from("sectors").select("*").eq("operator_id", user.operator_id)
        .gte("date", dateFrom).lte("date", dateTo).order("date").order("std"),
    );
    return json((rows ?? []).map(sectorOut));
  }
  requireWriter(user);
  const b = await readJson(req);
  const std = new Date(String(need(b.std, "std")));
  const sta = new Date(String(need(b.sta, "sta")));
  if (sta <= std) return json({ detail: "sta must be after std" }, 422);
  const up = (v: unknown, f: string) => String(need(v, f)).trim().toUpperCase();
  const created = await one(
    db.from("sectors").insert({
      operator_id: user.operator_id, created_by_user_id: user.id,
      flight_no: up(b.flight_no, "flight_no"),
      date: need(b.date, "date"),
      origin: up(b.origin, "origin"),
      destination: up(b.destination, "destination"),
      std: std.toISOString(), sta: sta.toISOString(),
      aircraft_reg: up(b.aircraft_reg, "aircraft_reg"),
      aircraft_type: up(b.aircraft_type, "aircraft_type"),
      status: "PLANNED",
    }).select().single(),
  );
  await auditLog(user.operator_id, user.id, "CREATE_SECTOR", "sector", (created as { id: string }).id, null, b);
  return json(sectorOut(created), 201);
}

async function sectorsRecurring(user: DbUser, req: Request): Promise<Response> {
  requireWriter(user);
  const b = await readJson(req);
  const dateFrom = String(need(b.date_from, "date_from"));
  const dateTo = String(need(b.date_to, "date_to"));
  if (dateTo < dateFrom) return json({ detail: "date_to before date_from" }, 422);
  const wanted = new Set((b.days_of_week as number[] | undefined) ?? []);
  const up = (v: unknown, f: string) => String(need(v, f)).trim().toUpperCase();
  const flightNo = up(b.flight_no, "flight_no");
  const stdTime = String(need(b.std_time, "std_time"));
  const staTime = String(need(b.sta_time, "sta_time"));

  const targets: string[] = [];
  for (let d = new Date(dateFrom + "T00:00:00Z"); isoDate(d) <= dateTo; d.setUTCDate(d.getUTCDate() + 1)) {
    const weekday = (d.getUTCDay() + 6) % 7; // JS Sun=0 → Python Mon=0
    if (!wanted.size || wanted.has(weekday)) targets.push(isoDate(d));
  }
  if (!targets.length) return json({ detail: "no dates match the selected days of week in this range" }, 422);
  if (targets.length > MAX_GENERATED_SECTORS) {
    return json({
      detail: `pattern would create ${targets.length} routings (limit ${MAX_GENERATED_SECTORS}); narrow the date range`,
    }, 422);
  }

  const { data: existingRows } = await db.from("sectors").select("date")
    .eq("operator_id", user.operator_id).eq("flight_no", flightNo).gte("date", dateFrom).lte("date", dateTo);
  const existing = new Set((existingRows ?? []).map((r) => r.date as string));

  const inserts = [];
  let skipped = 0;
  for (const day of targets) {
    if (existing.has(day)) { skipped++; continue; }
    const std = new Date(`${day}T${stdTime}Z`);
    let sta = new Date(`${day}T${staTime}Z`);
    if (sta <= std) sta = new Date(sta.getTime() + 86400000); // overnight
    inserts.push({
      operator_id: user.operator_id, created_by_user_id: user.id,
      flight_no: flightNo, date: day,
      origin: up(b.origin, "origin"), destination: up(b.destination, "destination"),
      std: std.toISOString(), sta: sta.toISOString(),
      aircraft_reg: up(b.aircraft_reg, "aircraft_reg"), aircraft_type: up(b.aircraft_type, "aircraft_type"),
      status: "PLANNED",
    });
  }
  let created: Record<string, unknown>[] = [];
  if (inserts.length) {
    created = await one<Record<string, unknown>[]>(db.from("sectors").insert(inserts).select());
    await auditLog(user.operator_id, user.id, "CREATE_RECURRING_SECTORS", "sector", null, null, {
      flight_no: flightNo, date_from: dateFrom, date_to: dateTo, created: created.length, skipped_existing: skipped,
    });
  }
  return json({ created: created.length, skipped_existing: skipped, sectors: created.map(sectorOut) }, 201);
}

async function sectorDelete(user: DbUser, id: string): Promise<Response> {
  const existing = await one<Record<string, unknown> | null>(
    db.from("sectors").select("*").eq("id", id).eq("operator_id", user.operator_id).maybeSingle(),
  );
  if (!existing) return json({ detail: "sector not found" }, 404);
  if (existing.status !== "PLANNED") {
    return json({ detail: "only PLANNED sectors can be deleted; this one is already published" }, 409);
  }
  await db.from("sectors").delete().eq("id", id);
  await auditLog(user.operator_id, user.id, "DELETE_SECTOR", "sector", id, {
    flight_no: existing.flight_no, date: existing.date,
  }, null);
  return new Response(null, { status: 204 });
}

// ── duties (standby / off) ──────────────────────────────────────────────────

// deno-lint-ignore no-explicit-any
function dutyOut(f: any, crew: any) {
  const duration = Math.round(((new Date(f.off_duty_time).getTime() - new Date(f.report_time).getTime()) / 3600000) * 100) / 100;
  return {
    id: f.id, crew_id: f.crew_id,
    employee_no: crew?.employee_no ?? "—",
    crew_name: crew ? `${crew.first_name} ${crew.last_name}` : "—",
    date: f.date, type: f.type, start: f.report_time, end: f.off_duty_time,
    duration_h: duration, legality_state: f.legality_state ?? null,
  };
}

async function duties(user: DbUser, req: Request, url: URL): Promise<Response> {
  if (req.method === "GET") {
    const dateFrom = need(url.searchParams.get("date_from"), "date_from");
    const dateTo = need(url.searchParams.get("date_to"), "date_to");
    const rows = await one<Record<string, unknown>[]>(
      db.from("flight_duty_periods").select("*").eq("operator_id", user.operator_id)
        .neq("type", "FDP").gte("date", dateFrom).lte("date", dateTo).order("date"),
    );
    const crewIds = [...new Set((rows ?? []).map((r) => r.crew_id as string))];
    const crewById: Record<string, Record<string, unknown>> = {};
    if (crewIds.length) {
      const { data: crews } = await db.from("crew").select("id, employee_no, first_name, last_name").in("id", crewIds);
      for (const c of crews ?? []) crewById[c.id] = c;
    }
    return json((rows ?? []).map((f) => dutyOut(f, crewById[f.crew_id as string])));
  }
  requireWriter(user);
  const b = await readJson(req);
  const dutyType = String(need(b.duty_type, "duty_type"));
  if (!["STANDBY_SHORT", "STANDBY_LONG", "OFF"].includes(dutyType)) {
    return json({ detail: `unknown duty_type '${dutyType}'` }, 422);
  }
  const crewId = String(need(b.crew_id, "crew_id"));
  const day = String(need(b.date, "date"));
  const crew = await one<Record<string, unknown> | null>(
    db.from("crew").select("*").eq("id", crewId).eq("operator_id", user.operator_id).maybeSingle(),
  );
  if (!crew) return json({ detail: "crew not found" }, 422);
  // Replace any existing non-flight duty on this date.
  await db.from("flight_duty_periods").delete().eq("crew_id", crewId).eq("date", day).neq("type", "FDP");

  let row: Record<string, unknown>;
  if (dutyType === "OFF") {
    const start = `${day}T00:00:00Z`;
    row = {
      operator_id: user.operator_id, created_by_user_id: user.id, crew_id: crewId, date: day,
      report_time: start, off_duty_time: start, sectors_count: 0, flight_hours: 0, duty_hours: 0,
      type: "OFF", legality_state: "LEGAL", ftl_rules_applied: [],
    };
  } else {
    const startTime = String(need(b.start_time, "start_time"));
    const endTime = String(need(b.end_time, "end_time"));
    const start = new Date(`${day}T${startTime}Z`);
    let end = new Date(`${day}T${endTime}Z`);
    if (end <= start) end = new Date(end.getTime() + 86400000);
    const dutyH = Math.round(((end.getTime() - start.getTime()) / 3600000) * 100) / 100;
    row = {
      operator_id: user.operator_id, created_by_user_id: user.id, crew_id: crewId, date: day,
      report_time: start.toISOString(), off_duty_time: end.toISOString(), sectors_count: 0,
      flight_hours: 0, duty_hours: dutyH, type: "STANDBY", legality_state: "LEGAL",
      ftl_rules_applied: ["SIMPLIFIED_TS_PORT"],
    };
  }
  const created = await one(db.from("flight_duty_periods").insert(row).select().single());
  return json(dutyOut(created, crew), 201);
}

async function dutyDelete(user: DbUser, id: string): Promise<Response> {
  const existing = await one<Record<string, unknown> | null>(
    db.from("flight_duty_periods").select("id").eq("id", id).eq("operator_id", user.operator_id)
      .neq("type", "FDP").maybeSingle(),
  );
  if (!existing) return json({ detail: "duty not found" }, 404);
  await db.from("flight_duty_periods").delete().eq("id", id);
  return new Response(null, { status: 204 });
}

// ── leave & swaps ───────────────────────────────────────────────────────────

async function leave(user: DbUser, req: Request, url: URL): Promise<Response> {
  if (req.method === "GET") {
    let q = db.from("leave_requests").select("*").eq("operator_id", user.operator_id);
    const status = url.searchParams.get("status");
    if (status) q = q.eq("status", status);
    const rows = await one<Record<string, unknown>[]>(q.order("created_at", { ascending: false }));
    return json((rows ?? []).map(leaveOut));
  }
  requireWriter(user);
  const b = await readJson(req);
  const created = await one(
    db.from("leave_requests").insert({
      operator_id: user.operator_id, created_by_user_id: user.id, status: "PENDING",
      crew_id: need(b.crew_id, "crew_id"), type: need(b.type, "type"),
      date_from: need(b.date_from, "date_from"), date_to: need(b.date_to, "date_to"),
      note: b.note ?? null,
    }).select().single(),
  );
  await auditLog(user.operator_id, user.id, "SUBMIT_LEAVE", "leave_request", (created as { id: string }).id, null, b);
  return json(leaveOut(created), 201);
}

async function leaveDecide(user: DbUser, req: Request, id: string): Promise<Response> {
  requireWriter(user);
  const existing = await one<Record<string, unknown> | null>(
    db.from("leave_requests").select("*").eq("id", id).eq("operator_id", user.operator_id).maybeSingle(),
  );
  if (!existing) return json({ detail: "leave request not found" }, 404);
  const b = await readJson(req);
  const status = String(need(b.status, "status"));
  const updates: Record<string, unknown> = { status, approver_id: user.id };
  if (b.note !== undefined && b.note !== null) updates.note = b.note;
  const updated = await one(db.from("leave_requests").update(updates).eq("id", id).select().single());
  await auditLog(user.operator_id, user.id, `LEAVE_${status}`, "leave_request", id, leaveOut(existing), leaveOut(updated));
  return json(leaveOut(updated));
}

async function swaps(user: DbUser, req: Request, url: URL): Promise<Response> {
  if (req.method === "GET") {
    let q = db.from("swap_requests").select("*").eq("operator_id", user.operator_id);
    const status = url.searchParams.get("status");
    if (status) q = q.eq("status", status);
    const rows = await one<Record<string, unknown>[]>(q.order("created_at", { ascending: false }));
    return json((rows ?? []).map(swapOut));
  }
  requireWriter(user);
  const b = await readJson(req);
  const created = await one(
    db.from("swap_requests").insert({
      operator_id: user.operator_id, created_by_user_id: user.id, status: "PENDING",
      crew_id_initiator: need(b.crew_id_initiator, "crew_id_initiator"),
      crew_id_counterparty: need(b.crew_id_counterparty, "crew_id_counterparty"),
      fdp_or_sector_ref: need(b.fdp_or_sector_ref, "fdp_or_sector_ref"),
      reason: b.reason ?? null,
    }).select().single(),
  );
  await auditLog(user.operator_id, user.id, "SUBMIT_SWAP", "swap_request", (created as { id: string }).id, null, b);
  return json(swapOut(created), 201);
}

async function swapDecide(user: DbUser, req: Request, id: string): Promise<Response> {
  requireWriter(user);
  const existing = await one<Record<string, unknown> | null>(
    db.from("swap_requests").select("*").eq("id", id).eq("operator_id", user.operator_id).maybeSingle(),
  );
  if (!existing) return json({ detail: "swap request not found" }, 404);
  const b = await readJson(req);
  const status = String(need(b.status, "status"));
  const updated = await one(
    db.from("swap_requests").update({ status, approver_id: user.id }).eq("id", id).select().single(),
  );
  await auditLog(user.operator_id, user.id, `SWAP_${status}`, "swap_request", id, swapOut(existing), swapOut(updated));
  return json(swapOut(updated));
}

// ── users & settings ────────────────────────────────────────────────────────

async function usersRoute(user: DbUser, req: Request): Promise<Response> {
  if (req.method === "GET") {
    const rows = await one<Record<string, unknown>[]>(
      db.from("users").select("id, email, full_name, role, is_active")
        .eq("operator_id", user.operator_id).order("full_name"),
    );
    return json(rows ?? []);
  }
  requireAdmin(user);
  const b = await readJson(req);
  const email = String(need(b.email, "email"));
  const password = String(need(b.password, "password"));
  if (password.length < 8) return json({ detail: "password must be at least 8 characters" }, 422);
  const { data: existing } = await db.from("users").select("id").eq("email", email).maybeSingle();
  if (existing) return json({ detail: "a user with that email already exists" }, 409);
  const created = await one(
    db.from("users").insert({
      operator_id: user.operator_id, email, full_name: need(b.full_name, "full_name"),
      hashed_password: bcrypt.hashSync(password.slice(0, 72), 12),
      role: need(b.role, "role"), is_active: true,
    }).select("id, email, full_name, role, is_active").single(),
  );
  await auditLog(user.operator_id, user.id, "CREATE_USER", "user", (created as { id: string }).id, null, created);
  return json(created, 201);
}

async function userPatch(user: DbUser, req: Request, targetId: string): Promise<Response> {
  requireAdmin(user);
  const target = await one<Record<string, unknown> | null>(
    db.from("users").select("*").eq("id", targetId).eq("operator_id", user.operator_id).maybeSingle(),
  );
  if (!target) return json({ detail: "user not found" }, 404);
  const b = await readJson(req);
  if (targetId === user.id) {
    if ("role" in b && b.role !== "ADMIN") {
      return json({ detail: "you cannot remove your own administrator role" }, 409);
    }
    if (b.is_active === false) {
      return json({ detail: "you cannot deactivate your own account" }, 409);
    }
  }
  const updates: Record<string, unknown> = {};
  for (const k of ["full_name", "role", "is_active"]) if (k in b) updates[k] = b[k];
  const updated = await one(
    db.from("users").update(updates).eq("id", targetId).select("id, email, full_name, role, is_active").single(),
  );
  await auditLog(user.operator_id, user.id, "UPDATE_USER", "user", targetId, null, updated);
  return json(updated);
}

// deno-lint-ignore no-explicit-any
function operatorOut(o: any) {
  return {
    id: o.id, aoc_number: o.aoc_number, name: o.name, base: o.base, timezone: o.timezone,
    contact_email: o.contact_email, tier: o.tier, default_soft_weights: o.default_soft_weights ?? {},
  };
}

async function settingsOperator(user: DbUser, req: Request): Promise<Response> {
  const op = await one<Record<string, unknown> | null>(
    db.from("operators").select("*").eq("id", user.operator_id).maybeSingle(),
  );
  if (!op) return json({ detail: "operator not found" }, 404);
  if (req.method === "GET") return json(operatorOut(op));
  requireWriter(user);
  const b = await readJson(req);
  const updates: Record<string, unknown> = {};
  for (const k of ["name", "base", "timezone", "contact_email", "tier", "default_soft_weights"]) {
    if (k in b && b[k] !== null) updates[k] = b[k];
  }
  const updated = await one(db.from("operators").update(updates).eq("id", user.operator_id).select().single());
  await auditLog(user.operator_id, user.id, "UPDATE_OPERATOR", "operator", user.operator_id, operatorOut(op), operatorOut(updated));
  return json(operatorOut(updated));
}

async function settingsAccount(user: DbUser, req: Request): Promise<Response> {
  if (req.method === "GET") {
    return json({ id: user.id, email: user.email, full_name: user.full_name, role: user.role });
  }
  const b = await readJson(req);
  const fullName = String(need(b.full_name, "full_name"));
  const updated = await one(
    db.from("users").update({ full_name: fullName }).eq("id", user.id)
      .select("id, email, full_name, role").single(),
  );
  return json(updated);
}

async function changePassword(user: DbUser, req: Request): Promise<Response> {
  const b = await readJson(req);
  const current = String(need(b.current_password, "current_password"));
  const next = String(need(b.new_password, "new_password"));
  if (next.length < 8) return json({ detail: "password must be at least 8 characters" }, 422);
  if (!bcrypt.compareSync(current.slice(0, 72), user.hashed_password)) {
    return json({ detail: "current password is incorrect" }, 403);
  }
  await db.from("users").update({ hashed_password: bcrypt.hashSync(next.slice(0, 72), 12) }).eq("id", user.id);
  return new Response(null, { status: 204 });
}

// ── training ────────────────────────────────────────────────────────────────

async function typeRatings(user: DbUser): Promise<Response> {
  const [ratings, crews] = await Promise.all([
    one<Record<string, unknown>[]>(
      db.from("crew_type_ratings").select("*").eq("operator_id", user.operator_id).order("valid_until"),
    ),
    one<Record<string, unknown>[]>(
      db.from("crew").select("id, employee_no, first_name, last_name").eq("operator_id", user.operator_id),
    ),
  ]);
  const byId: Record<string, Record<string, unknown>> = {};
  for (const c of crews ?? []) byId[c.id as string] = c;
  const today = todayUTC();
  return json(
    (ratings ?? []).map((r) => {
      const c = byId[r.crew_id as string];
      const days = daysBetween(r.valid_until as string, today);
      return {
        id: r.id, crew_id: r.crew_id,
        employee_no: c?.employee_no ?? "—",
        crew_name: c ? `${c.first_name} ${c.last_name}` : "—",
        aircraft_type: r.aircraft_type, valid_from: r.valid_from, valid_until: r.valid_until,
        evidence_ref: r.evidence_ref, days_remaining: days, state: ragState(days),
      };
    }),
  );
}

async function addTypeRating(user: DbUser, req: Request, crewId: string): Promise<Response> {
  requireWriter(user);
  const b = await readJson(req);
  const validFrom = String(need(b.valid_from, "valid_from"));
  const validUntil = String(need(b.valid_until, "valid_until"));
  if (validUntil < validFrom) return json({ detail: "valid_until before valid_from" }, 422);
  const crew = await one<Record<string, unknown> | null>(
    db.from("crew").select("*").eq("id", crewId).eq("operator_id", user.operator_id).maybeSingle(),
  );
  if (!crew) return json({ detail: "crew not found" }, 404);
  const created = await one(
    db.from("crew_type_ratings").insert({
      operator_id: user.operator_id, created_by_user_id: user.id, crew_id: crewId,
      aircraft_type: String(need(b.aircraft_type, "aircraft_type")).trim().toUpperCase(),
      valid_from: validFrom, valid_until: validUntil, evidence_ref: b.evidence_ref ?? null,
    }).select().single(),
  );
  const r = created as Record<string, unknown>;
  await auditLog(user.operator_id, user.id, "ADD_TYPE_RATING", "crew_type_rating", r.id as string, null, b);
  const days = daysBetween(r.valid_until as string, todayUTC());
  return json({
    id: r.id, crew_id: crewId, employee_no: crew.employee_no,
    crew_name: `${crew.first_name} ${crew.last_name}`,
    aircraft_type: r.aircraft_type, valid_from: r.valid_from, valid_until: r.valid_until,
    evidence_ref: r.evidence_ref, days_remaining: days, state: ragState(days),
  }, 201);
}

async function deleteTypeRating(user: DbUser, id: string): Promise<Response> {
  requireWriter(user);
  const existing = await one<Record<string, unknown> | null>(
    db.from("crew_type_ratings").select("*").eq("id", id).eq("operator_id", user.operator_id).maybeSingle(),
  );
  if (!existing) return json({ detail: "type rating not found" }, 404);
  await db.from("crew_type_ratings").delete().eq("id", id);
  await auditLog(user.operator_id, user.id, "DELETE_TYPE_RATING", "crew_type_rating", id, {
    aircraft_type: existing.aircraft_type, crew_id: existing.crew_id,
  }, null);
  return new Response(null, { status: 204 });
}

async function recurrency(user: DbUser, url: URL): Promise<Response> {
  const withinDays = Math.min(365, Math.max(1, Number(url.searchParams.get("within_days") ?? 90)));
  const today = todayUTC();
  const horizon = new Date(today.getTime() + withinDays * 86400000);
  const [currencies, ratings, documents, crews] = await Promise.all([
    one<Record<string, unknown>[]>(db.from("crew_currencies").select("*").eq("operator_id", user.operator_id)),
    one<Record<string, unknown>[]>(db.from("crew_type_ratings").select("*").eq("operator_id", user.operator_id)),
    one<Record<string, unknown>[]>(
      db.from("crew_documents").select("*").eq("operator_id", user.operator_id).not("expiry_date", "is", null),
    ),
    one<Record<string, unknown>[]>(
      db.from("crew").select("id, employee_no, first_name, last_name").eq("operator_id", user.operator_id),
    ),
  ]);
  const byId: Record<string, Record<string, unknown>> = {};
  for (const c of crews ?? []) byId[c.id as string] = c;
  const items: Record<string, unknown>[] = [];
  const push = (crewId: string, kind: string, label: string, expires: string) => {
    if (new Date(expires + "T00:00:00Z") > horizon) return;
    const c = byId[crewId];
    const days = daysBetween(expires, today);
    items.push({
      crew_id: crewId,
      employee_no: c?.employee_no ?? "—",
      crew_name: c ? `${c.first_name} ${c.last_name}` : "—",
      kind, label, expires_date: expires, days_remaining: days, state: ragState(days),
    });
  };
  for (const cur of currencies ?? []) {
    push(cur.crew_id as string, "currency", cur.currency_type as string, cur.expires_date as string);
  }
  for (const r of ratings ?? []) {
    push(r.crew_id as string, "type_rating", `Type rating: ${r.aircraft_type}`, r.valid_until as string);
  }
  for (const d of documents ?? []) {
    const label = String(d.doc_type).replaceAll("_", " ").replace(/\w\S*/g, (w) => w[0].toUpperCase() + w.slice(1).toLowerCase());
    push(d.crew_id as string, "document", label, d.expiry_date as string);
  }
  items.sort((a, b) => (a.days_remaining as number) - (b.days_remaining as number));
  return json(items);
}

// ── roster ──────────────────────────────────────────────────────────────────

// deno-lint-ignore no-explicit-any
function sectorToInput(s: any): SectorInput & { block_hours: number } {
  return {
    sector_id: s.flight_no, date_local: s.date, std: s.std, sta: s.sta,
    aircraft_reg: s.aircraft_reg, aircraft_type: s.aircraft_type,
    block_hours: Math.round(((new Date(s.sta).getTime() - new Date(s.std).getTime()) / 3600000) * 100) / 100,
  };
}

async function rosterList(user: DbUser, url: URL): Promise<Response> {
  const dateFrom = need(url.searchParams.get("date_from"), "date_from");
  const dateTo = need(url.searchParams.get("date_to"), "date_to");
  const sectorsRows = await one<Record<string, unknown>[]>(
    db.from("sectors").select("*").eq("operator_id", user.operator_id)
      .gte("date", dateFrom).lte("date", dateTo).eq("status", "PUBLISHED"),
  );
  if (!sectorsRows?.length) return json([]);
  const sectorIds = sectorsRows.map((s) => s.id as string);
  const saRows = await one<Record<string, unknown>[]>(
    db.from("sector_assignments").select("*").in("sector_id", sectorIds),
  );
  const sectorsById: Record<string, Record<string, unknown>> = {};
  for (const s of sectorsRows) sectorsById[s.id as string] = s;
  const crewIds = [...new Set((saRows ?? []).map((a) => a.crew_id as string))];
  const crewsById: Record<string, Record<string, unknown>> = {};
  if (crewIds.length) {
    const { data: crews } = await db.from("crew").select("id, employee_no").in("id", crewIds);
    for (const c of crews ?? []) crewsById[c.id] = c;
  }
  const fdpLegality: Record<string, string> = {};
  if (crewIds.length) {
    const { data: fdps } = await db.from("flight_duty_periods").select("crew_id, date, legality_state")
      .eq("operator_id", user.operator_id).in("crew_id", crewIds).gte("date", dateFrom).lte("date", dateTo);
    for (const f of fdps ?? []) fdpLegality[`${f.crew_id}|${f.date}`] = f.legality_state;
  }

  type Bucket = {
    sector_ids: Set<string>; aircraft_type: string;
    CAPT?: string; FO?: string; CAPT_id?: string; FO_id?: string;
  };
  const byDd: Record<string, Bucket> = {};
  for (const sa of saRows ?? []) {
    const sector = sectorsById[sa.sector_id as string];
    if (!sector) continue;
    const key = `${sector.aircraft_reg}|${sector.date}`;
    const bucket = (byDd[key] ??= { sector_ids: new Set(), aircraft_type: "" });
    bucket.sector_ids.add(sector.flight_no as string);
    bucket.aircraft_type = sector.aircraft_type as string;
    const crew = crewsById[sa.crew_id as string];
    if (crew) {
      const role = sa.role_on_sector as "CAPT" | "FO";
      bucket[role] = crew.employee_no as string;
      bucket[`${role}_id`] ??= crew.id as string;
    }
  }
  const out = [];
  for (const key of Object.keys(byDd).sort()) {
    const [reg, day] = key.split("|");
    const b = byDd[key];
    if (!b.CAPT || !b.FO) continue;
    const worst = worstLegality([
      fdpLegality[`${b.CAPT_id}|${day}`] ?? null,
      fdpLegality[`${b.FO_id}|${day}`] ?? null,
    ]);
    out.push({
      duty_day_key: key, date_local: day, aircraft_reg: reg, aircraft_type: b.aircraft_type,
      sector_ids: [...b.sector_ids].sort(), captain_id: b.CAPT, fo_id: b.FO,
      legality_state: worst,
    });
  }
  return json(out);
}

async function autoGenerate(user: DbUser, req: Request): Promise<Response> {
  requireWriter(user);
  const started = Date.now();
  const b = await readJson(req);
  const from = String(need(b.horizon_from, "horizon_from"));
  const to = String(need(b.horizon_to, "horizon_to"));
  if (to < from) return json({ detail: "horizon_to before horizon_from" }, 422);

  const [sectorsRows, crews, ratings, leaveRows] = await Promise.all([
    one<Record<string, unknown>[]>(
      db.from("sectors").select("*").eq("operator_id", user.operator_id)
        .gte("date", from).lte("date", to).order("date").order("std"),
    ),
    one<Record<string, unknown>[]>(
      db.from("crew").select("*").eq("operator_id", user.operator_id).eq("active", true).in("role", ["CAPT", "FO"]),
    ),
    one<Record<string, unknown>[]>(db.from("crew_type_ratings").select("*").eq("operator_id", user.operator_id)),
    one<Record<string, unknown>[]>(
      db.from("leave_requests").select("*").eq("operator_id", user.operator_id).eq("status", "APPROVED"),
    ),
  ]);
  if (!sectorsRows?.length) {
    return json({
      result: {
        status: "NO_SECTORS", assignments: [], objective_value: null,
        unassigned_duty_days: [], diagnostics: { reason: "no routings in horizon" },
        elapsed_s: (Date.now() - started) / 1000,
      },
      sectors: [],
    });
  }

  // duty day = all sectors flown by one aircraft on one date
  const dutyDays: Record<string, Record<string, unknown>[]> = {};
  for (const s of sectorsRows) {
    (dutyDays[`${s.aircraft_reg}|${s.date}`] ??= []).push(s);
  }

  // qualification index: crew_id -> set of aircraft types with a rating valid through the horizon end
  const qualified: Record<string, Set<string>> = {};
  for (const r of ratings ?? []) {
    if ((r.valid_until as string) < to || (r.valid_from as string) > from) continue;
    (qualified[r.crew_id as string] ??= new Set()).add(r.aircraft_type as string);
  }
  const onLeave = (crewId: string, day: string) =>
    (leaveRows ?? []).some((l) =>
      l.crew_id === crewId && (l.date_from as string) <= day && day <= (l.date_to as string)
    );

  const captains = (crews ?? []).filter((c) => c.role === "CAPT");
  const fos = (crews ?? []).filter((c) => c.role === "FO");
  const dutyCount: Record<string, number> = {};
  const busy: Record<string, Set<string>> = {}; // date -> crew ids already flying

  // Greedy: fewest-duties-first among qualified, available crew. This is a
  // deliberate simplification of the OR-Tools CP-SAT optimiser (which cannot
  // run in the Deno edge runtime); fairness comes from the duty counter.
  const assignments = [];
  const unassigned: string[] = [];
  for (const key of Object.keys(dutyDays).sort()) {
    const daySectors = dutyDays[key];
    const [, day] = key.split("|");
    const acType = daySectors[0].aircraft_type as string;
    const busyToday = (busy[day] ??= new Set());
    const pick = (pool: Record<string, unknown>[]) =>
      pool
        .filter((c) =>
          qualified[c.id as string]?.has(acType) && !busyToday.has(c.id as string) &&
          !onLeave(c.id as string, day)
        )
        .sort((a, b) => (dutyCount[a.id as string] ?? 0) - (dutyCount[b.id as string] ?? 0))[0];
    const capt = pick(captains);
    const fo = pick(fos);
    if (!capt || !fo) {
      unassigned.push(key);
      continue;
    }
    busyToday.add(capt.id as string).add(fo.id as string);
    dutyCount[capt.id as string] = (dutyCount[capt.id as string] ?? 0) + 1;
    dutyCount[fo.id as string] = (dutyCount[fo.id as string] ?? 0) + 1;
    assignments.push({
      duty_day_key: key,
      date_local: day,
      aircraft_reg: daySectors[0].aircraft_reg,
      aircraft_type: acType,
      sector_ids: daySectors.map((s) => s.flight_no as string),
      captain_id: capt.employee_no,
      fo_id: fo.employee_no,
    });
  }

  return json({
    result: {
      status: assignments.length ? (unassigned.length ? "PARTIAL" : "FEASIBLE") : "INFEASIBLE",
      assignments,
      objective_value: null,
      unassigned_duty_days: unassigned,
      diagnostics: {
        engine: "greedy-ts",
        note: "TypeScript heuristic (fewest-duties-first); OR-Tools optimiser is not available in the edge runtime",
        duty_days: Object.keys(dutyDays).length,
      },
      elapsed_s: (Date.now() - started) / 1000,
    },
    sectors: sectorsRows.map(sectorToInput),
  });
}

async function rosterPublish(user: DbUser, req: Request): Promise<Response> {
  requireWriter(user);
  const b = await readJson(req);
  const payloadSectors = (b.sectors as SectorInput[]) ?? [];
  const payloadAssignments = (b.assignments as Record<string, unknown>[]) ?? [];
  if (!payloadSectors.length || !payloadAssignments.length) {
    return json({ detail: "sectors and assignments are required" }, 422);
  }

  // get-or-create sector rows, mark PUBLISHED
  const persisted: Record<string, Record<string, unknown>> = {}; // sector_id (flight_no) -> row
  for (const s of payloadSectors) {
    const { data: existing } = await db.from("sectors").select("*")
      .eq("operator_id", user.operator_id).eq("flight_no", s.sector_id).eq("date", s.date_local).maybeSingle();
    if (existing) {
      await db.from("sectors").update({ status: "PUBLISHED" }).eq("id", existing.id);
      persisted[s.sector_id + "|" + s.date_local] = { ...existing, status: "PUBLISHED" };
    } else {
      const created = await one(
        db.from("sectors").insert({
          operator_id: user.operator_id, created_by_user_id: user.id,
          flight_no: s.sector_id, date: s.date_local, origin: "TBD", destination: "TBD",
          std: s.std, sta: s.sta, aircraft_reg: s.aircraft_reg, aircraft_type: s.aircraft_type,
          status: "PUBLISHED",
        }).select().single(),
      );
      persisted[s.sector_id + "|" + s.date_local] = created as Record<string, unknown>;
    }
  }

  // crew lookup by employee_no
  const empNos = [...new Set(payloadAssignments.flatMap((a) => [a.captain_id as string, a.fo_id as string]))];
  const { data: crews } = await db.from("crew").select("id, employee_no")
    .eq("operator_id", user.operator_id).in("employee_no", empNos);
  const crewByEmp: Record<string, string> = {};
  for (const c of crews ?? []) crewByEmp[c.employee_no] = c.id;
  for (const e of empNos) {
    if (!crewByEmp[e]) return json({ detail: `unknown crew employee_no ${e}` }, 422);
  }

  // idempotent republish: clear superseded assignment + FDP rows
  const touchedSectorDbIds = Object.values(persisted).map((s) => s.id as string);
  const touchedDates = [...new Set(payloadAssignments.map((a) => a.date_local as string))];
  const touchedCrewIds = [...new Set(empNos.map((e) => crewByEmp[e]))];
  await db.from("sector_assignments").delete().in("sector_id", touchedSectorDbIds);
  await db.from("flight_duty_periods").delete().in("crew_id", touchedCrewIds).in("date", touchedDates).eq("type", "FDP");

  const sectorInputByKey: Record<string, SectorInput> = {};
  for (const s of payloadSectors) sectorInputByKey[s.sector_id + "|" + s.date_local] = s;

  let saCount = 0;
  let fdpCount = 0;
  const saInserts = [];
  const crewDaySectors: Record<string, SectorInput[]> = {}; // `${crewId}|${date}` -> sectors
  for (const a of payloadAssignments) {
    const captId = crewByEmp[a.captain_id as string];
    const foId = crewByEmp[a.fo_id as string];
    for (const sid of a.sector_ids as string[]) {
      const key = sid + "|" + a.date_local;
      const sectorRow = persisted[key];
      const sectorInput = sectorInputByKey[key];
      if (!sectorRow || !sectorInput) return json({ detail: `assignment references unknown sector_id '${sid}'` }, 422);
      for (const [crewId, role] of [[captId, "CAPT"], [foId, "FO"]] as const) {
        saInserts.push({
          operator_id: user.operator_id, created_by_user_id: user.id,
          sector_id: sectorRow.id, crew_id: crewId, role_on_sector: role,
        });
        saCount++;
        (crewDaySectors[`${crewId}|${a.date_local}`] ??= []).push(sectorInput);
      }
    }
  }
  if (saInserts.length) {
    const { error } = await db.from("sector_assignments").insert(saInserts);
    if (error) return json({ detail: error.message }, 422);
  }

  const fdpInserts = [];
  for (const key of Object.keys(crewDaySectors)) {
    const [crewId, day] = key.split("|");
    const f = computeFdp(crewDaySectors[key]);
    fdpInserts.push({
      operator_id: user.operator_id, created_by_user_id: user.id, crew_id: crewId, date: day,
      report_time: f.report.toISOString(), off_duty_time: f.off.toISOString(),
      sectors_count: f.sectors, flight_hours: f.flightH, duty_hours: f.dutyH,
      type: "FDP", legality_state: f.legality, ftl_rules_applied: ["SIMPLIFIED_TS_PORT"],
    });
    fdpCount++;
  }
  if (fdpInserts.length) {
    const { error } = await db.from("flight_duty_periods").insert(fdpInserts);
    if (error) return json({ detail: error.message }, 422);
  }

  await auditLog(user.operator_id, user.id, "PUBLISH_ROSTER", "roster", null, null, {
    horizon_from: b.horizon_from, horizon_to: b.horizon_to,
    sectors: payloadSectors.length, assignments: payloadAssignments.length,
    sector_assignments_created: saCount, flight_duty_periods_created: fdpCount,
  });
  return json({ roster_version: 1, sector_assignments_created: saCount, flight_duty_periods_created: fdpCount });
}

async function rosterAmend(user: DbUser, req: Request): Promise<Response> {
  requireWriter(user);
  const b = await readJson(req);
  const dutyDayKey = String(need(b.duty_day_key, "duty_day_key"));
  const [reg, day] = dutyDayKey.includes("|") ? dutyDayKey.split("|", 2) : [null, null];
  if (!reg || !day) return json({ detail: `malformed duty_day_key: '${dutyDayKey}'` }, 422);
  const reason = String(need(b.reason, "reason"));

  const sectorsRows = await one<Record<string, unknown>[]>(
    db.from("sectors").select("*").eq("operator_id", user.operator_id)
      .eq("aircraft_reg", reg).eq("date", day).eq("status", "PUBLISHED"),
  );
  if (!sectorsRows?.length) return json({ detail: `no published sectors found for '${dutyDayKey}'` }, 422);
  const sectorIds = sectorsRows.map((s) => s.id as string);

  const findCrew = async (empNo: string) => {
    const { data } = await db.from("crew").select("id, employee_no")
      .eq("operator_id", user.operator_id).eq("employee_no", empNo).maybeSingle();
    return data;
  };
  const capt = await findCrew(String(need(b.new_captain_employee_no, "new_captain_employee_no")));
  const fo = await findCrew(String(need(b.new_fo_employee_no, "new_fo_employee_no")));
  if (!capt || !fo) return json({ detail: "unknown crew employee_no" }, 422);

  // previous crew on these sectors → drop their FDPs for the day
  const { data: oldSas } = await db.from("sector_assignments").select("crew_id").in("sector_id", sectorIds);
  const oldCrewIds = [...new Set((oldSas ?? []).map((a) => a.crew_id as string))];
  await db.from("sector_assignments").delete().in("sector_id", sectorIds);
  if (oldCrewIds.length) {
    await db.from("flight_duty_periods").delete().in("crew_id", oldCrewIds).eq("date", day).eq("type", "FDP");
  }

  const inserts = [];
  for (const sid of sectorIds) {
    for (const [crewId, role] of [[capt.id, "CAPT"], [fo.id, "FO"]] as const) {
      inserts.push({
        operator_id: user.operator_id, created_by_user_id: user.id,
        sector_id: sid, crew_id: crewId, role_on_sector: role,
      });
    }
  }
  const { error } = await db.from("sector_assignments").insert(inserts);
  if (error) return json({ detail: error.message }, 422);

  const dayInputs = sectorsRows.map((s) => sectorToInput(s));
  const f = computeFdp(dayInputs);
  const fdpInserts = [capt.id, fo.id].map((crewId) => ({
    operator_id: user.operator_id, created_by_user_id: user.id, crew_id: crewId, date: day,
    report_time: f.report.toISOString(), off_duty_time: f.off.toISOString(),
    sectors_count: f.sectors, flight_hours: f.flightH, duty_hours: f.dutyH,
    type: "FDP", legality_state: f.legality, ftl_rules_applied: ["SIMPLIFIED_TS_PORT"],
  }));
  const { error: fdpErr } = await db.from("flight_duty_periods").insert(fdpInserts);
  if (fdpErr) return json({ detail: fdpErr.message }, 422);

  await auditLog(user.operator_id, user.id, "AMEND_ROSTER", "roster", null, null, {
    duty_day_key: dutyDayKey, new_captain: capt.employee_no, new_fo: fo.employee_no, reason,
  });
  return json({
    duty_day_key: dutyDayKey, captain_id: capt.id, fo_id: fo.id, legality_state: f.legality,
  });
}

// ── dispatcher ──────────────────────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  const url = new URL(req.url);
  let path = url.pathname.replace(/^\/api(?=\/|$)/, "") || "/healthz";
  if (path === "") path = "/healthz";

  if (req.method === "OPTIONS") return new Response(null, { status: 204 });

  if (path === "/healthz") return json({ status: "ok" });
  if (path === "/version") {
    return json({ name: "Ratiba", version: "supabase-port-0.2.0", phase: "supabase-2" });
  }
  if (path === "/readyz") {
    const { error } = await db.from("alembic_version").select("version_num").limit(1);
    return json(
      { status: error ? "not_ready" : "ready", checks: { database: error ? "down" : "ok" } },
      error ? 503 : 200,
    );
  }

  // CSRF double-submit for cookie-authenticated unsafe requests
  if (!CSRF_SAFE.has(req.method) && !CSRF_EXEMPT.has(path)) {
    const auth = req.headers.get("authorization") ?? "";
    const cookies = parseCookies(req);
    const hasAuthCookie = [ACCESS_COOKIE, REFRESH_COOKIE, PILOT_COOKIE].some((n) => n in cookies);
    if (!auth.toLowerCase().startsWith("bearer ") && hasAuthCookie) {
      const header = req.headers.get("x-csrf-token");
      if (!header || !cookies[CSRF_COOKIE] || header !== cookies[CSRF_COOKIE]) {
        return json({ detail: "CSRF token missing or invalid" }, 403);
      }
    }
  }

  try {
    if (path === "/api/v1/auth/login" && req.method === "POST") return await handleLogin(req);
    if (path === "/api/v1/auth/refresh" && req.method === "POST") return await handleRefresh(req);
    if (path === "/api/v1/auth/logout" && req.method === "POST") return await handleLogout(req);

    const user = await currentUser(req);
    if (!user) return json({ detail: "Not authenticated" }, 401);

    const m = req.method;
    const seg = path.split("/").filter(Boolean); // e.g. ["api","v1","crew","<id>","currency"]
    const isUuid = (s: string | undefined) =>
      !!s && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s);

    if (path === "/api/v1/auth/me" && m === "GET") return json(userOut(user));

    // crew
    if (path === "/api/v1/crew" && m === "GET") return await crewList(user, url);
    if (path === "/api/v1/crew" && m === "POST") return await crewCreate(user, req);
    if (path === "/api/v1/crew/currency/dashboard" && m === "GET") return await currencyDashboard(user);
    if (seg[2] === "crew" && isUuid(seg[3]) && seg.length === 4 && (m === "GET" || m === "PATCH")) {
      return await crewGetOrPatch(user, req, seg[3]);
    }
    if (seg[2] === "crew" && isUuid(seg[3]) && seg[4] === "currency" && (m === "GET" || m === "POST")) {
      return await crewCurrency(user, req, seg[3]);
    }

    // fleet
    if (path === "/api/v1/fleet" && (m === "GET" || m === "POST")) return await fleet(user, req);
    if (seg[2] === "fleet" && isUuid(seg[3]) && m === "PATCH") return await fleetPatch(user, req, seg[3]);

    // notices
    if (path === "/api/v1/notices" && (m === "GET" || m === "POST")) return await notices(user, req, url);
    if (seg[2] === "notices" && isUuid(seg[3]) && m === "PATCH") return await noticePatch(user, req, seg[3]);

    // sectors
    if (path === "/api/v1/sectors" && (m === "GET" || m === "POST")) return await sectors(user, req, url);
    if (path === "/api/v1/sectors/recurring" && m === "POST") return await sectorsRecurring(user, req);
    if (seg[2] === "sectors" && isUuid(seg[3]) && m === "DELETE") {
      requireWriter(user);
      return await sectorDelete(user, seg[3]);
    }

    // duties
    if (path === "/api/v1/duties" && (m === "GET" || m === "POST")) return await duties(user, req, url);
    if (seg[2] === "duties" && isUuid(seg[3]) && m === "DELETE") {
      requireWriter(user);
      return await dutyDelete(user, seg[3]);
    }

    // leave & swaps
    if (path === "/api/v1/leave" && (m === "GET" || m === "POST")) return await leave(user, req, url);
    if (seg[2] === "leave" && isUuid(seg[3]) && m === "PATCH") return await leaveDecide(user, req, seg[3]);
    if (path === "/api/v1/swap" && (m === "GET" || m === "POST")) return await swaps(user, req, url);
    if (seg[2] === "swap" && isUuid(seg[3]) && m === "PATCH") return await swapDecide(user, req, seg[3]);

    // users & settings
    if (path === "/api/v1/users" && (m === "GET" || m === "POST")) return await usersRoute(user, req);
    if (seg[2] === "users" && isUuid(seg[3]) && m === "PATCH") return await userPatch(user, req, seg[3]);
    if (path === "/api/v1/settings/operator" && (m === "GET" || m === "PATCH")) {
      return await settingsOperator(user, req);
    }
    if (path === "/api/v1/settings/account" && (m === "GET" || m === "PATCH")) {
      return await settingsAccount(user, req);
    }
    if (path === "/api/v1/settings/account/password" && m === "POST") return await changePassword(user, req);

    // training
    if (path === "/api/v1/training/type-ratings" && m === "GET") return await typeRatings(user);
    if (seg[2] === "training" && seg[3] === "crew" && isUuid(seg[4]) && seg[5] === "type-ratings" && m === "POST") {
      return await addTypeRating(user, req, seg[4]);
    }
    if (seg[2] === "training" && seg[3] === "type-ratings" && isUuid(seg[4]) && m === "DELETE") {
      return await deleteTypeRating(user, seg[4]);
    }
    if (path === "/api/v1/training/recurrency" && m === "GET") return await recurrency(user, url);

    // ftl & reference
    if (path === "/api/v1/ftl/limits" && m === "GET") {
      return json({ source: "baseline", regulation_ref: REGULATION_REF, limits: FTL_LIMITS });
    }
    if (path === "/api/v1/reference/aircraft-types" && m === "GET") {
      return json(
        AIRCRAFT_TYPES.map(([icao, manufacturer, model, category, typical_seats]) => ({
          icao, manufacturer, model, category, typical_seats,
          label: `${icao} — ${manufacturer} ${model}`,
        })),
      );
    }
    if (path === "/api/v1/reference/public-holidays" && m === "GET") {
      const from = url.searchParams.get("date_from") ?? `${new Date().getUTCFullYear()}-01-01`;
      const to = url.searchParams.get("date_to") ?? `${new Date().getUTCFullYear()}-12-31`;
      const out = [];
      for (let y = Number(from.slice(0, 4)); y <= Number(to.slice(0, 4)); y++) {
        for (const [md, name] of KE_HOLIDAYS) {
          const d = `${y}-${md}`;
          if (d >= from && d <= to) out.push({ country_code: "KE", date: d, name, is_variable: false });
        }
      }
      return json(out);
    }

    // roster
    if (path === "/api/v1/roster" && m === "GET") return await rosterList(user, url);
    if (path === "/api/v1/roster/auto-generate" && m === "POST") return await autoGenerate(user, req);
    if (path === "/api/v1/roster/publish" && m === "POST") return await rosterPublish(user, req);
    if (path === "/api/v1/roster/amend" && m === "POST") return await rosterAmend(user, req);

    return json({
      detail: "This feature is being migrated to the new backend (Supabase) and isn't available yet.",
    }, 501);
  } catch (e) {
    if (e instanceof ApiError) return json({ detail: e.message }, e.status);
    console.error("unhandled", e);
    return json({ detail: "internal error" }, 500);
  }
});
