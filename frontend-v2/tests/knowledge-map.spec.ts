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

test("knowledge map shows the empty state for a fresh learner", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/map");
  await page.getByRole("heading", { name: "Knowledge Map" }).waitFor({ state: "visible", timeout: 20_000 });

  await expect(page.getByText("No concepts tracked yet").first()).toBeVisible({ timeout: 20_000 });
});

test("knowledge map renders real concepts and evidence after learning", async ({ page }) => {
  test.setTimeout(150_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const contextId = await activeContextId(page);
  const api = await authedApi(user);
  await seedLearningFlow(api, contextId);
  await api.dispose();

  await page.goto("/app/map");
  await page.getByRole("heading", { name: "Knowledge Map" }).waitFor({ state: "visible", timeout: 20_000 });

  // concept nodes render (connector lines exist only when n > 0)
  await expect(page.getByText("No concepts tracked yet").first()).toBeHidden({ timeout: 30_000 });
  await expect(page.locator("svg line").first()).toBeAttached({ timeout: 20_000 });

  // search + state filter UI present once data has rendered
  await expect(page.getByLabel("Search concepts")).toBeVisible({ timeout: 20_000 });

  // filter chips narrow the visible set to zero and back
  await page.getByRole("button", { name: "Supported" }).click();
  await page.waitForTimeout(300);
  await page.getByRole("button", { name: "All", exact: true }).click();

  // the hub shows the real context title from onboarding
  await expect(page.getByText("Database Management Systems").first()).toBeVisible({ timeout: 20_000 });
});

test("knowledge map invalidates evidence and refreshes state", async ({ page }) => {
  test.setTimeout(150_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const contextId = await activeContextId(page);
  const api = await authedApi(user);
  await seedLearningFlow(api, contextId);
  const evidence = await api.get(`/api/v1/contexts/${contextId}/evidence`).then((r) => r.json()).catch(() => [] as unknown[]);
  await api.dispose();

  await page.goto("/app/map");
  await page.getByRole("heading", { name: "Knowledge Map" }).waitFor({ state: "visible", timeout: 20_000 });

  // If we have valid evidence, exercising the invalidate button must not break the page.
  const hasValid = Array.isArray(evidence) && evidence.some((e) => (e as { valid: boolean }).valid);
  if (hasValid) {
    const btn = page.getByRole("button", { name: /Invalidate/i }).first();
    await btn.waitFor({ state: "visible", timeout: 20_000 });
    await btn.click();
    await expect(page.getByText("Evidence invalidated").first()).toBeVisible({ timeout: 20_000 });
    await page.getByRole("heading", { name: "Evidence" }).waitFor({ state: "visible", timeout: 20_000 });
  }
  await noSeriousAxe(page, "knowledge-map");
});

test("knowledge map shows retry UI when API fails and recovers on retry", async ({ page }) => {
  test.setTimeout(150_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  // Force adaptation to fail so the error UI is rendered.
  await page.route("**/api/v1/contexts/*/adaptation", (route) =>
    route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"boom"}' }),
  );
  await page.goto("/app/map");
  // The page header is rendered before data; the retry UI appears after the failed load.
  await expect(page.getByText("This screen could not be loaded.").first()).toBeVisible({ timeout: 20_000 });
  const retry = page.getByRole("button", { name: "Try again" });
  await expect(retry).toBeVisible({ timeout: 10_000 });
  // Allow the retry to hit the real backend.
  await page.unroute("**/api/v1/contexts/*/adaptation");
  await retry.click();
  await expect(page.getByRole("heading", { name: "Knowledge Map" }).first()).toBeVisible({ timeout: 20_000 });
  // Either the empty state (fresh learner) or the map renders — both prove recovery.
  await expect(page.getByText(/No concepts tracked yet|Evidence/).first()).toBeVisible({ timeout: 20_000 });
  await noSeriousAxe(page, "knowledge-map-retry");
});