/** Pilot session — separate from the crewing-officer session in lib/auth.tsx.
 *
 * The pilot JWT lives in an httpOnly `rt_pilot` cookie (XSS-safe), set by
 * `/auth/pilot-pair`. Only the non-sensitive display profile is kept in
 * localStorage, as the "this device is paired" marker. */

import { authFetch, api } from "./api";

const PILOT_PROFILE_KEY = "ratiba.pilot_profile";

export type PilotProfile = {
  crew_id: string;
  employee_no: string;
  role: "CAPT" | "FO" | "SO" | "PURSER" | "CABIN_CREW" | "ENGINEER";
  operator_id: string;
};

export const pilotStore = {
  getProfile: (): PilotProfile | null => {
    const raw = localStorage.getItem(PILOT_PROFILE_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as PilotProfile;
    } catch {
      return null;
    }
  },
  set: (profile: PilotProfile) => {
    localStorage.setItem(PILOT_PROFILE_KEY, JSON.stringify(profile));
  },
  clear: () => {
    localStorage.removeItem(PILOT_PROFILE_KEY);
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

export async function pilotPair(code: string): Promise<PilotProfile> {
  // The pairing response also sets the httpOnly pilot cookie; we only keep the
  // display profile (pilot_token in the body is ignored by the browser).
  const body = await api<PairResponse>("/api/v1/auth/pilot-pair", {
    method: "POST",
    body: JSON.stringify({ code }),
    skipAuth: true,
  });
  const profile: PilotProfile = {
    crew_id: body.crew_id,
    employee_no: body.employee_no,
    role: body.role,
    operator_id: body.operator_id,
  };
  pilotStore.set(profile);
  return profile;
}

/** Call a pilot-scoped endpoint — auth rides on the httpOnly cookie + CSRF. */
export async function pilotApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers ?? {});
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const resp = await authFetch(path, { ...init, headers });
  if (resp.status === 401) {
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
