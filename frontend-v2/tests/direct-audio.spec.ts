import { expect, test } from "@playwright/test";
import path from "path";
import { activeContextId, authedApi, createUser, randomUser, signInAndOnboard } from "./helpers";

test("create audio from text without materials and restore its saved source", async ({ page }, testInfo) => {
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  await page.goto("/app/audio");
  await page.getByRole("button", { name: "Convert to audio" }).first().click();
  await expect(page.getByLabel("Create from", { exact: true })).toHaveValue("text");
  await expect(page.getByRole("button", { name: "Create audio", exact: true })).toBeDisabled();
  await page.getByLabel("Episode title (optional)").fill("My direct episode");
  await page.getByLabel("Text to read aloud").fill("A stack follows last in, first out. Push adds an item and pop removes the latest item.");
  await page.screenshot({ path: testInfo.outputPath("paste-text.png") });
  await page.setViewportSize({width: 375, height: 812});
  await page.screenshot({ path: testInfo.outputPath("paste-text-mobile.png") });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("button", { name: "Create audio", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0, { timeout: 120000 });
  await expect(page.locator(".audio-card").filter({ hasText: "My direct episode" })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "View saved source" }).click();
  await expect(page.getByRole("dialog", { name: "Saved audio source" })).toContainText("A stack follows last in, first out.");
});

test("upload an image directly in Audio studio", async ({ page }) => {
  test.setTimeout(150000);
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  await page.goto("/app/audio");
  await page.getByRole("button", { name: "Convert to audio" }).first().click();
  await page.getByLabel("Create from", { exact: true }).selectOption("file");
  await page.getByLabel("PDF or image (up to 10 MB)").setInputFiles(path.resolve(__dirname, "../test-assets/sample_ocr_notes.png"));
  await page.getByRole("button", { name: "Create audio", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0, { timeout: 120000 });
  await expect(page.locator(".audio-card").filter({hasText: "sample_ocr_notes.png"})).toBeVisible();
  await page.getByRole("button", {name: "View saved source"}).click();
  await expect(page.getByRole("dialog", {name: "Saved audio source"})).toContainText(/CAP|Consistency/i);
});

test("a chat picked in Audio studio becomes a durable episode", async ({ page }) => {
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  await page.goto("/app/learn");
  await expect(page.getByRole("button", { name: /Create audio/ })).toHaveCount(0);
  await page.getByPlaceholder("Ask ARIA anything…").fill("Explain stacks briefly.");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator("article.msg-aria").first()).toBeVisible({ timeout: 60000 });
  await page.goto("/app/audio");
  await page.getByRole("button", { name: "Convert to audio" }).first().click();
  await page.getByLabel("Create from", { exact: true }).selectOption("chat");
  const chat = page.getByLabel("Chat", { exact: true });
  await expect(chat.locator("option")).toHaveCount(2);
  await chat.selectOption({ index: 1 });
  await page.getByRole("button", { name: "Create audio", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0, { timeout: 120000 });
  await expect(page.locator(".audio-card").filter({ hasText: "Chat: Explain stacks briefly." })).toBeVisible();
  const api = await authedApi(user);
  const cid = await activeContextId(page);
  const listed = await api.get(`/api/v1/audio?context_id=${cid}`);
  expect((await listed.json()).length).toBe(1);
  await api.dispose();
});

test("generation errors retain the pasted draft for retry", async ({ page }) => {
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  await page.route("**/api/v1/audio/text/generate", route => route.fulfill({status: 422, contentType: "application/json", body: JSON.stringify({detail: "Please retry audio creation."})}));
  await page.goto("/app/audio");
  await page.getByRole("button", { name: "Convert to audio" }).first().click();
  await page.getByLabel("Text to read aloud").fill("Keep this draft.");
  await page.getByRole("button", { name: "Create audio", exact: true }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText("Please retry audio creation.");
  await expect(page.getByLabel("Text to read aloud")).toHaveValue("Keep this draft.");
  await expect(page.getByRole("button", { name: "Create audio", exact: true })).toBeEnabled();
});
