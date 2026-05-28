/**
 * Thin fetch wrapper with bearer token + auto-refresh.
 *
 * Tokens live in localStorage. Production migrates to httpOnly cookies once
 * the dashboard's deployment shape is fixed in Phase 6.
 */

const ACCESS_KEY = "ratiba.access_token";
const REFRESH_KEY = "ratiba.refresh_token";

export const tokenStore = {
  getAccess: (): string | null => localStorage.getItem(ACCESS_KEY),
  getRefresh: (): string | null => localStorage.getItem(REFRESH_KEY),
  set: (access: string, refresh?: string) => {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(
      typeof body === "object" && body && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `HTTP ${status}`,
    );
    this.name = "ApiError";
  }
}

async function refreshAccess(): Promise<string | null> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return null;
  const resp = await fetch("/api/v1/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!resp.ok) return null;
  const body = (await resp.json()) as { access_token: string };
  tokenStore.set(body.access_token);
  return body.access_token;
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit & { skipAuth?: boolean } = {},
): Promise<T> {
  const { skipAuth, ...rest } = init;
  const headers = new Headers(rest.headers ?? {});
  if (rest.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!skipAuth) {
    const token = tokenStore.getAccess();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  let resp = await fetch(path, { ...rest, headers });
  if (resp.status === 401 && !skipAuth) {
    const fresh = await refreshAccess();
    if (fresh) {
      headers.set("Authorization", `Bearer ${fresh}`);
      resp = await fetch(path, { ...rest, headers });
    }
  }
  if (!resp.ok) {
    let body: unknown = null;
    try {
      body = await resp.json();
    } catch {
      body = await resp.text();
    }
    throw new ApiError(resp.status, body);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export async function login(
  email: string,
  password: string,
): Promise<{ access_token: string; refresh_token: string }> {
  const body = await api<{ access_token: string; refresh_token: string }>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
    skipAuth: true,
  });
  tokenStore.set(body.access_token, body.refresh_token);
  return body;
}

export function logout(): void {
  tokenStore.clear();
}
