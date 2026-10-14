import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import {
  activeContextId,
  authedApi,
  createUser,
  randomUser,
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

const bell = (page: Page) => page.getByRole("button", { name: "Notifications" });

test("bell shows an empty state for a fresh learner", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  // fresh session on a non-planner page: no reminder auto-check interference
  await page.goto("/app/account");
  await page.getByRole("heading", { name: "Account" }).waitFor({ state: "visible", timeout: 20_000 });

  await bell(page).click();
  await expect(page.getByText("No notifications yet.").first()).toBeVisible({ timeout: 20_000 });
  await expect(page.locator(".bell-btn .badge")).toHaveCount(0);
  await page.waitForLoadState("networkidle");
  await noSeriousAxe(page, "notifications-empty");
});

test("seeded exam reminder appears in the bell and mark-read clears the badge", async ({ page }) => {
  test.setTimeout(150_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const contextId = await activeContextId(page);
  const api = await authedApi(user);

  // exam due within its reminder window
  const dueAt = new Date(Date.now() + 2 * 86_400_000).toISOString();
  const created = await api.post("/api/v1/planner/deadlines", {
    data: { context_id: contextId, title: "History Exam", due_at: dueAt, reminder_days_before: 5 },
  });
  expect(created.ok(), `deadline create failed: ${created.status()} ${await created.text()}`).toBe(true);

  // surface reminders (same endpoint the Planner auto-calls)
  const check = await api.post("/api/v1/planner/reminders/check");
  expect(check.ok(), `reminder check failed: ${check.status()}`).toBe(true);
  const result = await check.json();
  expect(result.notifications_created).toBeGreaterThanOrEqual(1);

  // reload so the app-shell refetches the unread count
  await page.goto("/app");
  await page.getByText("Continue learning", { exact: true }).first().waitFor({ state: "visible", timeout: 20_000 });

  const badge = page.locator(".bell-btn .badge");
  await expect(badge).toBeVisible({ timeout: 20_000 });

  // open the bell: the reminder is there with the exam title
  await bell(page).click();
  await expect(page.getByText(/History Exam/i).first()).toBeVisible({ timeout: 20_000 });
  const unreadItems = page.locator(".notif-item.unread");
  await expect(unreadItems.first()).toBeVisible({ timeout: 20_000 });

  // clicking the notification marks it read; badge clears when nothing remains
  await unreadItems.first().click();
  await expect(badge).toHaveCount(0, { timeout: 20_000 });

  // mark all read keeps everything read
  await page.getByRole("button", { name: /Mark all read/i }).click();
  await expect(page.locator(".notif-item.unread")).toHaveCount(0, { timeout: 20_000 });
  await expect(badge).toHaveCount(0);
});

test("notification preferences persist across reloads", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/account");
  await page.getByRole("heading", { name: /Account & settings/i }).waitFor({ state: "visible", timeout: 20_000 });

  const remindersSwitch = page.getByRole("switch", { name: "Learning reminders" });
  await expect(remindersSwitch).toHaveAttribute("aria-checked", "false", { timeout: 20_000 });

  // toggle on -> persists via /me/preferences
  await remindersSwitch.click();
  await expect(remindersSwitch).toHaveAttribute("aria-checked", "true", { timeout: 20_000 });

  const contextId = await activeContextId(page);
  void contextId;
  const api = await authedApi(user);
  const prefs = (await api.get("/api/v1/me/preferences").then((r) => r.json())) as { key: string; value: string }[];
  const remindersPref = prefs.find((p) => p.key === "notify_reminders");
  expect(remindersPref?.value).toBe("true");
  await api.dispose();

  // survives reload
  await page.reload();
  const reloaded = page.getByRole("switch", { name: "Learning reminders" });
  await expect(reloaded).toHaveAttribute("aria-checked", "true", { timeout: 20_000 });

  // push toggle degrades gracefully without VAPID config (stays off, no crash)
  const pushSwitch = page.getByRole("switch", { name: "Push notifications" });
  await pushSwitch.click();
  await expect(pushSwitch).toHaveAttribute("aria-checked", "false", { timeout: 20_000 });
});