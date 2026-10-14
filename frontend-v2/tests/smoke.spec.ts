import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { createUser, randomUser, signInAndOnboard, waitForHome, type TestUser } from "./helpers";

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
  console.log(
    `${name}: ${results!.violations.length} violations (${serious.length} serious, ${critical.length} critical)`,
  );
  expect(critical, `critical on ${name}: ${critical.map((v) => v.id).join(", ")}`).toEqual([]);
  expect(serious, `serious on ${name}: ${serious.map((v) => v.id).join(", ")}`).toEqual([]);
}

test("landing route renders and is accessible", async ({ page, baseURL }) => {
  await page.goto("/");
  await expect(page.getByText("NEXT-GEN AI COMPANION", { exact: false }).first()).toBeVisible();
  await expect(page).toHaveURL(new URL("/", baseURL).href);
  await page.waitForLoadState("networkidle");
  await noSeriousAxe(page, "landing");
});

test("auth page renders and is accessible", async ({ page }) => {
  await page.goto("/signin");
  await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
  await expect(page.getByRole("main")).toHaveCount(1);
  await noSeriousAxe(page, "signin");
});

test("signup (via api) -> signin -> onboarding -> create context -> app works", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await waitForHome(page);
  await page.waitForLoadState("networkidle");
  await noSeriousAxe(page, "app");
});
