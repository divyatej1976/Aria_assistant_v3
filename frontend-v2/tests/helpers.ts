import { expect, type APIResponse, type Page, request } from "@playwright/test";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

export type TestUser = { email: string; password: string; name: string };

/** Read the currently selected context id from localStorage (set by useActiveContext). */
export async function activeContextId(page: Page): Promise<string> {
  const id = await page.evaluate(() => window.localStorage.getItem("aria_active_context"));
  expect(id, "no active context in localStorage").toBeTruthy();
  return id!;
}

/** Minimal authenticated API surface with CSRF echo on state changes. */
export type AuthedApi = {
  get: (url: string) => Promise<APIResponse>;
  post: (url: string, options?: { data?: unknown }) => Promise<APIResponse>;
  put: (url: string, options?: { data?: unknown }) => Promise<APIResponse>;
  dispose: () => Promise<void>;
};

/** Cookie-authenticated API client that echoes the CSRF token on state changes. */
export async function authedApi(user: TestUser): Promise<AuthedApi> {
  const ctx = await request.newContext({ baseURL: API });
  const res = await ctx.post("/api/v1/auth/login", {
    data: { email: user.email, password: user.password, device_label: "playwright" },
  });
  expect(res.ok(), `login failed: ${res.status()} ${await res.text()}`).toBe(true);
  const csrf = res
    .headersArray()
    .filter((h) => h.name.toLowerCase() === "set-cookie" && h.value.startsWith("aria_csrf="))
    .map((h) => /aria_csrf=([^;]+)/.exec(h.value)?.[1])
    .find(Boolean);
  return {
    get: (url) => ctx.get(url),
    post: (url, options = {}) =>
      ctx.post(url, { ...options, headers: csrf ? { "X-CSRF-Token": csrf } : undefined }),
    put: (url, options = {}) =>
      ctx.put(url, { ...options, headers: csrf ? { "X-CSRF-Token": csrf } : undefined }),
    dispose: () => ctx.dispose(),
  };
}

/** Seed a text resource so the context has "ready study material" (needed for assessment generation). */
export async function seedResource(api: AuthedApi, contextId: string): Promise<string> {
  const res = await api.post("/api/v1/resources/text", {
    data: {
      context_id: contextId,
      title: "Python Functions Basics",
      text: "A function is a reusable block of code. def defines a function. "
        + "Arguments are passed when calling. A function returns a value with return. "
        + "Loops repeat a block while a condition holds. Python uses indentation to group statements.",
    },
  });
  if (res.status() === 409 || res.status() === 422) {
    const body = await res.json().catch(() => ({}));
    const list = await api.get(`/api/v1/resources?context_id=${contextId}`).then((r) => r.json());
    if (Array.isArray(list) && list.length) return list[0].id;
    expect(res.ok(), `seedResource failed: ${res.status()} ${JSON.stringify(body)}`).toBe(true);
  }
  expect(res.ok(), `seedResource failed: ${res.status()} ${await res.text()}`).toBe(true);
  const created = await res.json();
  return created.id;
}

/**
 * Full deterministic learning flow: seed material -> sync concepts -> create,
 * take, and submit an assessment. Submission records assessment activity,
 * creates per-concept evidence, and runs the learner loop (concept states).
 */
export async function seedLearningFlow(api: AuthedApi, contextId: string): Promise<void> {
  await seedResource(api, contextId);
  const sync = await api.post(`/api/v1/contexts/${contextId}/concepts/sync`);
  if (!sync.ok()) return; // no chunks ready yet — nothing else will work either
  const created = await api.post("/api/v1/assessments", {
    data: { context_id: contextId, format: "mcq", question_count: 3, difficulty: "easy" },
  });
  if (!created.ok()) return;
  const assessment = await created.json();
  const started = await api.post(`/api/v1/assessments/${assessment.id}/attempts`);
  if (!started.ok()) return;
  const attempt = await started.json();
  const answers: Record<string, string> = {};
  for (const q of attempt.questions) answers[q.id] = q.options[0];
  await api.put(`/api/v1/assessments/${assessment.id}/attempts/${attempt.attempt_id}/answers`, {
    data: { answers },
  });
  await api.post(`/api/v1/assessments/${assessment.id}/attempts/${attempt.attempt_id}/submit`, {
    data: { idempotency_key: `aria-e2e-${Date.now()}`, answers },
  });
}

/** Wait until the home dashboard has finished loading its data and rendered a stable element. */
export async function waitForHome(page: Page): Promise<void> {
  await page.getByText("Continue learning", { exact: true }).first().waitFor({ state: "visible", timeout: 20_000 });
}

export function randomUser(): TestUser {
  return {
    email: `user-${Date.now()}@example.com`,
    password: "testing-12345",
    name: "Playwright User",
  };
}

/** Register a fresh user via the real backend API (isolated E2E instance). */
export async function createUser(user: TestUser): Promise<void> {
  const ctx = await request.newContext({ baseURL: API });
  const res = await ctx.post("/api/v1/auth/register", {
    data: {
      display_name: user.name,
      email: user.email,
      password: user.password,
    },
  });
  expect(res.ok(), `register failed: ${res.status()} ${await res.text()}`).toBe(true);
  await ctx.dispose();
}

/** Sign into the UI via the signin form and wait for the app dashboard. */
export async function signIn(page: Page, user: TestUser): Promise<void> {
  await page.goto("/signin");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL("**/app", { timeout: 20_000 });
}

/**
 * Sign in (fresh user -> onboarding), then create a learning context so the
 * learner lands on the app dashboard with a real context in place.
 */
export async function signInAndOnboard(page: Page, user: TestUser): Promise<void> {
  await page.goto("/signin");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: /sign in/i }).click();
  // fresh user has no context -> onboarding
  await page.waitForURL(/onboarding/, { timeout: 20_000 });
  await page.getByLabel("What would you like to learn?").fill("Database Management Systems");
  await page.getByLabel("What’s your goal?").fill("Understand database normalization");
  await page.getByRole("button", { name: /start learning/i }).click();
  await page.waitForURL("**/app", { timeout: 20_000 });
  await waitForHome(page);
}
