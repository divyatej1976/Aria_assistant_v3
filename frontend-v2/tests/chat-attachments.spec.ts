import { expect, test } from "@playwright/test";
import path from "path";
import { createUser, randomUser, signInAndOnboard } from "./helpers";

const QUESTION = "From my notes, what are the three properties in the CAP Theorem?";

test("a file attached in one chat stays in that chat until it is added to the library", async ({ page }) => {
  test.setTimeout(180_000);
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask ARIA anything…").waitFor({ timeout: 20_000 });

  // Attaching before the first message creates the chat and keeps the file in it.
  await page.locator('input[type="file"]').setInputFiles(path.resolve(__dirname, "../test-assets/sample_ocr_notes.png"));
  const chip = page.locator(".chat-files .chat-file").filter({ hasText: "sample_ocr_notes" });
  await expect(chip).toBeVisible({ timeout: 60_000 });
  await page.getByPlaceholder("Ask ARIA anything…").fill(QUESTION);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".msg-aria .source-chip").first()).toBeVisible({ timeout: 60_000 });

  // A new chat neither lists nor uses the file.
  await page.getByRole("button", { name: "New chat" }).click();
  await expect(page.locator(".chat-files")).toHaveCount(0);
  await page.getByPlaceholder("Ask ARIA anything…").fill(QUESTION);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator("article.msg-aria").first()).toBeVisible({ timeout: 60_000 });
  await expect(page.locator(".msg-aria .source-chip")).toHaveCount(0);

  // The Materials library does not list it either.
  await page.goto("/app/materials");
  await expect(page.getByText("No shared files yet")).toBeVisible({ timeout: 20_000 });

  // Adding it to the library from its chat shares it with every chat.
  await page.goto("/app/learn");
  // The first chat is the one whose reply drew on the file.
  await page.locator(".session-item").filter({ hasText: /excerpts from your material/ }).click();
  await expect(chip).toBeVisible({ timeout: 20_000 });
  await chip.getByRole("button", { name: /Add .* to library/ }).click();
  await expect(page.locator(".chat-files")).toHaveCount(0);
  await page.goto("/app/materials");
  await expect(page.getByText("sample_ocr_notes").first()).toBeVisible({ timeout: 20_000 });
});
