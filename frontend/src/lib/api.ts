/**
 * Thin fetch wrapper for the crewing-officer dashboard.
 *
 * Primary auth is **httpOnly cookies** set by the backend (XSS-safe — JS never
 * sees the JWT): we send them with `credentials: "include"` and echo the
 * readable `rt_csrf` cookie in an `X-CSRF-Token` header (double-submit CSRF).
 *
 * Fallback: in some contexts the browser won't round-trip the cookies — most
 * notably the Claude Code web preview, which embeds the app in a cross-site
 * iframe where third-party cookies are blocked. The backend also returns the
 * token pair in the login/refresh *body*, so we keep them **in memory** (never
 * localStorage — that would reintroduce the XSS-exfiltration risk) and send the
 * access token as a `Bearer` header. Cookies are preferred when they work; the
 * in-memory copy just keeps a cross-site session alive for the page's lifetime
 * (lost on refresh, which is acceptable for the preview).
 */

const CSRF_COOKIE = "rt_csrf";
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

// In-memory token fallback (module-scoped; not persisted).
let memAccess: string | null = null;
let memRefresh: string | null = null;

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
  const value = match?.[1];
  return value !== undefined ? decodeURIComponent(value) : null;
}

/**
 * Session helpers. A session exists if either the readable CSRF cookie is
 * present (cookie auth) or we hold an in-memory access token (cross-site
 * fallback).
 */
export const session = {
  isAuthed: (): boolean => readCookie(CSRF_COOKIE) !== null || memAccess !== null,
  csrf: (): string | null => readCookie(CSRF_COOKIE),
  /** Best-effort local clear of the cookie marker + in-memory tokens. */
  clear: (): void => {
    document.cookie = `${CSRF_COOKIE}=; Max-Age=0; path=/`;
    memAccess = null;
    memRefresh = null;
  },
};

function withCsrf(headers: Headers, method: string): void {
  if (UNSAFE_METHODS.has(method.toUpperCase())) {
    const csrf = session.csrf();
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }
}

/** Add the in-memory access token as a Bearer header when we have one. */
function withBearer(headers: Headers): void {
  if (memAccess && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${memAccess}`);
  }
}

/**
 * Raw, credentialed fetch for blob downloads and file uploads — adds the auth
 * cookies, the Bearer fallback, and the CSRF header but leaves body/response
 * handling to the caller.
 */
export function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers ?? {});
  withCsrf(headers, init.method ?? "GET");
  withBearer(headers);
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

type TokenPair = { access_token?: string; refresh_token?: string };

/** Capture the token pair from a login/refresh response body into memory. */
async function captureTokens(resp: Response): Promise<void> {
  try {
    const body = (await resp.clone().json()) as TokenPair;
    if (body.access_token) memAccess = body.access_token;
    if (body.refresh_token) memRefresh = body.refresh_token;
  } catch {
    /* non-JSON or empty — ignore */
  }
}

/**
 * Rotate the session. Prefers the cookie-based refresh; if we're running on the
 * in-memory fallback (cookies blocked), sends the stored refresh token in the
 * body. Returns true on success and updates the in-memory tokens.
 */
async function refreshAccess(): Promise<boolean> {
  const headers = new Headers();
  withCsrf(headers, "POST");
  const reqInit: RequestInit = { method: "POST", headers, credentials: "include" };
  if (memRefresh) {
    headers.set("Content-Type", "application/json");
    reqInit.body = JSON.stringify({ refresh_token: memRefresh });
  }
  const resp = await fetch("/api/v1/auth/refresh", reqInit);
  if (resp.ok) await captureTokens(resp);
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
  if (!_skipAuth) withBearer(headers);

  let resp = await fetch(path, { ...rest, headers, credentials: "include" });
  if (resp.status === 401 && !_skipAuth) {
    if (await refreshAccess()) {
      // Session rotated; rebuild headers (CSRF + Bearer may have changed) and retry.
      const retryHeaders = new Headers(rest.headers ?? {});
      if (rest.body && !retryHeaders.has("Content-Type")) {
        retryHeaders.set("Content-Type", "application/json");
      }
      withCsrf(retryHeaders, method);
      withBearer(retryHeaders);
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
  // The backend sets httpOnly session cookies AND returns the token pair in the
  // body. We capture the pair in memory so the session also works where cookies
  // can't round-trip (cross-site preview iframe / blocked third-party cookies).
  const resp = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    credentials: "include",
  });
  if (!resp.ok) {
    let body: unknown = null;
    try {
      body = await resp.json();
    } catch {
      body = await resp.text();
    }
    throw new ApiError(resp.status, body);
  }
  await captureTokens(resp);
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
