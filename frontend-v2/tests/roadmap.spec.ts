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

async function createAssessment(api: Authed, cid: string, conceptId: string): Promise<string> {
  const res = await api.post("/api/v1/assessments", {
    data: { context_id: cid, format: "mcq", question_count: 1, difficulty: "easy", concept_ids: [conceptId] },
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

test("roadmap milestones tick when a matching skill reaches Supported", async ({ page }) => {
  test.setTimeout(180_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const contextId = await activeContextId(page);
  const api = await authedApi(user);
  await seedResource(api, contextId);
  const skillResource = await api.post("/api/v1/resources/text", {
    data: {
      context_id: contextId,
      title: "Foundations practice",
      text: "Fundamentals and terminology form the essential core foundation of learning. ".repeat(80),
    },
  });
  expect(skillResource.ok(), await skillResource.text()).toBe(true);
  expect((await skillResource.json()).processing_status).toBe("READY");
  const sync = await api.post(`/api/v1/contexts/${contextId}/concepts/sync`);
  expect(sync.ok(), `concepts/sync failed: ${sync.status()}`).toBe(true);
  const concepts = (await sync.json()) as { id: string; name: string }[];
  const fundamentalsSkill = concepts.find((concept) => concept.name.toLowerCase() === "fundamentals");
  const terminologySkill = concepts.find((concept) => concept.name.toLowerCase() === "terminology");
  expect(fundamentalsSkill, "Fundamentals must be extracted from the practice resource").toBeTruthy();
  expect(terminologySkill, "Terminology must be extracted from the practice resource").toBeTruthy();
  const assessment1 = await createAssessment(api, contextId, fundamentalsSkill!.id);
  const assessment2 = await createAssessment(api, contextId, terminologySkill!.id);

  // First attempt answers option[0]; after a single attempt no concept can be
  // SUPPORTED (needs 2 consecutive correct), so the roadmap starts at 0%.
  const first1 = await runAttempt(api, assessment1, (qs) => Object.fromEntries(qs.map((q) => [q.id, q.options[0]])));
  const first2 = await runAttempt(api, assessment2, (qs) => Object.fromEntries(qs.map((q) => [q.id, q.options[0]])));
  const correct1 = Object.fromEntries(first1.details.map((d) => [d.question_id, d.correct_option]));
  const correct2 = Object.fromEntries(first2.details.map((d) => [d.question_id, d.correct_option]));

  // build the roadmap via the UI
  await page.goto("/app/roadmaps");
  await page.getByRole("heading", { name: "Roadmaps" }).waitFor({ state: "visible", timeout: 20_000 });
  await page.getByRole("button", { name: /Create roadmap/i }).first().click();
  // the setup asks one question at a time
  const setup = page.getByRole("dialog", { name: "Create roadmap" });
  await setup.getByLabel("What do you want to be able to do?").fill("Master Python for data analysis");
  await setup.getByRole("button", { name: /^Next/ }).click();
  await setup.getByRole("radio", { name: /^Beginner/ }).click();
  await setup.getByRole("button", { name: /^Next/ }).click();
  await setup.getByRole("radio", { name: "3–5 hours" }).click();
  await setup.getByRole("button", { name: /^Next/ }).click();
  await setup.getByRole("button", { name: /^Next/ }).click();
  await expect(setup.getByText("3–5 hours")).toBeVisible();
  await setup.getByRole("button", { name: /Create roadmap/i }).click();

  // tree renders from real concepts with 0% completion
  await expect(page.locator(".roadmap-tier-head").first()).toBeVisible({ timeout: 30_000 });
  await expect(page.locator(".r-n").first()).toHaveText("0%", { timeout: 30_000 });
  const topicCount = await page.locator(".roadmap-topic-card").count();
  expect(topicCount).toBeGreaterThan(0);
  // 3–5 hours a week fits two milestones, each with Study and Quiz me
  const week = page.locator(".plan-week li");
  await expect(week).toHaveCount(2);
  await expect(week.first().getByRole("link", { name: /Quiz me/ })).toHaveAttribute("href", /\/app\/assess\?quiz_topic=/);

  // subtopic page shows the reasoning behind the tick state
  await page.locator(".roadmap-topic-details").first().click();
  await expect(page.getByText("Why this tick state?").first()).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: /All topics/i }).click();

  // Confirm mastery of the matching skills with consecutive correct attempts.
  await runAttempt(api, assessment1, () => correct1);
  await runAttempt(api, assessment1, () => correct1);
  await runAttempt(api, assessment2, () => correct2);
  await runAttempt(api, assessment2, () => correct2);
  await api.dispose();

  await page.reload();
  await page.getByRole("heading", { name: "Roadmaps" }).waitFor({ state: "visible", timeout: 20_000 });
  // after the correct attempts, at least one milestone reached Supported -> ticks appear
  await expect(page.locator(".r-n").first()).not.toHaveText("0%", { timeout: 30_000 });
  await expect(page.getByText("Completed").first()).toBeVisible({ timeout: 20_000 });
});
