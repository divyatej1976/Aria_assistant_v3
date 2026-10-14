import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function fixture(page: Page, scores: unknown[]) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.route("**/api/v1/**", route => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = [];
    if (path.endsWith("/auth/me")) body = { id: "score-user", email: "scores@example.com", verified: true };
    else if (path === "/api/v1/contexts") body = [{ id: "score-context", title: "Database systems", status: "active" }];
    else if (path.endsWith("/unread-count")) body = { unread: 0 };
    else if (path === "/api/v1/assessments") body = [{ id: "assessment", context_id: "score-context", mode: "BASELINE", format: "mcq", status: "READY", question_count: 4, created_at: "2026-10-14T00:00:00Z", completed_scores: scores }];
    return route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
  });
}

test("score trend uses completed percentages chronologically and has an accessible alternative", async ({ page }, info) => {
  await fixture(page, [
    { attempt_id: "latest", score: 3, total: 4, completed_at: "2026-10-14T00:00:00Z" },
    { attempt_id: "first", score: 0, total: 5, completed_at: "2026-10-12T00:00:00Z" },
    { attempt_id: "second", score: 2, total: 2, completed_at: "2026-10-13T00:00:00Z" },
  ]);
  for (const palette of ["aurora", "noir"]) {
    await page.goto("/app/assess");
    await page.evaluate(value => { localStorage.setItem("aria.palette", value); localStorage.setItem("aria.gold", "0"); }, palette);
    await page.reload();
    const trend = page.locator(".assessment-score-trend");
    await expect(trend).toContainText("Latest · 3/4");
    await expect(trend.getByRole("img")).toHaveAccessibleName(/Latest score 75 percent/);
    await expect(trend.locator("circle")).toHaveCount(3);
    const values = await trend.locator("circle title").allTextContents();
    expect(values[0]).toContain("0/5 · 0%");
    expect(values[1]).toContain("2/2 · 100%");
    expect(values[2]).toContain("3/4 · 75%");
    await trend.locator("summary").click();
    await expect(trend.locator("li")).toHaveCount(3);
    for (const width of [375, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(2);
      const results = await new AxeBuilder({ page }).analyze();
      expect(results.violations.filter(item => item.impact === "serious" || item.impact === "critical")).toEqual([]);
      await page.screenshot({ path: info.outputPath(`assessment-scores-${palette}-${width}.png`), fullPage: true });
    }
  }
});

test("unsubmitted assessments do not create a fake score trend", async ({ page }) => {
  await fixture(page, []);
  await page.goto("/app/assess");
  await expect(page.getByText("Take test", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Assessment scores" })).toHaveCount(0);
});

test("a failed assessment list can recover through Try again", async ({ page }) => {
  await fixture(page, []);
  let failed = true;
  await page.route("**/api/v1/assessments?**", async route => {
    if (!failed) return route.fallback();
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Unavailable" }) });
  });
  await page.goto("/app/assess");
  await expect(page.getByRole("alert").filter({ hasText: "Could not load your assessments" })).toBeVisible();
  failed = false;
  await page.getByRole("button", { name: "Try again", exact: true }).click();
  await expect(page.getByText("Take test", { exact: true })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "Could not load your assessments" })).toHaveCount(0);
});
