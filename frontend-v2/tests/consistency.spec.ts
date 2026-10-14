import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import path from "node:path";

async function fixture(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.route("**/api/v1/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = [];
    if (path === "/api/v1/auth/me") body = { id: "consistency-user", email: "learner@example.com", display_name: "Learner", verified: true };
    else if (path === "/api/v1/contexts") body = [{ id: "consistency-context", title: "Databases", status: "ACTIVE" }];
    else if (path.endsWith("/unread-count")) body = { unread: 0 };
    else if (path.endsWith("/adaptation")) body = { states: [], decisions: [] };
    else if (path.endsWith("/consistency")) body = { current_streak: 1, longest_streak: 1, active_this_week: 1, active_this_month: 1, heatmap: [] };
    else if (path.endsWith("/badges")) body = [{ code: "first_study", label: "First study", earned: true, earned_at: "2026-10-14T12:00:00Z" }];
    else if (path === "/api/v1/settings/capabilities") body = { personal_keys_enabled: false, allowed_models: [], personal_key: { configured: false } };
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
  });
}

test("note review states stay readable without leaking backend enums", async ({ page }) => {
  await fixture(page);
  await page.route("**/api/v1/notes?*", route => route.fulfill({ contentType: "application/json", body: JSON.stringify(
    ["NEW", "REVIEWING", "LEARNING", "MASTERED", "AWAITING_REVIEW"].map((state, index) => ({
      id: `note-${index}`, title: `Note ${index}`, state, created_at: "2026-10-14T12:00:00Z",
    })),
  ) }));
  await page.goto("/app/materials");
  await expect(page.locator(".audio-card .type-tag")).toHaveText(["New note", "Review needed", "Learning", "Mastered", "Awaiting review"]);
});

for (const screen of [
  { route: "account", endpoint: "**/auth/sessions", label: "Loading your account…", heading: "Account & settings" },
  { route: "planner", endpoint: "**/planner/deadlines?*", label: "Loading your planner…", heading: "Planner" },
  { route: "learn", endpoint: "**/study/sessions?*", label: "Loading your tutor…", heading: null },
]) {
  test(`${screen.route} waits for its data before displaying an empty screen`, async ({ page }) => {
    await fixture(page);
    let release!: () => void;
    const gate = new Promise<void>(resolve => { release = resolve; });
    await page.route(screen.endpoint, async route => {
      await gate;
      await route.fulfill({ contentType: "application/json", body: "[]" });
    });
    await page.goto(`/app/${screen.route}`);
    await expect(page.getByRole("status").filter({ hasText: screen.label })).toBeVisible();
    if (screen.heading) await expect(page.getByRole("heading", { name: screen.heading, exact: true })).toHaveCount(0);
    release();
    await expect(page.locator(".loading-state")).toHaveCount(0);
    if (screen.heading) await expect(page.getByRole("heading", { name: screen.heading, exact: true })).toBeVisible();
    else await expect(page.getByPlaceholder("Ask ARIA anything…")).toBeVisible();
  });
}

for (const palette of ["aurora", "noir"]) {
  test(`earned badges and profile foreground remain accessible in ${palette}`, async ({ page }) => {
    await fixture(page);
    await page.addInitScript(theme => localStorage.setItem("aria.palette", theme), palette);
    const evidence = path.resolve("../docs/screenshots/consistency");
    mkdirSync(evidence, { recursive: true });
    for (const width of [375, 1440]) for (const route of ["progress", "account"]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(`/app/${route}`);
      await expect(page.locator("html")).toHaveAttribute("data-theme", palette);
      await expect(page.locator(".loading-state")).toHaveCount(0);
      await expect(page.getByRole("heading", { name: route === "progress" ? "Your progress" : "Account & settings", exact: true })).toBeVisible();
      const results = await new AxeBuilder({ page }).analyze();
      expect(results.violations.filter(v => v.impact === "serious" || v.impact === "critical")).toEqual([]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: path.join(evidence, `${palette}-${width}-${route}.png`), fullPage: true, animations: "disabled" });
    }
  });
}
