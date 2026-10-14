import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import {
  activeContextId,
  authedApi,
  createUser,
  randomUser,
  seedLearningFlow,
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

test("progress screen renders real zeros for a fresh learner", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/progress");
  await page.getByText("Your Progress").waitFor({ state: "visible", timeout: 20_000 });

  // streaks + activity render from the real consistency endpoint
  await expect(page.getByText("Current Streak").first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTitle(/session/).first()).toBeVisible();
  await expect(page.getByText("Locked").first()).toBeVisible();
  await expect(page.getByText("No learning activity yet").first()).toBeVisible({ timeout: 20_000 });
});

test("progress reflects real learning activity and awards badges", async ({ page }) => {
  test.setTimeout(120_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const contextId = await activeContextId(page);
  const api = await authedApi(user);
  await seedLearningFlow(api, contextId);
  await api.dispose();

  await page.goto("/app/progress");
  await page.getByText("Your Progress").waitFor({ state: "visible", timeout: 20_000 });

  // a qualifying assessment activity was recorded today
  await expect(page.getByText("Assessment", { exact: true }).first()).toBeVisible({ timeout: 20_000 });
  // the first-assessment badge is now unlocked (earned cards carry the .earned
  // class and a check mark; locked ones show "Locked")
  const firstAssessmentBadge = page.locator(".badge-card.earned").filter({ hasText: "First assessment" });
  await expect(firstAssessmentBadge).toBeVisible({ timeout: 20_000 });
  await expect(firstAssessmentBadge.locator(".badge-check")).toBeVisible();
});

test("progress page is accessible", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/progress");
  await page.getByText("Your Progress").waitFor({ state: "visible", timeout: 20_000 });
  await page.waitForLoadState("networkidle");
  await noSeriousAxe(page, "progress");
});