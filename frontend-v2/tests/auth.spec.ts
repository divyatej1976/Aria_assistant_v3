import { expect, test } from "@playwright/test";
import { createUser, randomUser, signInAndOnboard, type TestUser } from "./helpers";

test("sign in with wrong password shows an error and stays on signin", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);

  await page.goto("/signin");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill("wrong-password-123");
  await page.getByRole("button", { name: /sign in/i }).click();

  await expect(page.getByText(/invalid credentials/i).first()).toBeVisible({ timeout: 15_000 });
  await expect(page).toHaveURL(/\/signin/);
});

test("sign in with correct credentials sends a fresh user to onboarding", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);

  await page.goto("/signin");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: /sign in/i }).click();

  // fresh user has no context yet
  await page.waitForURL(/onboarding/, { timeout: 20_000 });
  await expect(page.getByRole("heading", { name: /start your learning journey/i })).toBeVisible();
});

test("sign out returns to the landing page", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  // open profile popover and sign out
  await page.getByRole("button", { name: "Profile" }).click();
  await page.getByText("Sign Out").click();

  await page.waitForURL("**/", { timeout: 20_000 });
  await expect(page.getByText("NEXT-GEN AI COMPANION", { exact: false }).first()).toBeVisible();
});

test("sign-in preserves credentials when application JavaScript loads late", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  let release = () => {};
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/_next/static/**", async route => {
    if (new URL(route.request().url()).pathname.endsWith(".js")) await pending;
    await route.continue();
  });
  try {
    await page.goto("/signin", { waitUntil: "commit" });
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Email")).toBeDisabled();
    await expect(page.getByLabel("Password")).toBeDisabled();
    release();
    await expect(page.getByLabel("Email")).toBeEnabled();
    await page.getByLabel("Email").fill(user.email);
    await page.getByLabel("Password").fill(user.password);
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForURL(/onboarding/, { timeout: 20_000 });
  } finally {
    release();
  }
});
