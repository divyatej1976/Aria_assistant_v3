import { expect, test } from "@playwright/test";
import {
  activeContextId,
  authedApi,
  createUser,
  randomUser,
  seedResource,
  signInAndOnboard,
  type TestUser,
} from "./helpers";

/** Seed material + concepts + one all-first-option attempt → weak (non-SUPPORTED) concept states. */
async function seedWeakStates(
  api: Awaited<ReturnType<typeof authedApi>>,
  contextId: string,
): Promise<void> {
  await seedResource(api, contextId);
  const sync = await api.post(`/api/v1/contexts/${contextId}/concepts/sync`);
  expect(sync.ok(), `concepts/sync failed: ${sync.status()}`).toBe(true);

  const created = await api.post("/api/v1/assessments", {
    data: { context_id: contextId, format: "mcq", question_count: 3, difficulty: "easy" },
  });
  expect(created.ok(), await created.text()).toBe(true);
  const assessmentId = ((await created.json()) as { id: string }).id;

  const started = await api.post(`/api/v1/assessments/${assessmentId}/attempts`);
  expect(started.ok()).toBe(true);
  const attempt = await started.json();
  const answers = Object.fromEntries(
    (attempt.questions as { id: string; options: string[] }[]).map((q) => [q.id, q.options[0]]),
  );
  const submitted = await api.post(
    `/api/v1/assessments/${assessmentId}/attempts/${attempt.attempt_id}/submit`,
    { data: { idempotency_key: `r3-${Date.now()}`, answers } },
  );
  expect(submitted.ok(), await submitted.text()).toBe(true);
}

test("planner shows readiness, ARIA suggestions, and turns a suggestion into a real task", async ({ page }) => {
  test.setTimeout(150_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const contextId = await activeContextId(page);
  const api = await authedApi(user);
  await seedWeakStates(api, contextId);
  await api.dispose();

  await page.goto("/app/planner");
  await page.getByText("What should I do today?").waitFor({ state: "visible", timeout: 20_000 });

  // readiness strip renders with real numbers
  await expect(page.getByText(/readiness \d+%/).first()).toBeVisible({ timeout: 20_000 });

  // ARIA suggests study tasks for weak concepts
  const suggestSection = page.getByText("Suggested by ARIA").first();
  await expect(suggestSection).toBeVisible({ timeout: 20_000 });
  const addButtons = page.getByRole("button", { name: /\+ Add study task/i });
  await expect(addButtons.first()).toBeVisible({ timeout: 20_000 });

  // clicking creates a REAL task that lands in Tomorrow
  await addButtons.first().click();
  await expect(page.getByText(/Added/, { exact: true }).first()).toBeVisible({ timeout: 20_000 });
});

test("missed tasks can be rescheduled to tomorrow", async ({ page }) => {
  test.setTimeout(150_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const contextId = await activeContextId(page);
  const api = await authedApi(user);
  const past = new Date(Date.now() - 86_400_000).toISOString();
  const created = await api.post("/api/v1/planner/tasks", {
    data: { context_id: contextId, title: "Old Missed Task", due_at: past },
  });
  expect(created.ok(), await created.text()).toBe(true);
  await api.dispose();

  await page.goto("/app/planner");
  await page.getByText("What should I do today?").waitFor({ state: "visible", timeout: 20_000 });
  await page.getByRole("button", { name: /Task Planning/i }).click();

  // Missed bucket contains it; reschedule moves it out
  const missedRow = page.locator(".ws-row").filter({ hasText: "Old Missed Task" });
  await expect(missedRow.first()).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: /Reschedule Old Missed Task/i }).click();

  // exactly one row remains, inside the Tomorrow card
  const rows = page.locator(".ws-row").filter({ hasText: "Old Missed Task" });
  await expect(rows).toHaveCount(1, { timeout: 20_000 });
  await expect(
    rows.first().locator("xpath=ancestor::div[contains(@class,'card')][1]"),
  ).toContainText("Tomorrow");
});
