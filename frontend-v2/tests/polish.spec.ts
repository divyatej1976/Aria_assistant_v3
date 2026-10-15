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

const APP_ROUTES = [
  "/app",
  "/app/learn",
  "/app/planner",
  "/app/assess",
  "/app/materials",
  "/app/audio",
  "/app/map",
  "/app/roadmaps",
  "/app/progress",
  "/app/account",
];

/** A stable, route-specific element that proves data has rendered before axe runs. */
const LANDMARKS: Record<string, string> = {
  "/app": '[data-home-ready="true"]',
  "/app/learn": 'input[placeholder="Ask ARIA anything…"]',
  "/app/planner": 'button:has-text("Exams")',
  "/app/assess": 'button:has-text("Create assessment")',
  "/app/materials": "text=Generated from your learning",
  "/app/audio": 'button:has-text("Convert to audio")',
  "/app/map": 'h1:has-text("Topic map")',
  "/app/roadmaps": 'button:has-text("Create roadmap")',
  "/app/progress": 'h1:has-text("Your progress")',
  "/app/account": 'h1:has-text("Account & settings")',
};

const AUTH_ROUTES = ["/signin", "/signup", "/verify-email", "/reset-password"];

test("axe sweep across every app route", async ({ page }) => {
  test.setTimeout(600_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  for (const route of APP_ROUTES) {
    await page.goto(route);
    // a stable, route-specific landmark before running axe
    await page.locator(LANDMARKS[route]).first().waitFor({ state: "visible", timeout: 20_000 });
    await noSeriousAxe(page, route);
  }
});

test("axe sweep across auth routes", async ({ page }) => {
  test.setTimeout(180_000);
  for (const route of AUTH_ROUTES) {
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    await noSeriousAxe(page, route);
  }
});

test("responsive sweep: no horizontal overflow across 5 breakpoints x 2 palettes", async ({ page }) => {
  test.setTimeout(300_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const sizes = [
    { width: 1440, height: 900 },
    { width: 1024, height: 768 },
    { width: 768, height: 1024 },
    { width: 375, height: 812 },
    { width: 320, height: 700 },
  ];
  const routes = ["/app", "/app/materials", "/app/progress", "/app/planner"];
  const palettes = ["aurora", "noir"] as const;

  for (const palette of palettes) {
    // switch palette through the app's own persistence key
    await page.evaluate((p) => {
      window.localStorage.setItem("aria.palette", p);
      window.localStorage.setItem("aria.gold", "0");
    }, palette);
    for (const size of sizes) {
      await page.setViewportSize(size);
      for (const route of routes) {
        await page.goto(route);
        await page.waitForLoadState("networkidle");
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        if (overflow > 2) {
          const offenders = await page.evaluate(() => {
            const vw = document.documentElement.clientWidth;
            const describe = (el: HTMLElement): string => {
              const path: string[] = [];
              let cur: HTMLElement | null = el;
              for (let depth = 0; cur && depth < 4; depth++) {
                const cls =
                  typeof cur.className === "string" && cur.className
                    ? "." + cur.className.split(" ")[0]
                    : "";
                path.unshift(`${cur.tagName.toLowerCase()}${cls}${cur.id ? "#" + cur.id : ""}`);
                cur = cur.parentElement;
              }
              return `${path.join(" < ")} w=${Math.round(el.getBoundingClientRect().width)}`;
            };
            return Array.from(document.querySelectorAll<HTMLElement>("body *"))
              .filter((el) => {
                const rect = el.getBoundingClientRect();
                if (rect.right <= vw + 2 || el.offsetParent === null) return false;
              // elements inside a horizontally scrollable strip are contained
              if (el.closest(".mobile-nav")) return false;
                let cur: HTMLElement | null = el;
                while (cur) {
                  if (getComputedStyle(cur).position === "fixed") return false;
                  cur = cur.parentElement;
                }
                return true;
              })
              .slice(0, 6)
              .map(describe);
          });
          expect(
            overflow,
            `overflow ${overflow}px on ${route} @${size.width}x${size.height} (${palette}); offenders: ${offenders.join(" | ")}`,
          ).toBeLessThanOrEqual(2);
        }
      }
    }
  }
});

test("dashboard performance sanity", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const started = Date.now();
  await page.goto("/app");
  await page.locator('[data-home-ready="true"]').waitFor({ state: "visible", timeout: 20_000 });
  await expect(page.locator(".home .learning-hero").first()).toBeVisible({ timeout: 20_000 });
  const elapsed = Date.now() - started;
  // generous ceiling: guards against pathological regressions, not micro-tuning
  expect(elapsed, `dashboard took ${elapsed}ms to become interactive`).toBeLessThan(20_000);
});