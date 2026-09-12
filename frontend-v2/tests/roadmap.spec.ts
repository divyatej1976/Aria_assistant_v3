import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import {
  activeContextId,
  authedApi,
  createUser,
  randomUser,
  seedResource,
  signInAndOnboard,
  type TestUser,
} from "./helpers";

async function noSeriousAxe(page: Page, name: string) {
  let results;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      results = await new AxeBuilder({ page }).analyze();
      break;
    } catch {
      if (attempt === 1) throw Error(`axe failed on ${name}`);
      await page.waitForLoadState("networkidle");
    }
  }
  const serious = results!.violations.filter((v) => v.impact === "serious");
  const critical = results!.violations.filter((v) => v.impact === "critical");
  expect(critical, `critical on ${name}`).toEqual([]);
  expect(serious, `serious on ${name}`).toEqual([]);
}

type Authed = Awaited<ReturnType<typeof authedApi>>;
type Question = { id: string; options: string[] };
type Detail = { question_id: string; correct_option: string; correct: boolean };

async function createAssessment(api: Authed, cid: string): Promise<string> {
  const res = await api.post("/api/v1/assessments", {
    data: { context_id: cid, format: "mcq", question_count: 3, difficulty: "easy" },
  });
  expect(res.ok(), `assessment create failed: ${res.status()} ${await res.text()}`).toBe(true);
  return (await res.json()).id;
}

async function runAttempt(
  api: Authed,
  assessmentId: string,
  makeAnswers: (questions: Question[]) => Record<string, string>,
): Promise<{ details: Detail[]; questions: Question[] }> {
  const started = await api.post(`/api/v1/assessments/${assessmentId}/attempts`);
  expect(started.ok(), `attempt start failed: ${started.status()}`).toBe(true);
  const attempt = await started.json();
  const answers = makeAnswers(attempt.questions as Question[]);
  const idem = `roadmap-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const submitted = await api.post(`/api/v1/assessments/${assessmentId}/attempts/${attempt.attempt_id}/submit`, {
    data: { idempotency_key: idem, answers },
  });
  expect(submitted.ok(), `submit failed: ${submitted.status()} ${await submitted.text()}`).toBe(true);
  return { details: (await submitted.json()).details as Detail[], questions: attempt.questions as Question[] };
}

test("roadmaps shows the empty state for a fresh learner", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/roadmaps");
  await page.getByRole("heading", { name: "Roadmaps" }).waitFor({ state: "visible", timeout: 20_000 });

  await expect(page.getByText("No roadmap yet").first()).toBeVisible({ timeout: 20_000 });
  await page.waitForLoadState("networkidle");
  await noSeriousAxe(page, "roadmaps");
});

test("tree builds from real concepts and ticks flip when concept states reach Supported", async ({ page }) => {
  test.setTimeout(180_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const contextId = await activeContextId(page);
  const api = await authedApi(user);
  await seedResource(api, contextId);
  const sync = await api.post(`/api/v1/contexts/${contextId}/concepts/sync`);
  expect(sync.ok(), `concepts/sync failed: ${sync.status()}`).toBe(true);
  const assessmentId = await createAssessment(api, contextId);

  // First attempt answers option[0]; after a single attempt no concept can be
  // SUPPORTED (needs 2 consecutive correct), so the roadmap starts at 0%.
  const first = await runAttempt(api, assessmentId, (qs) =>
    Object.fromEntries(qs.map((q) => [q.id, q.options[0]])),
  );
  // correct options are revealed in the attempt result
  const correctAnswers = Object.fromEntries(first.details.map((d) => [d.question_id, d.correct_option]));

  // build the roadmap via the UI
  await page.goto("/app/roadmaps");
  await page.getByRole("heading", { name: "Roadmaps" }).waitFor({ state: "visible", timeout: 20_000 });
  await page.getByRole("button", { name: /Create Roadmap/i }).first().click();
  await page.getByLabel("Learning Goal").fill("Master Python for data analysis");
  await page.getByRole("button", { name: "Beginner" }).click();
  await page.getByRole("button", { name: /Create Roadmap/i }).last().click();

  // tree renders from real concepts with 0% completion
  await expect(page.locator(".ws-row").first()).toBeVisible({ timeout: 30_000 });
  await expect(page.locator(".r-n").first()).toHaveText("0%", { timeout: 30_000 });
  const topicCount = await page.locator(".ws-row + div .card").count();
  expect(topicCount).toBeGreaterThan(0);

  // subtopic page shows the reasoning behind the tick state
  await page.locator(".ws-row + div .card").first().click();
  await expect(page.getByText("Why this tick state?").first()).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: /All topics/i }).click();

  // Flip every concept to SUPPORTED with 2 consecutive correct attempts.
  await runAttempt(api, assessmentId, () => correctAnswers);
  await runAttempt(api, assessmentId, () => correctAnswers);
  await api.dispose();

  await page.reload();
  await page.getByRole("heading", { name: "Roadmaps" }).waitFor({ state: "visible", timeout: 20_000 });
  // after the correct attempts, at least one concept reached Supported -> ticks appear
  await expect(page.locator(".r-n").first()).not.toHaveText("0%", { timeout: 30_000 });
  await expect(page.getByText("Completed").first()).toBeVisible({ timeout: 20_000 });
});