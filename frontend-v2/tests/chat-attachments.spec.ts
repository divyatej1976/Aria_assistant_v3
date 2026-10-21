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

  // A picked file waits in the input bar and goes with the message, like ChatGPT or Claude.
  await page.locator('input[type="file"]').setInputFiles(path.resolve(__dirname, "../test-assets/sample_ocr_notes.png"));
  await expect(page.locator(".pending-file").filter({ hasText: "sample_ocr_notes" })).toBeVisible();
  await page.getByPlaceholder("Ask ARIA anything…").fill(QUESTION);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".pending-file")).toHaveCount(0);
  await expect(page.locator(".msg-file").filter({ hasText: "sample_ocr_notes" })).toBeVisible();
  await expect(page.locator(".msg-aria .source-chip").first()).toBeVisible({ timeout: 60_000 });
  // Reopened later, the chat lists its file with a way to share it.
  const chip = page.locator(".chat-files .chat-file").filter({ hasText: "sample_ocr_notes" });

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
  // Both chats asked the same question; the list is newest first, so the file's chat is last.
  await page.locator(".session-item").last().click();
  await expect(chip).toBeVisible({ timeout: 20_000 });
  await chip.getByRole("button", { name: /Add .* to library/ }).click();
  await expect(page.locator(".chat-files")).toHaveCount(0);
  await page.goto("/app/materials");
  await expect(page.getByText("sample_ocr_notes").first()).toBeVisible({ timeout: 20_000 });
});

test("Send turns into Stop while ARIA replies, and a stopped reply is not kept", async ({ page }) => {
  test.setTimeout(120_000);
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  let stopped = false;
  await page.route("**/api/v1/study/sessions/*/messages/stream", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await new Promise((resolve) => setTimeout(resolve, 8_000));
    await route.fallback().catch(() => {});
  });
  await page.route("**/api/v1/study/sessions/*/messages/*/stop", async (route) => { stopped = true; await route.fallback(); });
  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask ARIA anything…").fill("Explain normalization");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  const stop = page.getByRole("button", { name: "Stop", exact: true });
  await expect(stop).toBeVisible();
  await stop.click();
  await expect(page.getByText("You stopped this reply.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeVisible();
  await expect.poll(() => stopped).toBe(true);
});
