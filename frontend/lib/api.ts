const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("aria_access_token");
}

export function saveToken(token: string): void {
  window.localStorage.setItem("aria_access_token", token);
}

export function clearToken(): void {
  window.localStorage.removeItem("aria_access_token");
}

export function deviceLabel(): string {
  if (typeof window === "undefined") return "Unknown device";
  const label = window.navigator.userAgent;
  return label.length > 120 ? label.slice(0, 117) + "..." : label;
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

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(0, "Network error — check your connection and try again.");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail ?? "ARIA request failed";
    if (response.status === 401 && token && !isAuthPage()) {
      clearToken();
      window.location.assign("/signin?reason=expired");
    }
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
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
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
    if (response.status === 401 && token && !isAuthPage()) {
      clearToken();
      window.location.assign("/signin?reason=expired");
    }
    throw new ApiError(response.status, detail);
  }
  return payload as T;
}
