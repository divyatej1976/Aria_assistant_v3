import { expect, test } from "@playwright/test";
import { createUser, randomUser, signInAndOnboard } from "./helpers";

test("first visit asks one question, then home turns into continue-learning", async ({ page }) => {
  test.setTimeout(120_000);
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  // First visit: a greeting by name, one question box, and progress at a glance.
  await expect(page.getByRole("heading", { level: 1, name: /^(Good morning|Good afternoon|Good evening|Up late|Hi)/ })).toBeVisible();
  await expect(page.getByLabel("Your question")).toBeVisible();
  await expect(page.getByRole("img", { name: /of concepts strong/ })).toHaveCount(0);

  // Asking from Home opens a chat and sends the question straight away.
  await page.getByLabel("Your question").fill("What is a primary key?");
  await page.getByRole("button", { name: /^Ask/ }).click();
  await expect(page).toHaveURL(/\/app\/learn/);
  await expect(page.locator(".msg-user").filter({ hasText: "What is a primary key?" })).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("article.msg-aria").first()).toBeVisible({ timeout: 60_000 });
  await expect(page).not.toHaveURL(/autosend/);

  // Back home: the last chat is one tap away and counted.
  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "Continue learning", exact: true })).toBeVisible({ timeout: 20_000 });
  const open = page.getByRole("link", { name: /Open this chat/ });
  await expect(open).toHaveAttribute("href", /\/app\/learn\?session=/);
  await expect(page.getByRole("list", { name: "Your progress at a glance" }).getByRole("listitem").filter({ hasText: "chat" })).toContainText("1");
  await open.click();
  await expect(page.locator(".msg-user").filter({ hasText: "What is a primary key?" })).toBeVisible({ timeout: 20_000 });
});
