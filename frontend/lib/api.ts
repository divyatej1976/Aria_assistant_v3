const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const CSRF_COOKIE = "aria_csrf";
const TOKEN_KEY = "aria_access_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function saveToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
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

function isAuthPage(): boolean {
  if (typeof window === "undefined") return false;
  const path = window.location.pathname;
  return path.startsWith("/signin") || path.startsWith("/signup");
}

async function handleAuthFailure(status: number): Promise<void> {
  if (status === 401 && getToken() && !isAuthPage()) {
    clearToken();
    window.location.assign("/signin?reason=expired");
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const method = init.method ?? "GET";
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...csrfHeaders(method),
        ...(init.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(0, "Network error — check your connection and try again.");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail ?? "ARIA request failed";
    await handleAuthFailure(response.status);
    throw new ApiError(response.status, detail);
  }
  return payload as T;
}

export async function apiBinary<T>(
  path: string,
  method: string,
  body: BodyInit,
  contentType: string,
): Promise<T> {
  const token = getToken();
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      credentials: "include",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...csrfHeaders(method),
        "Content-Type": contentType,
      },
      body,
    });
  } catch {
    throw new ApiError(0, "Network error — check your connection and try again.");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail ?? "ARIA request failed";
    await handleAuthFailure(response.status);
    throw new ApiError(response.status, detail);
  }
  return payload as T;
}

export async function apiFormData<T>(path: string, formData: FormData): Promise<T> {
  const token = getToken();
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      credentials: "include",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...csrfHeaders("POST"),
      },
      body: formData,
    });
  } catch {
    throw new ApiError(0, "Network error — check your connection and try again.");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail ?? "ARIA request failed";
    await handleAuthFailure(response.status);
    throw new ApiError(response.status, detail);
  }
  return payload as T;
}

export async function apiBlob(path: string): Promise<Blob> {
  const token = getToken();
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      credentials: "include",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    throw new ApiError(0, "Network error — check your connection and try again.");
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail ?? "ARIA request failed";
    await handleAuthFailure(response.status);
    throw new ApiError(response.status, detail);
  }
  return response.blob();
}
