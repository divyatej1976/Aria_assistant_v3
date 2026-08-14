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
  expect(critical, `${name} critical: ${critical.map((v) => v.id).join(", ")}`).toEqual([]);
  expect(serious, `${name} serious: ${serious.map((v) => v.id).join(", ")}`).toEqual([]);
}

test("planner: add an exam and a task with collapsible forms", async ({ page }) => {
  const email = `planner-${Date.now()}@example.com`;

  await page.goto("/signup");
  await page.getByLabel("Display name").fill("Planner Learner");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct-horse");
  await page.getByRole("button", { name: /Create account/ }).click();
  await page.waitForURL("**/onboarding");
  await page.getByLabel("Primary Learning Vector").fill("DBMS");
  await page.getByRole("button", { name: /Start Journey/ }).click();
  await page.waitForURL("**/app");

  await page.getByRole("link", { name: "Planner" }).first().click();

  // The mutating POSTs below need the CSRF cookie applied from signup.
  await expect
    .poll(() => page.evaluate(() => document.cookie.includes("aria_csrf=")))
    .toBe(true);

  // Add an exam via the collapsible form.
  await page.getByRole("button", { name: "Add exam" }).click();
  await page.getByLabel("Exam title").fill("DBMS End Sem");
  await page.getByLabel("Due date").fill("2027-06-01");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByText("DBMS End Sem")).toBeVisible();

  // Close the exam form, then add a dated task.
  await page.getByRole("button", { name: "Close" }).click();
  await page.getByRole("button", { name: "Add task" }).click();
  await page.getByLabel("Task title").fill("Revise serializability");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByText("Revise serializability")).toBeVisible();

  await noAxeViolations(page, "planner");
});
