import { expect, test } from "@playwright/test";
import { createUser, randomUser, signInAndOnboard } from "./helpers";

test("Quick check turns the current chat into a short practice quiz", async ({ page }) => {
  test.setTimeout(150_000);
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask ARIA anything…").fill("Explain how database indexes speed up queries in detail.");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  const quick = page.locator("article.msg-aria").last().getByRole("link", { name: /Quick check/ });
  await expect(quick).toBeVisible({ timeout: 60_000 });
  await quick.click();

  // Practice opens pre-set to five questions on exactly this chat.
  const setup = page.getByRole("dialog", { name: "Create assessment" });
  await expect(setup.getByRole("radio", { name: "My chats" })).toHaveAttribute("aria-checked", "true");
  await expect(setup.getByRole("checkbox")).toBeChecked();
  await expect(setup.getByRole("radio", { name: /Quick practice/ })).toHaveAttribute("aria-checked", "true");
  await setup.getByRole("button", { name: "Start quiz" }).click();
  await expect(page.getByRole("region", { name: "Quiz" }).getByText(/Question 1 of \d+/)).toBeVisible({ timeout: 60_000 });
});
