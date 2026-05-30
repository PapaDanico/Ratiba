/**
 * Thin fetch wrapper for the crewing-officer dashboard.
 *
 * Browser sessions authenticate with **httpOnly cookies** set by the backend
 * (defence against XSS token theft — JS never sees the JWT). This client just
 * sends them (`credentials: "include"`) and, on unsafe requests, echoes the
 * readable `rt_csrf` cookie in an `X-CSRF-Token` header (double-submit CSRF).
 */

const CSRF_COOKIE = "rt_csrf";
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
  const value = match?.[1];
  return value !== undefined ? decodeURIComponent(value) : null;
}

/**
 * Session helpers. The httpOnly auth cookies are invisible to JS, so the
 * presence of the *readable* CSRF cookie is our "a session exists" signal.
 */
export const session = {
  isAuthed: (): boolean => readCookie(CSRF_COOKIE) !== null,
  csrf: (): string | null => readCookie(CSRF_COOKIE),
  /** Best-effort local clear; the server also expires the cookies on logout. */
  clear: (): void => {
    document.cookie = `${CSRF_COOKIE}=; Max-Age=0; path=/`;
  },
};

function withCsrf(headers: Headers, method: string): void {
  if (UNSAFE_METHODS.has(method.toUpperCase())) {
    const csrf = session.csrf();
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }
}

/**
 * Raw, credentialed fetch for blob downloads and file uploads — adds the auth
 * cookies and CSRF header but leaves body/response handling to the caller.
 */
export function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers ?? {});
  withCsrf(headers, init.method ?? "GET");
  return fetch(path, { ...init, headers, credentials: "include" });
}

function messageFromBody(status: number, body: unknown): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors return `detail` as a list of {loc, msg, ...}.
    if (Array.isArray(detail)) {
      const msgs = detail
        .map((d) =>
          typeof d === "object" && d !== null && "msg" in d
            ? String((d as { msg: unknown }).msg)
            : String(d),
        )
        .filter(Boolean);
      if (msgs.length) return msgs.join("; ");
    }
  }
  return `HTTP ${status}`;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(messageFromBody(status, body));
    this.name = "ApiError";
  }
}

/** Rotate the access cookie via the refresh cookie. Returns true on success. */
async function refreshAccess(): Promise<boolean> {
  const headers = new Headers();
  withCsrf(headers, "POST");
  const resp = await fetch("/api/v1/auth/refresh", {
    method: "POST",
    headers,
    credentials: "include",
  });
  return resp.ok;
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit & { skipAuth?: boolean } = {},
): Promise<T> {
  const { skipAuth: _skipAuth, ...rest } = init;
  const method = rest.method ?? "GET";
  const headers = new Headers(rest.headers ?? {});
  if (rest.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  withCsrf(headers, method);

  let resp = await fetch(path, { ...rest, headers, credentials: "include" });
  if (resp.status === 401 && !_skipAuth) {
    if (await refreshAccess()) {
      // The access cookie (and CSRF) rotated; rebuild the CSRF header and retry.
      const retryHeaders = new Headers(rest.headers ?? {});
      if (rest.body && !retryHeaders.has("Content-Type")) {
        retryHeaders.set("Content-Type", "application/json");
      }
      withCsrf(retryHeaders, method);
      resp = await fetch(path, { ...rest, headers: retryHeaders, credentials: "include" });
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

export async function login(email: string, password: string): Promise<void> {
  // Tokens are returned in the body too, but the browser ignores them — the
  // backend has set the httpOnly session cookies on this response.
  await api("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
    skipAuth: true,
  });
}

export function logout(): void {
  // Best-effort server-side revocation. The CSRF marker must stay readable until
  // the request is actually dispatched: clearing it synchronously races the
  // keepalive fetch and strips the double-submit cookie (leaving only the
  // header), which the server then rejects with 403 — silently skipping
  // revocation. The logout *response* clears all cookies; we only drop the
  // local marker once the request has settled.
  const headers = new Headers();
  withCsrf(headers, "POST");
  void fetch("/api/v1/auth/logout", {
    method: "POST",
    headers,
    credentials: "include",
    keepalive: true,
  })
    .catch(() => {})
    .finally(() => session.clear());
}
