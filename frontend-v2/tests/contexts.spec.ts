import { expect, test } from "@playwright/test";
import { createUser, randomUser, waitForHome, type TestUser } from "./helpers";

test("onboarding creates a real learning context and the home shows it", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);

  await page.goto("/signin");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: /sign in/i }).click();

  // fresh user -> onboarding
  await page.waitForURL(/onboarding/, { timeout: 20_000 });

  const topic = "Database Management Systems";
  await page.getByLabel("What are you studying?").fill(topic);
  await page.getByRole("button", { name: /start learning/i }).click();

  await page.waitForURL("**/app", { timeout: 20_000 });
  await waitForHome(page);
  await expect(page.getByText(topic, { exact: false }).first()).toBeVisible();
});

test("re-signing in after a context exists goes straight to the app (not onboarding)", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);

  // first session: create a context
  await page.goto("/signin");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL(/onboarding/, { timeout: 20_000 });
  await page.getByLabel("What are you studying?").fill("DSA");
  await page.getByRole("button", { name: /start learning/i }).click();
  await page.waitForURL("**/app", { timeout: 20_000 });
  await waitForHome(page);

  // sign out
  await page.getByRole("button", { name: "Profile" }).click();
  await page.getByText("Sign Out").click();
  await page.waitForURL("**/", { timeout: 20_000 });

  // second session: context exists -> goes straight to /app
  await page.goto("/signin");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL("**/app", { timeout: 20_000 });
  await waitForHome(page);
  await expect(page.getByText("DSA", { exact: false }).first()).toBeVisible();
});

test("switching context in the header updates mounted screens immediately (no reload)", async ({ page }) => {
  const { createUser, randomUser, signInAndOnboard, authedApi, activeContextId } = await import("./helpers");
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const firstContextId = await activeContextId(page);
  const api = await authedApi(user);
  const created = await api.post("/api/v1/contexts", {
    data: { title: "Second Goal", configuration: { mastery_level: "intermediate" } },
  });
  expect(created.ok(), await created.text()).toBe(true);
  const secondId = ((await created.json()) as { id: string }).id;
  await api.dispose();

  // refresh so the shared provider picks up the API-created context
  await page.reload();
  await page.locator('[data-home-ready="true"]').waitFor({ state: "visible", timeout: 20_000 });

  // header select now offers both; switching updates mounted screens WITHOUT reload
  const switcher = page.getByLabel("Active learning context");
  await expect(switcher).toBeVisible({ timeout: 20_000 });
  await switcher.selectOption(secondId);
  await expect(switcher).toHaveValue(secondId, { timeout: 10_000 });

  // The Continue learning card reflects the new context WITHOUT any reload.
  await expect(
    page.locator(".learning-hero .hero-topic"),
  ).toHaveText("Second Goal", { timeout: 15_000 });
  void firstContextId;
});
