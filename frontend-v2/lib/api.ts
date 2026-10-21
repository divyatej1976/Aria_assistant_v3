const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const CSRF_COOKIE = "aria_csrf";

export function clearToken(): void {
  if (typeof window === "undefined") return;
  // Mirror the attributes the server sets (no Domain=, Path=/,
  // SameSite=Strict). Adding domain= would create a mismatched cookie and
  // the delete would silently no-op.
  window.document.cookie = `${CSRF_COOKIE}=; Max-Age=0; Path=/; SameSite=Strict`;
}

export function deviceLabel(): string {
  if (typeof window === "undefined") return "Unknown device";
  const label = window.navigator.userAgent;
  return label.length > 120 ? label.slice(0, 117) + "..." : label;
}

function getCookie(name: string): string | null {
  if (typeof window === "undefined") return null;
  const match = window.document.cookie.match(
    new RegExp(`(?:^|; )${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}=([^;]*)`),
  );
  return match ? decodeURIComponent(match[1]) : null;
}

function csrfHeaders(method: string): Record<string, string> {
  if (method === "GET" || method === "HEAD" || method === "OPTIONS") return {};
  const token = getCookie(CSRF_COOKIE);
  return token ? { "X-CSRF-Token": token } : {};
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// The HttpOnly session cookie is unreadable here; the CSRF cookie is issued
// alongside it with the same max-age, so it stands in for "signed in".
function hasSessionCookie(): boolean {
  return getCookie(CSRF_COOKIE) !== null;
}

function isPublicPath(): boolean {
  if (typeof window === "undefined") return true;
  const path = window.location.pathname;
  return (
    path === "/" ||
    path.startsWith("/signin") ||
    path.startsWith("/signup") ||
    path.startsWith("/reset-password") ||
    path.startsWith("/verify-email")
  );
}

async function handleAuthFailure(status: number): Promise<void> {
  // Only bounce a real session to sign-in. Anonymous visitors on public pages
  // (landing, auth screens) must never be redirected by an API 401.
  if (status === 401 && !isPublicPath() && hasSessionCookie()) {
    clearToken();
    // Full reload is intentional: it clears all client state on session expiry.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign("/signin?reason=expired");
  }
}

const API_TIMEOUT_MS = 120_000;

function timeoutSignal(init?: RequestInit): AbortSignal | undefined {
  const timeout = AbortSignal.timeout(API_TIMEOUT_MS);
  return init?.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
}

function isTimeoutError(err: unknown): boolean {
  return err instanceof DOMException && err.name === "TimeoutError";
}

/** POST and read a reply that streams back as one JSON object per line (NDJSON).
 * Each object goes to onEvent as it arrives; errors before the stream starts throw like api(). */
export async function apiStream(path: string, body: unknown, onEvent: (event: Record<string, unknown>) => void,
  signal?: AbortSignal): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      body: JSON.stringify(body),
      signal,
      credentials: "include",
      headers: { "Content-Type": "application/json", ...csrfHeaders("POST") },
    });
  } catch (err) {
    if (signal?.aborted) throw err;
    throw new ApiError(0, "Couldn’t reach ARIA’s server. Check your connection, then retry.");
  }
  if (!response.ok || !response.body) {
    const payload = await response.json().catch(() => ({}));
    await handleAuthFailure(response.status);
    throw new ApiError(response.status, (payload as { detail?: string }).detail ?? "ARIA request failed");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffered = "";
  for (;;) {
    const { done, value } = await reader.read();
    buffered += decoder.decode(value, { stream: !done });
    const lines = buffered.split("\n");
    buffered = done ? "" : lines.pop() ?? "";
    for (const line of lines) if (line.trim()) onEvent(JSON.parse(line));
    if (done) return;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method ?? "GET";
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      signal: timeoutSignal(init),
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...csrfHeaders(method),
        ...(init.headers ?? {}),
      },
    });
  } catch (err) {
    if (isTimeoutError(err)) {
      throw new ApiError(0, "Request timed out — check your connection and retry.");
    }
    throw new ApiError(0, "Couldn’t reach ARIA’s server. Check your connection, then retry.");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = (payload as { detail?: string }).detail ?? "ARIA request failed";
    await handleAuthFailure(response.status);
    throw new ApiError(response.status, detail);
  }
  return payload as T;
}

