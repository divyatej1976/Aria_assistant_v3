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

test("learn screen creates a session and sends a message to the real tutor", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask ARIA anything...").waitFor({ state: "visible", timeout: 20_000 });

  // send a message
  await page.getByPlaceholder("Ask ARIA anything...").fill("Explain Python functions");
  await page.getByRole("button", { name: "Send" }).click();

  // an AI reply (aria) appears
  await expect(page.getByText("ARIA Tutor").first()).toBeVisible({ timeout: 30_000 });
  await noSeriousAxe(page, "learn");
});

test("selecting a session whose messages fail does not leave the page stuck loading", async ({ page }) => {
  test.setTimeout(150_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask ARIA anything...").waitFor({ state: "visible", timeout: 20_000 });
  await expect(page.getByText("Sessions").first()).toBeVisible({ timeout: 20_000 });

  // Ensure the sidebar has a second session by creating one via the UI.
  await page.getByRole("button", { name: "New Chat" }).click();
  await page.waitForTimeout(800);
  await expect(page.locator(".nav-link")).toHaveCount(2, { timeout: 20_000 });

  // Fail only message-list GETs; the POST (send) and session-list calls must still succeed.
  await page.route("**/api/v1/study/sessions/*/messages", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"boom"}' });
      return;
    }
    await route.continue();
  });

  // Click the older session — the bug left the page on "Loading your tutor..." forever.
  const other = page.locator(".nav-link").nth(1);
  await other.waitFor({ state: "visible", timeout: 20_000 });
  await other.click();

  // The full-page loading spinner must clear (no stuck state) and a toast must appear.
  await expect(page.getByText("Loading your tutor").first()).toBeHidden({ timeout: 20_000 });
  await expect(page.getByText("Could not load this session.").first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByPlaceholder("Ask ARIA anything...")).toBeVisible({ timeout: 20_000 });

  await page.unroute("**/api/v1/study/sessions/*/messages");
  await noSeriousAxe(page, "learn-failed-session");
});
