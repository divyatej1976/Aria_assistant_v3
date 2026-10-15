import { expect, test, type Page } from "@playwright/test";
import { activeContextId, authedApi, createUser, randomUser, seedResource, signInAndOnboard } from "./helpers";

/** A one-minute, answers-at-the-end quiz on seeded material, open at question 1. */
async function startTimedQuiz(page: Page) {
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  const api = await authedApi(user);
  await seedResource(api, await activeContextId(page));
  await api.dispose();
  await page.clock.install();
  await page.goto("/app/assess");
  await page.getByRole("button", { name: /Create assessment/i }).first().click();
  const setup = page.getByRole("dialog", { name: "Create assessment" });
  await setup.getByRole("radio", { name: /Topic test/ }).click();
  await setup.getByText("Customize").click();
  await setup.getByRole("radio", { name: "Whole quiz", exact: true }).click();
  await setup.getByLabel("Minutes for the whole quiz").fill("1");
  await setup.getByRole("button", { name: "Start quiz" }).click();
  const player = page.getByRole("region", { name: "Quiz" });
  await expect(player.getByText(/Question 1 of \d+/)).toBeVisible({ timeout: 60_000 });
  return player;
}

test("timer, flags and Enter survive the way learners actually use them", async ({ page }) => {
  test.setTimeout(180_000);
  const player = await startTimedQuiz(page);

  // Enter on a focused "Flag to review" flags the question and stays on it.
  await player.getByRole("button", { name: /Flag to review/ }).focus();
  await page.keyboard.press("Enter");
  await expect(player.getByText(/Question 1 of \d+/)).toBeVisible();
  await expect(player.getByRole("button", { name: /^Flagged/ })).toBeVisible();

  // After a reload the timer resumes and the flag is still there.
  await page.clock.fastForward(6_000);
  await page.reload();
  await page.locator(".card", { hasText: /Resume test/i }).first().click();
  await expect(player.locator(".quiz-clock")).toHaveText(/0:5\d left/, { timeout: 30_000 });
  await expect(player.getByRole("button", { name: /^Question 1, .*flagged/ })).toBeVisible();
});

test("a timed submission that fails is attempted once, not every second", async ({ page }) => {
  test.setTimeout(180_000);
  let submits = 0;
  await page.route("**/attempts/*/submit", async (route) => {
    submits += 1;
    await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "Server error" }) });
  });
  await startTimedQuiz(page);
  await page.clock.fastForward(62_000);
  await expect.poll(() => submits, { timeout: 20_000 }).toBe(1);
  await page.clock.fastForward(6_000);
  expect(submits).toBe(1);
});
