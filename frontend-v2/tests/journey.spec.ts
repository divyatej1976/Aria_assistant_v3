import { expect, test } from "@playwright/test";
import {
  activeContextId,
  authedApi,
  createUser,
  randomUser,
  seedResource,
  signInAndOnboard,
  type TestUser,
  answerQuiz,
} from "./helpers";

/**
 * Full learner journey in one continuous flow:
 * signup -> onboarding -> material -> learn -> planner -> assess ->
 * materials/audio -> progress/map -> notifications -> account.
 */
test("full journey: signup to account across every feature", async ({ page }) => {
  test.setTimeout(420_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user); // signup -> onboarding -> context -> dashboard

  // ---- study material (API-seeded; UI path covered by materials.spec) ----
  const contextId = await activeContextId(page);
  const api = await authedApi(user);
  await seedResource(api, contextId);

  // ---- learn: ask the tutor and get a reply ----
  await page.goto("/app/learn");
  const input = page.getByPlaceholder("Ask ARIA anything…");
  await input.waitFor({ state: "visible", timeout: 20_000 });
  await input.fill("Explain Python functions");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.locator(".msg-aria .mh-name").first()).toBeVisible({ timeout: 60_000 });

  // ---- planner: create and complete a task ----
  await page.goto("/app/planner");
  await page.getByRole("button", { name: /Task planning/i }).waitFor({ state: "visible", timeout: 20_000 });
  await page.getByRole("button", { name: /Task planning/i }).click();
  await page.getByRole("button", { name: /Create task/i }).click();
  await page.getByLabel(/Task name/i).fill("Journey Task");
  await page.locator(".modal").getByRole("button", { name: /^Create/i }).click();
  await page.locator(".modal").waitFor({ state: "hidden", timeout: 10_000 });
  await expect(page.getByText("Journey Task").first()).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: "Complete Journey Task" }).click();

  // ---- assess: create, take, submit, review ----
  await page.goto("/app/assess");
  await page.getByRole("button", { name: /Create assessment/i }).first().click();
  await page.getByRole("dialog", { name: "Create assessment" }).getByRole("button", { name: "5", exact: true }).click();
  await page.getByRole("button", { name: "Start quiz" }).click();
  expect(await answerQuiz(page)).toBe(5);
  await expect(page.getByText(/You answered \d+ of \d+ questions correctly\./)).toBeVisible();

  // ---- materials: generate a note from the chat session + download PDF ----
  await page.goto("/app/materials");
  await page.getByRole("heading", { name: "Library", exact: true }).waitFor({ state: "visible", timeout: 20_000 });
  await page.getByRole("button", { name: /Generate notes/i }).first().click();
  const sessionValue = await page.locator("#note-source option").nth(1).getAttribute("value");
  expect(sessionValue).toBeTruthy();
  await page.getByLabel("Source").selectOption(sessionValue!);
  await page.getByRole("button", { name: /Generate notes/i }).last().click();
  const noteTitle = "Database Management Systems — Study notes";
  await expect(page.getByText(noteTitle).first()).toBeVisible({ timeout: 30_000 });
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: /Download .*Study notes/i }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/\.pdf$/i);

  // ---- audio: convert the note, play it, pause it ----
  await page.goto("/app/audio");
  await page.getByRole("button", { name: /Convert to audio/i }).first().click();
  await page.getByLabel("Create from", { exact: true }).selectOption("saved");
  const noteValue = await page.locator("#audio-source option").nth(1).getAttribute("value");
  expect(noteValue).toContain("note:");
  await page.getByLabel("Source").selectOption(noteValue!);
  await page.getByRole("button", { name: /Create audio/i }).last().click();
  const recording = page.locator(".audio-card").filter({ hasText: noteTitle });
  await expect(recording).toBeVisible({ timeout: 30_000 });
  await expect(recording.getByText(/^READY(?:\s|$)/)).toBeVisible({ timeout: 30_000 });
  await recording.getByRole("button", { name: /Play NOTE audio/i }).click();
  await expect(page.locator("audio").first()).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: /Pause/i }).click();
  await expect(page.locator("audio")).toHaveCount(0);

  // ---- progress + knowledge map reflect the activity ----
  await page.goto("/app/progress");
  await expect(page.getByText("Current streak").first()).toBeVisible({ timeout: 20_000 });
  // the recorded assessment shows up in Recent activity
  await expect(page.getByText("Assessment", { exact: true }).first()).toBeVisible({ timeout: 20_000 });

  await page.goto("/app/map");
  await page.getByRole("heading", { name: "Topic map" }).waitFor({ state: "visible", timeout: 20_000 });
  await expect(page.locator(".concept-node").first()).toBeVisible({ timeout: 20_000 });

  // ---- notifications: assessment result landed in the bell ----
  await page.goto("/app/account"); // leave map so badge refetches on next load
  await page.goto("/app");
  const badge = page.locator(".bell-btn .badge");
  await expect(badge).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: "Notifications" }).click();
  await expect(page.locator(".notif-item").first()).toBeVisible({ timeout: 20_000 });

  // ---- account: real identity ----
  await page.goto("/app/account");
  await expect(page.getByLabel("Email")).toHaveValue(user.email, { timeout: 20_000 });

  void api;
  await api.dispose();
});
