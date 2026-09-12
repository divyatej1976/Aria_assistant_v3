import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import {
  activeContextId,
  authedApi,
  createUser,
  randomUser,
  signInAndOnboard,
  type TestUser,
} from "./helpers";

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
  expect(critical, `critical on ${name}`).toEqual([]);
  expect(serious, `serious on ${name}`).toEqual([]);
}

/** Seed a chat session with one message via the real API (same flow learn.spec relies on). */
async function seedChat(api: Awaited<ReturnType<typeof authedApi>>, contextId: string): Promise<string> {
  const session = await api.post("/api/v1/study/sessions", { data: { context_id: contextId, mode: "CHAT" } });
  expect(session.ok(), `session create failed: ${session.status()} ${await session.text()}`).toBe(true);
  const created = await session.json();
  const msg = await api.post(`/api/v1/study/sessions/${created.id}/messages`, {
    data: { content: "Explain Python functions and how to write reusable code" },
  });
  expect(msg.ok(), `message failed: ${msg.status()} ${await msg.text()}`).toBe(true);
  return created.id;
}

test("materials page shows empty states for a fresh learner", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/materials");
  await page.getByRole("heading", { name: "Materials Library" }).waitFor({ state: "visible", timeout: 20_000 });

  await expect(page.getByText("No materials yet").first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("No resources yet").first()).toBeVisible({ timeout: 20_000 });
  await page.waitForLoadState("networkidle");
  await noSeriousAxe(page, "materials");
});

test("add a text resource and delete it", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/materials");
  await page.getByRole("heading", { name: "Materials Library" }).waitFor({ state: "visible", timeout: 20_000 });

  await page.getByRole("button", { name: /Add Resource/i }).click();
  await page.getByLabel("Title").fill("Python Study Notes");
  await page.getByLabel("Text").fill(
    "A function is a reusable block of code. def defines a function. Arguments are passed when calling. "
      + "A function returns a value with return. Loops repeat a block while a condition holds.",
  );
  await page.getByRole("button", { name: /Add Resource/i }).last().click();

  await expect(page.getByText("Python Study Notes").first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/chunks/).first()).toBeVisible({ timeout: 20_000 });

  await page.getByRole("button", { name: /Delete Python Study Notes/i }).click();
  await expect(page.getByText("Python Study Notes").first()).toBeHidden({ timeout: 20_000 }).catch(() => {});
});

test("generate a note from a chat session and download the PDF", async ({ page }) => {
  test.setTimeout(150_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const contextId = await activeContextId(page);
  const api = await authedApi(user);
  await seedChat(api, contextId);
  await api.dispose();

  await page.goto("/app/materials");
  await page.getByRole("heading", { name: "Materials Library" }).waitFor({ state: "visible", timeout: 20_000 });

  // generate from the real chat session
  await page.getByRole("button", { name: /Add Material/i }).click();
  const sessionValue = await page.locator("#note-source option").nth(1).getAttribute("value");
  expect(sessionValue).toBeTruthy();
  await page.getByLabel("Source").selectOption(sessionValue!);
  await page.getByRole("button", { name: /Create Material/i }).last().click();

  const noteTitle = "Database Management Systems — Study notes";
  await expect(page.getByText(noteTitle).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("NEW").first()).toBeVisible({ timeout: 20_000 });

  // download produces a real PDF
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: /Download .*Study notes/i }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/\.pdf$/i);
});