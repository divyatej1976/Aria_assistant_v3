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

/** Create a note directly via API so the audio page has a real source to convert. */
async function seedNote(api: Awaited<ReturnType<typeof authedApi>>, contextId: string): Promise<void> {
  const res = await api.post("/api/v1/notes", {
    data: {
      context_id: contextId,
      title: "Python Functions Audio Notes",
      body: "A function is a reusable block of code. def defines a function. Arguments are passed when calling. ",
    },
  });
  expect(res.ok(), `note create failed: ${res.status()} ${await res.text()}`).toBe(true);
}

test("audio page shows empty state and lists available sources", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/audio");
  await page.getByRole("heading", { name: "Audio studio" }).waitFor({ state: "visible", timeout: 20_000 });

  await expect(page.getByText("No audio yet").first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Available sources").first()).toBeVisible({ timeout: 20_000 });
  await page.waitForLoadState("networkidle");
  await noSeriousAxe(page, "audio");
});

test("convert a note to audio, save progress, and restore it after reload", async ({ page }) => {
  test.setTimeout(150_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const contextId = await activeContextId(page);
  const api = await authedApi(user);
  await seedNote(api, contextId);
  await api.dispose();

  await page.goto("/app/audio");
  await page.getByRole("heading", { name: "Audio studio" }).waitFor({ state: "visible", timeout: 20_000 });

  // open the convert modal and pick the note source
  await page.getByRole("button", { name: /Convert to audio/i }).first().click();
  await page.getByLabel("Create from", { exact: true }).selectOption("saved");
  const noteValue = await page.locator("#audio-source option").nth(1).getAttribute("value");
  expect(noteValue).toContain("note:");
  await page.getByLabel("Source").selectOption(noteValue!);
  await page.getByRole("button", { name: /Create audio/i }).last().click();

  // artifact card with real READY status appears
  await expect(page.getByText("Python Functions Audio Notes").first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/READY/).first()).toBeVisible({ timeout: 20_000 });

  // play: an <audio> element is inserted
  await page.getByRole("button", { name: /Play NOTE audio/i }).click();
  await expect(page.locator("audio").first()).toBeVisible({ timeout: 20_000 });
  // pause so the live timer doesn't rewrite progress underneath us
  await page.getByRole("button", { name: /Pause/i }).click();
  await expect(page.locator("audio")).toHaveCount(0);

  // simulate progress via the same PUT endpoint the UI uses, then reload
  // (artifact id comes from the durable server-side list, not localStorage)
  const api2 = await authedApi(user);
  const listed = await api2.get(`/api/v1/audio?context_id=${contextId}`);
  expect(listed.ok(), `audio list failed: ${listed.status()}`).toBe(true);
  const artifactId = ((await listed.json()) as Array<{ id: string }>)[0]?.id ?? "";
  expect(artifactId).toBeTruthy();

  const prog = await api2.put(`/api/v1/audio/${artifactId}/progress`, { data: { position_seconds: 42, completed: false } });
  expect(prog.ok(), `progress save failed: ${prog.status()}`).toBe(true);
  await api2.dispose();

  // reload: artifact restored from the server list with the saved resume position
  await page.reload();
  await page.getByRole("heading", { name: "Audio studio" }).waitFor({ state: "visible", timeout: 20_000 });
  await expect(page.getByText("Resume 0:42").first()).toBeVisible({ timeout: 30_000 });
});
