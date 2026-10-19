import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFileSync } from "node:fs";
import ts from "typescript";

const context = { id: "polish-context", title: "Database Management Systems", status: "active" };
const roadmap = {
  id: "polish-roadmap", goal: "Understand databases", level: "Beginner", status: "ACTIVE",
  generation_mode: "ai", total: 4, done: 1,
  tiers: [
    { name: "Foundation", icon: "book", topics: [
      { id: "keys", title: "Tables and primary keys", prerequisites: [], state: "SUPPORTED", confidence: 80, ticked: true },
      { id: "normalization", title: "Normalization and functional dependencies", prerequisites: ["Tables and primary keys"], state: "DEVELOPING", confidence: 45, ticked: false },
    ] },
    { name: "Advanced topics", icon: "target", topics: [
      { id: "transactions", title: "Transactions", prerequisites: ["Normalization and functional dependencies"], state: "NOT_STARTED", confidence: 0, ticked: false },
      { id: "indexing", title: "Index design", prerequisites: [], state: "NOT_STARTED", confidence: 0, ticked: false },
    ] },
  ],
};

async function fixture(page: Page, ready = false) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  let sessionCreated = false;
  const session = { id: "polish-session", context_id: context.id, mode: "BASELINE", status: "ACTIVE", created_at: "2026-10-14T10:00:00Z", message_count: 2 };
  await page.route("**/api/v1/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = [];
    if (path === "/api/v1/auth/me") body = { id: "polish-user", email: "learner@example.com", verified: true };
    else if (path === "/api/v1/contexts") body = [context];
    else if (path.endsWith("/unread-count")) body = { unread: 0 };
    else if (path.endsWith("/consistency")) body = { current_streak: 0, today_active: false };
    else if (path.endsWith("/adaptation")) body = { states: [], decisions: [] };
    else if (path === "/api/v1/roadmaps") body = [roadmap];
    else if (path === "/api/v1/roadmaps/polish-roadmap") body = roadmap;
    else if (path === "/api/v1/resources" && ready) body = [{ id: "resource", title: "Lecture notes", resource_type: "TEXT", processing_status: "READY" }];
    else if (path === "/api/v1/settings/capabilities") body = { cloud_speech_configured: false, personal_keys_enabled: false };
    else if (path === "/api/v1/study/sessions" && route.request().method() === "POST") { sessionCreated = true; body = session; }
    else if (path === "/api/v1/study/sessions") body = sessionCreated ? [session] : [];
    await route.fulfill({ contentType: "application/json", headers: {
      "Access-Control-Allow-Origin": route.request().headers().origin ?? "http://localhost:3130",
      "Access-Control-Allow-Credentials": "true", "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type,X-CSRF-Token",
    }, body: JSON.stringify(body) });
  });
}