export async function apiFormData<T>(path: string, formData: FormData, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    const { signal: _ignored, ...restInit } = init;
    void _ignored;
    response = await fetch(`${API_URL}${path}`, {
      ...restInit,
      method: "POST",
      credentials: "include",
      headers: csrfHeaders("POST"),
      body: formData,
      signal: timeoutSignal(init),
    });
  } catch (err) {
    if (isTimeoutError(err)) {
      throw new ApiError(0, "Request timed out — check your connection and retry.");
    }
    throw new ApiError(0, "Couldn’t reach ARIA’s server. Check your connection, then retry.");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = (payload as { detail?: string }).detail ?? "ARIA request failed";
    await handleAuthFailure(response.status);
    throw new ApiError(response.status, detail);
  }
  return payload as T;
}

export async function apiBlob(path: string, init: RequestInit = {}): Promise<Blob> {
  let response: Response;
  try {
    const { signal: _ignored, ...restInit } = init;
    void _ignored;
    response = await fetch(`${API_URL}${path}`, {
      ...restInit,
      credentials: "include",
      signal: timeoutSignal(init),
    });
  } catch (err) {
    if (isTimeoutError(err)) {
      throw new ApiError(0, "Request timed out — check your connection and retry.");
    }
    throw new ApiError(0, "Couldn’t reach ARIA’s server. Check your connection, then retry.");
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = (payload as { detail?: string }).detail ?? "ARIA request failed";
    await handleAuthFailure(response.status);
    throw new ApiError(response.status, detail);
  }
  return response.blob();
}

// The host caps a request body (Vercel: 4.5 MB), so bigger files go up in pieces first.
const UPLOAD_PIECE_BYTES = 4 * 1024 * 1024;

async function uploadPieces(file: File | Blob): Promise<string> {
  const uploadId = crypto.randomUUID();
  for (let start = 0, seq = 0; start < file.size; start += UPLOAD_PIECE_BYTES, seq += 1) {
    let response: Response;
    try {
      response = await fetch(`${API_URL}/api/v1/resources/uploads/${uploadId}/${seq}`, {
        method: "PUT", signal: timeoutSignal(), credentials: "include",
        headers: { "Content-Type": "application/octet-stream", ...csrfHeaders("PUT") },
        body: file.slice(start, start + UPLOAD_PIECE_BYTES),
      });
    } catch {
      throw new ApiError(0, "The upload was interrupted. Check your connection, then retry.");
    }
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      await handleAuthFailure(response.status);
      throw new ApiError(response.status, (payload as { detail?: string }).detail ?? "Upload failed");
    }
  }
  return uploadId;
}

export async function apiUpload<T>(path: string, file: File | Blob, contentType: string): Promise<T> {
  const method = "POST";
  if (file.size > UPLOAD_PIECE_BYTES) {
    const uploadId = await uploadPieces(file);
    path += `${path.includes("?") ? "&" : "?"}upload_id=${uploadId}`;
    file = new Blob([]);
  }
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      signal: timeoutSignal(),
      credentials: "include",
      headers: {
        "Content-Type": contentType,
        ...csrfHeaders(method),
      },
      body: file,
    });
  } catch (err) {
    if (isTimeoutError(err)) {
      throw new ApiError(0, "Upload timed out — check your connection and retry.");
    }
    throw new ApiError(0, "Couldn’t reach ARIA’s server, so the file was not uploaded. Check your connection, then retry.");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = (payload as { detail?: string }).detail ?? "Upload failed";
    await handleAuthFailure(response.status);
    throw new ApiError(response.status, detail);
  }
  return payload as T;
}
