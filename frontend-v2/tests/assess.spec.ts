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

test("assessments page shows the empty state for a fresh learner", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/assess");
  await page.getByText("Assessments").first().waitFor({ state: "visible", timeout: 20_000 });
  await expect(page.getByRole("button", { name: /Create Assessment/i }).first()).toBeVisible({ timeout: 20_000 });
});

test("create an assessment from real material, answer it, and see the real score", async ({ page }) => {
  test.setTimeout(120_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  // seed "ready study material" the assessment generator depends on
  const contextId = await activeContextId(page);
  const api = await authedApi(user);
  await seedResource(api, contextId);
  await api.dispose();

  await page.goto("/app/assess");
  await page.getByRole("button", { name: /Create Assessment/i }).first().click();

  // choose difficulty and create
  await page.getByRole("button", { name: "Hard" }).click();
  await page.getByRole("button", { name: /Create Assessment/i }).last().click();

  // lands on the take screen with questions
  await page.getByRole("heading", { name: "Assessment", exact: true }).waitFor({ state: "visible", timeout: 30_000 });

  // draft persistence: answer the first question, reload, resume keeps it checked
  const firstRadio = page.locator('input[type="radio"]').first();
  await firstRadio.waitFor({ state: "visible", timeout: 20_000 });
  await firstRadio.check();
  await page.reload();
  const cardWithResume = page.locator(".card", { hasText: /Resume test/i }).first();
  await expect(cardWithResume).toBeVisible({ timeout: 20_000 });
  await cardWithResume.click();
  await page.getByRole("heading", { name: "Assessment", exact: true }).waitFor({ state: "visible", timeout: 30_000 });
  await expect(page.locator('input[type="radio"]').first()).toBeChecked({ timeout: 20_000 });

  // timer + mark-for-review controls exist
  await expect(page.getByRole("button", { name: "Mark for review" }).first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/answered/).first()).toBeVisible();

  // answer every question
  const radios = page.locator('input[type="radio"]');
  await radios.first().waitFor({ state: "visible", timeout: 20_000 });
  const count = await radios.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < count; i++) {
    const radio = radios.nth(i);
    if (!(await radio.isChecked())) await radio.check();
  }

  await page.getByRole("button", { name: /Submit Answers/i }).click();

  // real result review — numbers must be consistent with the answered count
  await page.locator(".score-hero").waitFor({ state: "visible", timeout: 30_000 });
  const correctVal = parseInt((await page.locator(".score-stat.ok").innerText()).trim(), 10);
  const incorrectVal = parseInt((await page.locator(".score-stat.bad").innerText()).trim(), 10);
  expect(Number.isNaN(correctVal)).toBe(false);
  expect(Number.isNaN(incorrectVal)).toBe(false);
  // MCQ renders 4 option radios per question; catches dropped-answers regressions
  const questions = count / 4;
  expect(Number.isInteger(questions)).toBe(true);
  expect(correctVal + incorrectVal, "correct + incorrect must equal question count").toBe(questions);
  // one answer-review row per question
  await expect(page.locator(".kv")).toHaveCount(questions);
  await noSeriousAxe(page, "assess-review");
});