test("tutor retry reuses the request and keeps one question bubble", async ({ page }) => {
  await fixture(page);
  const requests: { content: string; request_id: string }[] = [];
  await page.route("**/study/sessions/polish-session/messages", async route => {
    requests.push(route.request().postDataJSON());
    await route.fulfill({ status: requests.length === 1 ? 503 : 200, contentType: "application/json",
      body: JSON.stringify(requests.length === 1 ? { detail: "The tutor is temporarily unavailable. Try again." } : { role: "assistant", content: "A primary key identifies each row uniquely.", sources: [] }) });
  });
  await page.goto("/app/learn");
  const input = page.getByPlaceholder("Ask ARIA anything…");
  await input.fill("Explain primary keys");
  await input.press("Enter");
  await expect(page.getByRole("alert").filter({ hasText: "Reply unavailable" })).toContainText("temporarily unavailable");
  await page.getByRole("button", { name: "Retry reply" }).click();
  await expect(page.getByText("A primary key identifies each row uniquely.", { exact: true })).toBeVisible();
  expect(requests).toHaveLength(2);
  expect(requests[1]).toEqual(requests[0]);
  expect(requests[0].request_id).toMatch(/^[0-9a-f-]{36}$/);
  await expect(page.getByText("Explain primary keys", { exact: true })).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Retry reply" })).toHaveCount(0);
  const focus = page.getByRole("button", { name: "Focus mode", exact: true });
  await focus.click();
  await expect(page.getByRole("button", { name: "Exit focus" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("navigation", { name: "Workspace", exact: true })).not.toBeVisible();
  await page.getByRole("button", { name: "Exit focus" }).click();
  await expect(page.getByRole("navigation", { name: "Workspace", exact: true })).toBeVisible();
});

test("assessment types have friendly names and distinct badges", async ({ page }) => {
  await fixture(page);
  await page.route("**/api/v1/assessments?**", route => route.fulfill({ contentType: "application/json", body: JSON.stringify(["BASELINE", "DAILY_REVIEW", "TARGETED", "RETEST_TARGETED"].map(mode => ({ id: mode, context_id: context.id, format: "mcq", mode, status: "READY", question_count: 3, created_at: "2026-10-14T10:00:00Z" }))) }));
  await page.goto("/app/assess");
  for (const label of ["Practice", "Daily Review", "Targeted Practice", "Targeted Review"]) await expect(page.locator(".route-view").getByText(label, { exact: true }).last()).toBeVisible();
  const colours = await page.locator(".assessment-kind").evaluateAll(elements => elements.map(element => getComputedStyle(element).backgroundColor));
  expect(new Set(colours).size).toBe(4);
  expect((await new AxeBuilder({ page }).analyze()).violations.filter(issue => issue.impact === "serious" || issue.impact === "critical")).toEqual([]);
});

test("roadmap tiles stay readable, reveal prerequisites, and prefill the tutor", async ({ page }, info) => {
  await fixture(page);
  await page.goto("/app/roadmaps");
  await expect(page.locator(".roadmap-summary")).toContainText("1 / 4 completed");
  await expect(page.locator(".roadmap-topic-card.completed")).toHaveCount(1);
  await expect(page.locator(".roadmap-topic-card.in-progress")).toHaveCount(1);
  const collapsed = page.getByRole("button", { name: /Advanced topics/ });
  await expect(collapsed).toContainText("Transactions · Index design");
  await collapsed.click();
  await expect(page.locator(".roadmap-topic-card.prerequisite-pending")).toHaveCount(1);
  for (const width of [320, 375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    const dimensions = await page.locator(".roadmap-topic-card").evaluateAll(tiles => tiles.map(tile => {
      const box = tile.getBoundingClientRect();
      return { width: box.width, height: box.height, clipped: tile.scrollHeight > tile.clientHeight + 2 };
    }));
    expect(dimensions.length).toBe(4);
    for (const tile of dimensions) { expect(Math.abs(tile.width - tile.height)).toBeLessThan(3); expect(tile.clipped).toBe(false); }
    const trail = page.locator(".milestone-next");
    const trailSize = await trail.evaluate(element => ({ display: getComputedStyle(element).display, columns: getComputedStyle(element).gridTemplateColumns, scroll: element.scrollWidth, client: element.clientWidth }));
    await info.attach(`trail-${width}`, { body: JSON.stringify(trailSize), contentType: "application/json" });
    expect(trailSize.scroll - trailSize.client, JSON.stringify(trailSize)).toBeLessThanOrEqual(2);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(2);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await page.screenshot({ path: info.outputPath(`roadmap-${width}.png`), fullPage: true });
  }
  await page.getByRole("button", { name: "Dismiss roadmap information" }).click();
  await page.reload();
  await expect(page.getByText("About this learning path", { exact: true })).toHaveCount(0);
  await expect(page.getByText("AI-generated curriculum", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "View Normalization and functional dependencies details" }).click();
  await page.getByRole("link", { name: "Study this milestone" }).click();
  await expect(page.getByPlaceholder("Ask ARIA anything…")).toHaveValue("Help me learn Normalization and functional dependencies. Start with a clear explanation and an example.");
  await page.goto("/app/roadmaps");
  await page.getByRole("link", { name: "Study Tables and primary keys", exact: true }).click();
  await expect(page.getByPlaceholder("Ask ARIA anything…")).toHaveValue("Help me learn Tables and primary keys. Start with a clear explanation and an example.");
});

test("note generation keeps conversation selection and shows failures inside the modal", async ({ page }) => {
  await fixture(page);
  await page.route("**/api/v1/study/sessions?**", route => route.fulfill({ contentType: "application/json", body: JSON.stringify([{ id: "conversation", message_count: 2, created_at: "2026-10-14T10:00:00Z" }]) }));
  await page.route("**/api/v1/notes/generate", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Notes are temporarily unavailable. Please try again." }) }));
  await page.goto("/app/materials");
  await page.getByRole("button", { name: "Generate notes", exact: true }).first().click();
  const modal = page.getByRole("dialog", { name: "Generate notes" });
  await modal.getByLabel("Source", { exact: true }).selectOption("conversation");
  await modal.getByRole("button", { name: "Generate notes", exact: true }).click();
  await expect(modal.getByRole("alert")).toContainText("temporarily unavailable");
  await expect(modal.getByLabel("Source", { exact: true })).toHaveValue("conversation");
  await expect(modal.getByRole("button", { name: "Generate notes", exact: true })).toBeEnabled();
});

test("streaming replies follow the latest message without pulling an earlier reading position", async ({ page }) => {
  await fixture(page);
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.route("**/study/sessions/polish-session/messages", route => route.fulfill({ contentType: "application/json", body: JSON.stringify({ role: "assistant", content: "A primary key identifies each row uniquely. ".repeat(70) + "End of explanation.", sources: [] }) }));
  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask ARIA anything…").fill("Explain primary keys");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".msg-aria").last()).toContainText("End of explanation.", { timeout: 30_000 });
  const chat = page.locator(".chat-body");
  await expect.poll(() => chat.evaluate(element => element.scrollHeight - element.scrollTop - element.clientHeight)).toBeLessThan(90);
  await page.getByPlaceholder("Ask ARIA anything…").fill("Explain another example");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".msg-aria")).toHaveCount(2);
  await chat.evaluate(element => { element.scrollTop = 0; element.dispatchEvent(new Event("scroll")); });
  await expect(page.getByRole("button", { name: "Scroll to the latest message" })).toBeVisible();
  await expect(page.locator(".msg-aria").last()).toContainText("End of explanation.", { timeout: 30_000 });
  expect(await chat.evaluate(element => element.scrollTop)).toBeLessThan(100);
});

test("assessment readiness explains both learning paths before submission", async ({ page }) => {
  await fixture(page);
  await page.goto("/app/assess");
  await page.getByRole("button", { name: "Create your first assessment" }).click();
  const modal = page.getByRole("dialog", { name: "Create assessment" });
  await expect(modal.getByRole("status")).toContainText("Pick chats or a topic instead");
  await expect(modal.getByRole("button", { name: "Start quiz", exact: true })).toBeDisabled();
});

test("assessment failure preserves selections and displays an inline error", async ({ page }) => {
  await fixture(page, true);
  await page.route("**/api/v1/assessments", async route => {
    if (route.request().method() !== "POST") return route.fallback();
    await route.fulfill({ status: 422, contentType: "application/json", body: JSON.stringify({ detail: "Add more detail to your material." }) });
  });
  await page.goto("/app/assess");
  await page.getByRole("button", { name: "Create assessment", exact: true }).click();
  const modal = page.getByRole("dialog", { name: "Create assessment" });
  await modal.getByRole("button", { name: "Start quiz", exact: true }).click();
  await expect(modal.getByRole("alert")).toContainText("Add more detail");
  await expect(modal).toBeVisible();
  await expect(modal.getByRole("button", { name: "Start quiz", exact: true })).toBeEnabled();
});

test("first session guidance makes materials optional", async ({ page }, info) => {
  await fixture(page);
  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "Three small steps" })).toBeVisible();
  await expect(page.locator(".first-chapter")).toContainText("Your own notes are optional");
  await expect(page.locator(".first-chapter li").filter({ hasText: "Add your own material" })).toContainText("Optional");
  await expect(page.getByRole("img", { name: "0% of concepts strong" })).toHaveCount(0);
  await page.screenshot({ path: info.outputPath("first-session.png"), fullPage: true });
});

