/** Pilot session — separate from the crewing-officer session in lib/auth.tsx.
 *
 * The pilot JWT lives in an httpOnly `rt_pilot` cookie (XSS-safe), set by
 * `/auth/pilot-pair`. Only the non-sensitive display profile is kept in
 * localStorage, as the "this device is paired" marker. */

import { authFetch, api } from "./api";
import { safeStorage } from "./safeStorage";

const PILOT_PROFILE_KEY = "ratiba.pilot_profile";

export type PilotProfile = {
  crew_id: string;
  employee_no: string;
  role: "CAPT" | "FO" | "SO" | "PURSER" | "CABIN_CREW" | "ENGINEER";
  operator_id: string;
};

export const pilotStore = {
  getProfile: (): PilotProfile | null => {
    const raw = safeStorage.get(PILOT_PROFILE_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as PilotProfile;
    } catch {
      return null;
    }
  },
  set: (profile: PilotProfile) => {
    safeStorage.set(PILOT_PROFILE_KEY, JSON.stringify(profile));
  },
  clear: () => {
    safeStorage.remove(PILOT_PROFILE_KEY);
    // Best-effort clear of the readable CSRF marker; the server expires the
    // httpOnly pilot cookie on its own schedule / on a 401.
    document.cookie = "rt_csrf=; Max-Age=0; path=/";
  },
};

type PairResponse = {
  pilot_token: string;
  crew_id: string;
  employee_no: string;
  role: "CAPT" | "FO" | "SO" | "PURSER" | "CABIN_CREW" | "ENGINEER";
  operator_id: string;
};

// In-memory pilot token (never persisted). Auth prefers the httpOnly rt_pilot
// cookie; this Bearer fallback keeps the session alive where the cookie can't
// round-trip — the cross-site preview iframe with third-party cookies blocked.
let memPilotToken: string | null = null;

export async function pilotPair(code: string): Promise<PilotProfile> {
  // The pairing response sets the httpOnly pilot cookie AND returns the token in
  // the body; we keep the token in memory as a cross-site fallback (cookies
  // preferred when they work) and the non-sensitive profile in localStorage.
  const body = await api<PairResponse>("/api/v1/auth/pilot-pair", {
    method: "POST",
    body: JSON.stringify({ code }),
    skipAuth: true,
  });
  memPilotToken = body.pilot_token;
  const profile: PilotProfile = {
    crew_id: body.crew_id,
    employee_no: body.employee_no,
    role: body.role,
    operator_id: body.operator_id,
  };
  pilotStore.set(profile);
  return profile;
}

/** Call a pilot-scoped endpoint — auth rides on the httpOnly cookie + CSRF,
 * with an in-memory Bearer fallback for cookie-blocked (cross-site) contexts. */
export async function pilotApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers ?? {});
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (memPilotToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${memPilotToken}`);
  }
  const resp = await authFetch(path, { ...init, headers });
  if (resp.status === 401) {
    memPilotToken = null;
    pilotStore.clear();
    throw new Error("Pilot session expired — please re-pair.");
  }
  if (!resp.ok) {
    let body: unknown = null;
    try {
      body = await resp.json();
    } catch {
      body = await resp.text();
    }
    const detail =
      typeof body === "object" && body && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `HTTP ${resp.status}`;
    throw new Error(detail);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}
