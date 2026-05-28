/** Pilot session — separate from the crewing-officer session in lib/auth.tsx. */

import { api } from "./api";

const PILOT_TOKEN_KEY = "ratiba.pilot_token";
const PILOT_PROFILE_KEY = "ratiba.pilot_profile";

export type PilotProfile = {
  crew_id: string;
  employee_no: string;
  role: "CAPT" | "FO" | "SO";
  operator_id: string;
};

export const pilotStore = {
  getToken: (): string | null => localStorage.getItem(PILOT_TOKEN_KEY),
  getProfile: (): PilotProfile | null => {
    const raw = localStorage.getItem(PILOT_PROFILE_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as PilotProfile;
    } catch {
      return null;
    }
  },
  set: (token: string, profile: PilotProfile) => {
    localStorage.setItem(PILOT_TOKEN_KEY, token);
    localStorage.setItem(PILOT_PROFILE_KEY, JSON.stringify(profile));
  },
  clear: () => {
    localStorage.removeItem(PILOT_TOKEN_KEY);
    localStorage.removeItem(PILOT_PROFILE_KEY);
  },
};

type PairResponse = {
  pilot_token: string;
  crew_id: string;
  employee_no: string;
  role: "CAPT" | "FO" | "SO";
  operator_id: string;
};

export async function pilotPair(code: string): Promise<PilotProfile> {
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
  pilotStore.set(body.pilot_token, profile);
  return profile;
}

/** Call a pilot-scoped endpoint with the stored pilot token. */
export async function pilotApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = pilotStore.getToken();
  const headers = new Headers(init.headers ?? {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const resp = await fetch(path, { ...init, headers });
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