test("creating a review keeps the guide until the learner submits it", async ({ page }) => {
  await fixture(page);
  await page.route("**/api/v1/study/sessions?**", route => route.fulfill({ contentType: "application/json", body: JSON.stringify([{ id: "session", message_count: 2 }]) }));
  let taken = false;
  await page.route("**/api/v1/assessments?**", route => route.fulfill({ contentType: "application/json", body: JSON.stringify([{ id: "review", submitted_attempt_count: taken ? 1 : 0 }]) }));
  await page.goto("/app");
  const step = page.locator(".first-chapter li").filter({ hasText: "Take your first quiz" });
  await expect(step).toContainText("Your quiz is ready in Practice");
  await expect(step.getByRole("link")).toHaveAttribute("href", "/app/assess");
  await expect(step.locator(".step-check")).toHaveAttribute("aria-label", "Not completed");
  taken = true;
  await page.reload();
  await expect(page.locator(".first-chapter")).toHaveCount(0);
  await expect(page.getByRole("img", { name: "0% of concepts strong" })).toBeVisible();
});

test("slow replies explain the wait and the daily review has a clear action", async ({ page }) => {
  await fixture(page);
  await page.clock.install();
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/study/sessions/polish-session/messages", async route => {
    await held;
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ role: "assistant", content: "Primary keys identify rows.", sources: [] }) });
  });
  await page.route("**/api/v1/study/sessions?**", route => route.fulfill({ contentType: "application/json", body: JSON.stringify([{ id: "polish-session", message_count: 2, created_at: "2026-10-14T10:00:00Z" }]) }));
  await page.route("**/finish-day", route => route.fulfill({ contentType: "application/json", body: JSON.stringify({ assessment_id: "daily-review" }) }));
  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask ARIA anything…").fill("Explain primary keys");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".request-status")).toBeVisible();
  await page.clock.fastForward(8100);
  await expect(page.locator(".request-status")).toContainText("Still working…");
  await expect(page.locator(".request-lines span")).toHaveCount(3);
  release();
  await expect(page.getByText("Primary keys identify rows.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Done for today" })).toHaveCount(0);
  expect((await new AxeBuilder({ page }).analyze()).violations.filter(issue => issue.impact === "serious" || issue.impact === "critical")).toEqual([]);
});

