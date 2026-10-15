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
  answerQuiz,
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
  await page.getByText("Practice").first().waitFor({ state: "visible", timeout: 20_000 });
  await expect(page.getByRole("button", { name: /Create assessment/i }).first()).toBeVisible({ timeout: 20_000 });
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
  await page.getByRole("button", { name: /Create assessment/i }).first().click();

  // choose the quiz: hard, 5 multiple-choice questions, answers at the end
  const setup = page.getByRole("dialog", { name: "Create assessment" });
  await setup.getByText("Customize").click();
  await setup.getByRole("radio", { name: "Hard" }).click();
  await setup.getByRole("button", { name: "5", exact: true }).click();
  await setup.getByRole("radio", { name: "At the end", exact: true }).click();
  await setup.getByRole("button", { name: "Start quiz" }).click();

  // one question at a time
  const player = page.getByRole("region", { name: "Quiz" });
  await expect(player.getByText("Question 1 of 5")).toBeVisible({ timeout: 30_000 });
  await expect(player.locator(".quiz-prompt")).toHaveCount(1);

  // draft persistence: answer the first question, reload, resume keeps it
  await player.locator('input[type="radio"]').first().check();
  await page.reload();
  const cardWithResume = page.locator(".card", { hasText: /Resume test/i }).first();
  await expect(cardWithResume).toBeVisible({ timeout: 20_000 });
  await cardWithResume.click();
  await expect(player.getByText("Question 2 of 5")).toBeVisible({ timeout: 30_000 });
  await player.getByRole("button", { name: /Back/ }).click();
  await expect(player.locator('input[type="radio"]').first()).toBeChecked({ timeout: 20_000 });

  // exam mode: a flag control exists and nothing is revealed before the end
  await player.getByRole("button", { name: /Flag to review/ }).click();
  await expect(player.getByRole("button", { name: "Question 1, answered, flagged" })).toBeVisible();
  const count = await answerQuiz(page);
  expect(count).toBe(5);

  // real result review — numbers must be consistent with the answered count
  await page.locator(".score-hero").waitFor({ state: "visible", timeout: 30_000 });
  const correctVal = parseInt((await page.locator(".score-stat.ok").innerText()).trim(), 10);
  const incorrectVal = parseInt((await page.locator(".score-stat.bad").innerText()).trim(), 10);
  expect(Number.isNaN(correctVal)).toBe(false);
  expect(Number.isNaN(incorrectVal)).toBe(false);
  expect(correctVal + incorrectVal, "correct + incorrect must equal question count").toBe(5);
  // one answer-review row per question, each showing its question
  await expect(page.locator(".quiz-review li")).toHaveCount(5);
  await expect(page.locator(".quiz-review-q").first()).not.toBeEmpty();
  await noSeriousAxe(page, "assess-review");
});