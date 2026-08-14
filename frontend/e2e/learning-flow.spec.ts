import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const MATERIAL = [
  "Two-phase locking uses a growth phase and a shrink phase.",
  "Strict two-phase locking releases every lock only at commit time.",
  "A precedence graph detects cycles that indicate non-serializable schedules.",
  "Conflict serializability is a subset of view serializability for most schedules.",
  "Deadlock detection requires waiting for a cycle in the resource wait-for graph.",
].join(" ");

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

test("learning flow: sign in -> context -> resource -> study -> assessment -> progress", async ({
  page,
}) => {
  const email = `flow-${Date.now()}@example.com`;

  // Sign up -> onboarding creates a learning context.
  await page.goto("/signup");
  await page.getByLabel("Display name").fill("Flow Learner");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct-horse");
  await page.getByRole("button", { name: /Create account/ }).click();
  await page.waitForURL("**/onboarding");
  await page.getByLabel("Primary Learning Vector").fill("DBMS");
  await page.getByRole("button", { name: /Start Journey/ }).click();
  await page.waitForURL("**/app");
  await noAxeViolations(page, "app");

  // Add a text resource.
  await page.goto("/app/resources");
  await page.getByRole("button", { name: "Add material" }).click();
  await page.getByLabel("Title").fill("Two-phase locking notes");
  await page.getByLabel("Study text").fill(MATERIAL);
  await page.getByRole("button", { name: "Add material" }).click();
  await expect(page.getByText("Two-phase locking notes")).toBeVisible();
  await noAxeViolations(page, "resources");

  // Study: ask a grounded question.
  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask a question...").fill("What is strict two-phase locking?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(
    page.getByText(/Two-phase locking|strict two-phase locking/i).first(),
  ).toBeVisible({ timeout: 20_000 });
  await noAxeViolations(page, "learn");

  // Assessment: generate, answer, submit, see results.
  await page.goto("/app/assess");
  await page.getByRole("button", { name: "Generate assessment" }).click();
  await expect(page.getByRole("button", { name: "Next" })).toBeVisible({ timeout: 30_000 });
  for (;;) {
    await page.locator("ul li button").first().click();
    const next = page.getByRole("button", { name: "Next" });
    if (await next.isVisible()) {
      await next.click();
    } else {
      await page.getByRole("button", { name: "Submit assessment" }).click();
      break;
    }
  }
  await page.getByRole("button", { name: "Submit" }).last().click();
  await expect(page.getByText(/\d+ \/ \d+ correct/)).toBeVisible({ timeout: 20_000 });
  await noAxeViolations(page, "assess");

  // Progress reflects the completed loop.
  await page.getByRole("link", { name: "Progress" }).first().click();
  await expect(page.getByRole("heading", { name: /Progress/i })).toBeVisible();
  await noAxeViolations(page, "progress");
});
