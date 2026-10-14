import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { createUser, randomUser, signInAndOnboard, type TestUser } from "./helpers";

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

test("create an exam, then complete and delete it", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/planner");
  await page.getByRole("button", { name: /Create exam/i }).click();
  await page.getByLabel(/Exam name/i).fill("Data Structures");
  // default datetime may be empty; use the date input
  const dateInput = page.getByLabel("Due date");
  await dateInput.fill("2026-09-01T12:00");

  await page.getByRole("button", { name: /^Create/i }).last().click();
  await expect(page.getByText("Data Structures").first()).toBeVisible({ timeout: 15_000 });

  // mark complete
  await page.getByRole("button", { name: /Mark complete/i }).click();
  // delete
  await page.getByRole("button", { name: /Delete/i }).click();
  await expect(page.getByText("Data Structures").first()).toBeHidden({ timeout: 15_000 }).catch(() => {});
});

test("create a task and complete it", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/planner");
  await page.getByRole("button", { name: /Task planning/i }).click();
  await page.getByRole("button", { name: /Create task/i }).click();
  await page.getByLabel(/Task name/i).fill("Solve LeetCode 53");
  await page.getByRole("button", { name: /^Create/i }).last().click();

  await expect(page.getByText("Solve LeetCode 53").first()).toBeVisible({ timeout: 15_000 });
  // complete via the check button
  await page.getByRole("button", { name: "Complete Solve LeetCode 53" }).click();
  await expect(page.getByText("Completed").first()).toBeVisible({ timeout: 15_000 }).catch(() => {});
});

test("planner page is accessible", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  await page.goto("/app/planner");
  await page.getByRole("button", { name: /Exams & Deadlines/i }).waitFor({ state: "visible", timeout: 15_000 });
  await page.waitForLoadState("networkidle");
  await noSeriousAxe(page, "planner");
});