test("error feedback stays above a modal, survives closing it, and can be dismissed", async ({ page }) => {
  await fixture(page);
  await page.goto("/app/roadmaps");
  await page.clock.install();
  await page.getByRole("button", { name: "Create roadmap", exact: true }).click();
  const source = readFileSync("lib/toast.ts", "utf8");
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  await page.evaluate(compiled => {
    const exports: Record<string, (message: string, kind: string) => void> = {};
    new Function("exports", compiled)(exports);
    exports.toast("Please retry this request.", "error");
  }, code);
  const toast = page.locator(".toast").filter({ hasText: "Please retry" });
  await expect(page.getByRole("dialog").locator(".toast")).toBeVisible();
  const point = await toast.boundingBox();
  expect(point).not.toBeNull();
  expect(await page.evaluate(({ x, y }) => document.elementFromPoint(x, y)?.closest(".toast") !== null, { x: point!.x + 5, y: point!.y + 5 })).toBe(true);
  await page.clock.fastForward(3500);
  await expect(toast).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(toast).toBeVisible();
  await toast.getByRole("button", { name: "Dismiss notification" }).click();
  await expect(toast).toHaveCount(0);
});

test("mobile navigation traps focus, restores it, and follows a destination", async ({ page }) => {
  await fixture(page);
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/app");
  const trigger = page.getByRole("button", { name: "Open navigation" });
  await trigger.click();
  const drawer = page.getByRole("dialog", { name: "Navigation" });
  await expect(drawer).toBeVisible();
  for (let index = 0; index < 15; index++) {
    await page.keyboard.press("Tab");
    expect(await drawer.evaluate(element => element.contains(document.activeElement))).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await expect(trigger).toBeFocused();
  await trigger.click();
  await drawer.getByRole("link", { name: "Plan", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/roadmaps$/);
  await expect(page.getByRole("dialog", { name: "Navigation" })).toHaveCount(0);
});

test("polished pages remain accessible and contained at mobile widths", async ({ page }, info) => {
  test.setTimeout(240_000);
  await fixture(page, true);
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  for (const route of ["/app", "/app/learn", "/app/roadmaps", "/app/assess", "/app/materials", "/app/audio"]) {
    await page.goto(route);
    await expect(page.getByRole("navigation", { name: "Workspace", exact: true })).toBeAttached();
    for (const width of [320, 375, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth), { message: `${route} width ${width}` }).toBeLessThanOrEqual(2);
    }
    const accessibility = await new AxeBuilder({ page }).analyze();
    expect(accessibility.violations.filter(issue => issue.impact === "serious" || issue.impact === "critical"), route).toEqual([]);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await page.screenshot({ path: info.outputPath(`${route.split("/").pop()}-desktop.png`), fullPage: true });
  }
  expect(errors).toEqual([]);
});
