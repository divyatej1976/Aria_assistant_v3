import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function noAxeViolations(page: Page, name: string) {
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter(
    (violation) => violation.impact === "serious",
  );
  const critical = results.violations.filter(
    (violation) => violation.impact === "critical",
  );
  console.log(
    `${name}: ${results.violations.length} violations (${serious.length} serious, ${critical.length} critical)`,
  );
  expect(
    critical,
    `${name} critical violations: ${critical.map((v) => v.id).join(", ")}`,
  ).toEqual([]);
  expect(
    serious,
    `${name} serious violations: ${serious.map((v) => v.id).join(", ")}`,
  ).toEqual([]);
}

test("landing page loads and has no critical axe violations", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Master any subject/ })).toBeVisible();
  await noAxeViolations(page, "landing");
});

test("sign-in page has no critical axe violations", async ({ page }) => {
  await page.goto("/signin");
  await expect(page.getByRole("button", { name: /Sign in/ })).toBeVisible();
  await noAxeViolations(page, "signin");
});

test("sign-up page has no critical axe violations", async ({ page }) => {
  await page.goto("/signup");
  await expect(page.getByRole("button", { name: /Create account/ })).toBeVisible();
  await noAxeViolations(page, "signup");
});

test("signup -> onboarding -> app flow works", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;
  await page.goto("/signup");
  await page.getByLabel("Display name").fill("E2E Learner");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct-horse");
  await page.getByRole("button", { name: /Create account/ }).click();
  await page.waitForURL("**/onboarding");

  await page.getByLabel("Primary Learning Vector").fill("DBMS");
  await page.getByRole("button", { name: /Start Journey/ }).click();
  await page.waitForURL("**/app");

  await expect(page.getByRole("heading", { name: "Mission Control" })).toBeVisible();
  await noAxeViolations(page, "app");
});
