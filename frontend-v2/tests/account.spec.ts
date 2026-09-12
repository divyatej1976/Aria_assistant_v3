import AxeBuilder from "@axe-core/playwright";
import { expect, request, test, type APIRequestContext, type Page } from "@playwright/test";
import {
  createUser,
  randomUser,
  signIn,
  signInAndOnboard,
  waitForHome,
  type TestUser,
} from "./helpers";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

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

/** Open an independent, cookie-authenticated session for the same user. */
async function secondSession(user: TestUser): Promise<APIRequestContext> {
  const ctx = await request.newContext({ baseURL: API });
  const res = await ctx.post("/api/v1/auth/login", {
    data: { email: user.email, password: user.password, device_label: "e2e-second" },
  });
  expect(res.ok(), `second login failed: ${res.status()}`).toBe(true);
  return ctx;
}

test("account page shows the real identity and is accessible", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/account");
  await page.getByRole("heading", { name: /Account & Settings/i }).waitFor({ state: "visible", timeout: 20_000 });

  // email + display_name come from GET /auth/me (registered with display_name)
  await expect(page.getByLabel("Email")).toHaveValue(user.email, { timeout: 20_000 });
  await expect(page.getByLabel("Name")).toHaveValue(user.name);
  await page.waitForLoadState("networkidle");
  await noSeriousAxe(page, "account");
});

test("profile updates persist across reloads", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/account");
  await page.getByRole("heading", { name: /Personal Details/i }).waitFor({ state: "visible", timeout: 20_000 });

  await page.getByLabel("Name").fill("Renamed User");
  await page.getByRole("button", { name: /Save Changes/i }).click();

  // persists in UI after reload
  await page.reload();
  await expect(page.getByLabel("Name")).toHaveValue("Renamed User", { timeout: 20_000 });
});

test("password change signs other devices out and the new password works", async ({ page }) => {
  test.setTimeout(150_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  // second device session exists before the change
  const second = await secondSession(user);
  expect((await second.get("/api/v1/auth/me")).status()).toBe(200);

  await page.goto("/app/account");
  await page.getByLabel("Current Password").fill(user.password);
  await page.getByLabel("New Password", { exact: true }).fill("brand-new-pw-123");
  await page.getByLabel("Confirm New Password").fill("brand-new-pw-123");
  await page.getByRole("button", { name: /Change Password/i }).click();

  // fields cleared on success
  await expect(page.getByLabel("New Password", { exact: true })).toHaveValue("", { timeout: 20_000 });

  // the pre-existing second session was revoked by the change
  expect((await second.get("/api/v1/auth/me")).status()).toBe(401);

  // sign out via the profile popover, old password rejected, new one works
  await page.getByRole("button", { name: "Profile" }).click();
  await page.getByText(/Sign Out/i).click();
  await page.waitForURL("**/", { timeout: 20_000 });

  await page.goto("/signin");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByText(/invalid credentials/i).first()).toBeVisible({ timeout: 20_000 });

  await signIn(page, { ...user, password: "brand-new-pw-123" });
  await waitForHome(page);
});

test("revoking another session kills it", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const second = await secondSession(user);
  expect((await second.get("/api/v1/auth/me")).status()).toBe(200);

  await page.goto("/app/account");
  await page.getByRole("heading", { name: /Active Sessions/i }).waitFor({ state: "visible", timeout: 20_000 });

  // two active sessions: this device + e2e-second
  await expect(page.getByText("This device").first()).toBeVisible({ timeout: 20_000 });
  const secondRow = page.locator(".kv").filter({ hasText: "e2e-second" });
  await expect(secondRow).toBeVisible({ timeout: 20_000 });

  await page.getByRole("button", { name: /Revoke e2e-second/i }).click();

  // row disappears and that session is really dead
  await expect(secondRow).toHaveCount(0, { timeout: 20_000 });
  expect((await second.get("/api/v1/auth/me")).status()).toBe(401);
});

test("danger zone: export downloads JSON and context deletion returns to onboarding", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/account");
  await page.getByRole("heading", { name: /Data & Privacy/i }).waitFor({ state: "visible", timeout: 20_000 });

  // export produces a JSON attachment
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: /Export my data/i }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/aria-data-export\.json$/);

  // confirm dialog opens; Escape cancels without deleting
  await page.getByRole("button", { name: /Delete this context/i }).click();
  const dialog = page.getByRole("alertdialog");
  await expect(dialog).toBeVisible({ timeout: 20_000 });
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0, { timeout: 10_000 });
  // still on account (context intact)
  await expect(page.getByRole("heading", { name: /Personal Details/i })).toBeVisible();

  // reopen and confirm deletion -> onboarding
  await page.getByRole("button", { name: /Delete this context/i }).click();
  await page.getByRole("alertdialog").waitFor({ state: "visible", timeout: 10_000 });
  await page.getByRole("button", { name: /Delete context/i }).last().click();
  await page.waitForURL(/onboarding/, { timeout: 20_000 });
});
