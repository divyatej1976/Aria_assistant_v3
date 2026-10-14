import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { writeFile } from "node:fs/promises";

const contexts = [
  { id: "context-a", title: "Database Management Systems", description: "Normalization", status: "active" },
  { id: "context-b", title: "Linear Algebra", description: "Vectors", status: "active" },
];

async function fixture(page: Page) {
  await page.route("**/api/v1/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = [];
    if (path.endsWith("/auth/me")) body = { id: "learner", email: "learner@example.com", display_name: "Learner", verified: true };
    else if (path === "/api/v1/contexts") body = contexts;
    else if (path.endsWith("/unread-count")) body = { unread: 0 };
    else if (path.endsWith("/consistency")) body = { current_streak: 4, today_active: true };
    else if (path.endsWith("/adaptation")) body = { states: [{ concept_id: "one", concept_name: "Normalization", state: "SUPPORTED", confidence: 80, reason: "Assessment evidence" }, { concept_id: "two", concept_name: "Dependencies", state: "DEVELOPING", confidence: 50, reason: "Keep practicing" }], decisions: [] };
    else if (path.endsWith("/concepts")) body = [{ id: "one", name: "Normalization" }, { id: "two", name: "Dependencies" }];
    else if (path.endsWith("/one/prerequisites")) body = [{ prerequisite_concept_id: "two" }];
    else if (path === "/api/v1/roadmaps") body = [{ id: "roadmap", goal: "Understand databases", level: "Beginner", total: 2, done: 1, status: "ACTIVE" }];
    else if (path === "/api/v1/roadmaps/roadmap") body = { id: "roadmap", goal: "Understand databases", level: "Beginner", total: 2, done: 1, status: "ACTIVE", tiers: [{ name: "Foundation", icon: "book", topics: [{ id: "keys", title: "Tables and keys", key_skills: ["Primary keys"], prerequisites: [], state: "SUPPORTED", confidence: 80, ticked: true }, { id: "normalization", title: "Normalization", key_skills: ["Dependencies"], prerequisites: ["Tables and keys"], state: "DEVELOPING", confidence: 50, ticked: false }] }] };
    else if (path === "/api/v1/study/sessions") body = [{ id: "session", context_id: "context-a", mode: "BASELINE", status: "ACTIVE", created_at: "2026-10-05T00:00:00Z" }];
    else if (path === "/api/v1/resources") body = [{ id: "resource", context_id: "context-a", title: "Lecture notes", resource_type: "TEXT", processing_status: "READY", error_detail: null, chunk_count: 4 }];
    await route.fulfill({ status: 200, contentType: "application/json", headers: { "Access-Control-Allow-Origin": new URL(page.url()).origin, "Access-Control-Allow-Credentials": "true" }, body: JSON.stringify(body) });
  });
}

async function settleUI(page: Page) {
  await page.evaluate(async () => { await document.fonts.ready; });
  await expect.poll(() => page.evaluate(() => document.getAnimations()
    .filter(animation => animation.effect?.getComputedTiming().iterations !== Infinity)
    .every(animation => animation.playState === "finished" || animation.playState === "idle"))).toBe(true);
}

test("dashboard retains navigation, real progress, and accessible surfaces across palettes", async ({ page }, testInfo) => {
  await fixture(page);
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "Continue learning", exact: true })).toBeVisible();
  await expect(page.getByRole("img", { name: "50% of concepts supported" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Workspace", exact: true })).toBeVisible();
  for (const palette of ["aurora", "noir", "gold"]) {
    await page.evaluate(p => {
      localStorage.setItem("aria.palette", p === "aurora" ? "aurora" : "noir");
      localStorage.setItem("aria.gold", p === "gold" ? "1" : "0");
    }, palette);
    await page.reload();
    await expect(page.getByRole("img", { name: "50% of concepts supported" })).toBeVisible();
    await settleUI(page);
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations.filter(v => v.impact === "serious" || v.impact === "critical"), palette).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`dashboard-${palette}.png`), fullPage: true });
  }
  expect(errors).toEqual([]);
});

test("learning screens remain accessible and contained across palettes and widths", async ({ page }, testInfo) => {
  test.setTimeout(240_000);
  await fixture(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/app");
  const routes = ["/app/map", "/app/learn", "/app/materials", "/app/roadmaps"];
  for (const palette of ["aurora", "noir", "gold"]) {
    await page.evaluate(p => { localStorage.setItem("aria.palette", p === "aurora" ? "aurora" : "noir"); localStorage.setItem("aria.gold", p === "gold" ? "1" : "0"); }, palette);
    for (const route of routes) {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto(route);
      await expect(page.locator(".constellation, .chat-input-row, .resource-card, .milestone-trail").first()).toBeVisible();
      await settleUI(page);
      const results = await new AxeBuilder({ page }).analyze();
      expect(results.violations.filter(v => v.impact === "serious" || v.impact === "critical"), `${palette} ${route}`).toEqual([]);
      for (const width of [320, 375, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth), `${palette} ${route} ${width}`).toBeLessThanOrEqual(2);
      }
      if (palette === "noir" || palette === "aurora") await page.screenshot({ path: testInfo.outputPath(`${route.split("/").pop()}-${palette}.png`), fullPage: true });
    }
  }
});

test("roadmap trail selects real topic details and materials processing follows the request", async ({ page }) => {
  await fixture(page);
  await page.goto("/app/roadmaps");
  await page.getByRole("button", { name: "Normalization, next milestone", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Normalization", exact: true })).toBeVisible();
  await page.goto("/app/materials");
  await page.getByRole("button", { name: "Add resource", exact: true }).first().click();
  await page.getByRole("button", { name: "Paste text", exact: true }).click();
  await page.getByLabel("Title", { exact: true }).fill("New study text");
  await page.getByLabel("Text", { exact: true }).fill("A primary key identifies a row uniquely.");
  let finish!: () => void;
  const released = new Promise<void>(resolve => { finish = resolve; });
  await page.route("**/api/v1/resources/text", async route => { await released; await route.fulfill({ status: 200, contentType: "application/json", body: '{"id":"new"}' }); });
  await page.getByRole("button", { name: "Add resource", exact: true }).last().click();
  await expect(page.getByText("Processing your study text", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Processing material…", exact: false })).toBeDisabled();
  finish();
  await expect(page.getByText("Processing your study text", { exact: true })).not.toBeVisible();
  await expect(page.getByRole("link", { name: "Explore connected concepts" })).toBeVisible();
});

test("map uses confirmed edges, keeps filtered positions stable, and supports keyboard and list selection", async ({ page }, testInfo) => {
  await fixture(page);
  await page.goto("/app/map");
  await expect(page.getByText("2 concepts · 1 visible prerequisite connections")).toBeVisible();
  const normalization = page.getByRole("button", { name: "Normalization, Supported", exact: true });
  const before = await normalization.getAttribute("style");
  await normalization.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("complementary", { name: "Selected concept details" }).getByRole("heading", { name: "Normalization", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Reset zoom" })).toHaveText("125%");
  await page.getByRole("button", { name: "Reset zoom" }).click();
  await page.getByRole("button", { name: "Supported", exact: true }).click();
  expect(await normalization.getAttribute("style")).toBe(before);
  await expect(page.locator(".concept-edge")).toHaveCount(0);
  await page.getByRole("button", { name: "All", exact: true }).click();
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page.locator(".concept-list-item").filter({ hasText: "Dependencies" }).click();
  await expect(page.getByRole("complementary", { name: "Selected concept details" }).getByRole("heading", { name: "Dependencies", exact: true })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter(v => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  await page.getByRole("button", { name: "Constellation", exact: true }).click();
  await page.screenshot({ path: testInfo.outputPath("knowledge-map.png"), fullPage: true });
});

test("chat focus and incoming replies preserve an earlier reading position", async ({ page }) => {
  await fixture(page);
  await page.route("**/study/sessions**", async route => {
    const path = new URL(route.request().url()).pathname;
    const body = path.endsWith("/messages") ? route.request().method() === "POST" ? { content: "A new response to your question." } : Array.from({ length: 30 }, (_, index) => ({ role: index % 2 ? "assistant" : "user", content: `Earlier message ${index}. ` + "An explanation about concepts and connections. ".repeat(20) })) : [{ id: "session", context_id: "context-a", mode: "BASELINE", status: "ACTIVE", created_at: "2026-10-05T00:00:00Z", title: "Earlier message 0", message_count: 30 }];
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.goto("/app/learn?session=session");
  await expect(page.getByPlaceholder("Ask ARIA anything…")).toBeVisible();
  await expect(page.locator(".msg")).toHaveCount(30);
  await page.getByRole("button", { name: "Focus", exact: true }).click();
  await expect(page.locator(".learn-side")).not.toBeVisible();
  await page.locator(".chat-body").evaluate(el => { el.scrollTop = 200; el.dispatchEvent(new Event("scroll")); });
  await expect(page.getByRole("button", { name: "Jump to latest" })).toBeVisible();
  await page.getByPlaceholder("Ask ARIA anything…").fill("Explain normalization");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByText("A new response to your question.")).toBeAttached();
  expect(await page.locator(".chat-body").evaluate(el => el.scrollTop)).toBeLessThan(300);
  await page.getByRole("button", { name: "Jump to latest" }).click();
  await expect.poll(() => page.locator(".chat-body").evaluate(el => el.scrollHeight - el.scrollTop - el.clientHeight)).toBeLessThan(100);
  await page.getByRole("button", { name: "Exit focus", exact: true }).click();
  await expect(page.locator(".learn-side")).toBeVisible();
});

test("landing sample can change topic and learning stage", async ({ page }, testInfo) => {
  await page.route("**/api/v1/**", route => route.fulfill({ status: 401, contentType: "application/json", body: '{"detail":"anonymous"}' }));
  let release = () => {};
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/_next/static/**", async route => {
    if (new URL(route.request().url()).pathname.endsWith(".js")) await pending;
    await route.continue();
  });
  try {
    await page.goto("/", { waitUntil: "commit" });
    await expect(page.getByLabel("Sample topic")).toBeDisabled();
    await expect(page.getByRole("button", { name: /A conversation/ })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Palette settings" })).toBeDisabled();
  } finally {
    release();
  }
  await expect(page.getByLabel("Sample topic")).toBeEnabled();
  await expect(page.getByRole("heading", { name: "ARIA", exact: true })).toBeVisible();
  await page.getByLabel("Sample topic").selectOption("2");
  await page.getByRole("button", { name: /A conversation/ }).click();
  await expect(page.getByText("When should I write a function?")).toBeVisible();
  await page.getByRole("button", { name: /Connected ideas/ }).click();
  await expect(page.getByRole("heading", { name: "Functions", exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("landing-preview.png"), fullPage: true });
});

test("mobile layouts and live reduced motion keep the dashboard usable", async ({ page }) => {
  await fixture(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const width of [320, 375, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/app");
    await expect(page.getByRole("heading", { name: "Continue learning", exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(2);
    expect(await page.locator(".motion-reveal").first().evaluate(el => getComputedStyle(el).animationName)).toBe("none");
    await expect(page.locator(".ambient canvas")).toHaveCount(0);
  }
  await page.getByRole("button", { name: "Profile", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign Out" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Sign Out" })).not.toBeVisible();
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await expect(page.locator(".ambient canvas")).toHaveCount(1);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(page.locator(".ambient canvas")).toHaveCount(0);
  await page.setViewportSize({ width: 375, height: 900 });
  const navigation = page.getByRole("navigation", { name: "Primary", exact: true });
  await navigation.getByRole("link", { name: "Knowledge map", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/map$/);
  await expect(navigation.getByRole("link", { name: "Knowledge map", exact: true })).toHaveAttribute("aria-current", "page");
  await expect(navigation.locator(".mobile-active-surface")).toHaveCount(1);
  await expect(navigation.getByRole("link", { name: "Dashboard", exact: true })).not.toHaveAttribute("aria-current", "page");
});

test("workspace popovers preserve focus during switching and dismissal", async ({ page }) => {
  await fixture(page);
  await page.goto("/app");
  const profile = page.getByRole("button", { name: "Profile", exact: true });
  const notifications = page.getByRole("button", { name: "Notifications", exact: true });
  await profile.click();
  await expect(page.getByRole("link", { name: "Account & settings", exact: true })).toBeFocused();
  await notifications.click();
  await expect(page.getByRole("button", { name: "Mark all read", exact: true })).toBeFocused();
  await expect(page.getByRole("button", { name: "Sign Out", exact: true })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(notifications).toBeFocused();
  await expect(page.locator(".popover-card")).toHaveCount(0);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await profile.click();
  await expect(page.getByRole("link", { name: "Account & settings", exact: true })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(profile).toBeFocused();
  await expect(page.locator(".popover-card")).toHaveCount(0);
});

test("materials ignores old subject results after a context switch", async ({ page }) => {
  await fixture(page);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let oldRequestStarted = false;
  await page.route("**/api/v1/resources?**", async route => {
    const oldSubject = new URL(route.request().url()).searchParams.get("context_id") === "context-a";
    if (oldSubject) { oldRequestStarted = true; await gate; }
    await route.fulfill({ status: 200, contentType: "application/json",
      headers: { "Access-Control-Allow-Origin": new URL(page.url()).origin, "Access-Control-Allow-Credentials": "true" },
      body: JSON.stringify([{ id: oldSubject ? "old" : "new", context_id: oldSubject ? "context-a" : "context-b",
        title: oldSubject ? "Old database notes" : "Vector notes", resource_type: "TEXT", processing_status: "READY", error_detail: null, chunk_count: 2 }]) });
  });
  await page.goto("/app/materials");
  await expect.poll(() => oldRequestStarted).toBe(true);
  await page.getByRole("combobox", { name: "Active learning context" }).selectOption("context-b");
  await expect(page.getByText("Vector notes", { exact: true })).toBeVisible();
  release();
  await settleUI(page);
  await expect(page.getByText("Old database notes", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Vector notes", { exact: true })).toBeVisible();
});

test("roadmap celebrates a newly confirmed milestone once per session", async ({ page }) => {
  await fixture(page);
  let completed = false;
  await page.route("**/api/v1/roadmaps/roadmap", async route => {
    await route.fulfill({ status: 200, contentType: "application/json",
      headers: { "Access-Control-Allow-Origin": new URL(page.url()).origin, "Access-Control-Allow-Credentials": "true" },
      body: JSON.stringify({ id: "roadmap", goal: "Understand databases", level: "Beginner", total: 1, done: completed ? 1 : 0, status: "ACTIVE",
        tiers: [{ name: "Foundation", icon: "book", topics: [{ id: "keys", title: "Tables and keys", key_skills: [], prerequisites: [], state: completed ? "SUPPORTED" : "DEVELOPING", confidence: 80, ticked: completed }] }] }) });
  });
  await page.goto("/app/roadmaps");
  await expect(page.locator(".milestone-count")).toHaveText("0 / 1 complete");
  await expect(page.locator(".milestone-status")).toBeEmpty();
  completed = true;
  await page.reload();
  await expect(page.locator(".milestone-status")).toHaveText("1 new milestone completed.");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(page.locator(".milestone-status")).toHaveText("1 new milestone completed.");
  await expect(page.locator(".milestone-status")).toBeEmpty();
  await page.reload();
  await expect(page.locator(".milestone-count")).toHaveText("1 / 1 complete");
  await expect(page.locator(".milestone-status")).toBeEmpty();
});

test("onboarding supports keyboard submission and an optional learning goal", async ({ page }) => {
  await fixture(page);
  let submitted: unknown;
  await page.route("**/api/v1/contexts", async route => {
    if (route.request().method() !== "POST") return route.fallback();
    submitted = route.request().postDataJSON();
    await route.fulfill({ status: 201, contentType: "application/json",
      headers: { "Access-Control-Allow-Origin": new URL(page.url()).origin, "Access-Control-Allow-Credentials": "true" },
      body: JSON.stringify({ id: "new-context", title: "Python", description: null, status: "active" }) });
  });
  await page.goto("/onboarding");
  await page.getByRole("button", { name: "Start learning", exact: true }).click();
  const topic = page.getByRole("textbox", { name: "What would you like to learn?" });
  await expect(topic).toBeFocused();
  await expect(topic).toHaveAttribute("aria-invalid", "true");
  await topic.fill(" Python ");
  await page.getByRole("button", { name: "Intermediate", exact: true }).click();
  await topic.press("Enter");
  await expect(page).toHaveURL(/\/app$/);
  expect(submitted).toEqual({ title: "Python", configuration: { mastery_level: "intermediate" } });
});

test("a delayed tutor reply stays out of a different study session", async ({ page }) => {
  await fixture(page);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let replyStarted = false;
  await page.route("**/study/sessions**", async route => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown;
    if (route.request().method() === "POST") {
      replyStarted = true;
      await gate;
      body = { content: "Reply belonging to the old session" };
    } else if (path.endsWith("/messages")) {
      body = [{ role: "assistant", content: path.includes("/second/") ? "Second conversation history" : "First conversation history" }];
    } else {
      body = ["first", "second"].map(id => ({ id, context_id: "context-a", mode: "BASELINE", status: "ACTIVE", created_at: "2026-10-05T00:00:00Z", title: `${id} conversation`, message_count: 2 }));
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.goto("/app/learn?session=first");
  await page.getByPlaceholder("Ask ARIA anything…").fill("Explain this");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect.poll(() => replyStarted).toBe(true);
  await page.locator(".learn-side .session-item").nth(1).click();
  await expect(page.getByText("Second conversation history", { exact: true })).toBeVisible();
  const finished = page.waitForResponse(response => response.request().method() === "POST" && response.url().includes("/first/messages"));
  release();
  await (await finished).finished();
  await settleUI(page);
  await expect(page.getByText("Reply belonging to the old session", { exact: true })).toHaveCount(0);
  await expect(page.getByPlaceholder("Ask ARIA anything…")).toHaveValue("");
  await page.getByPlaceholder("Ask ARIA anything…").fill("A new question");
  await expect(page.getByRole("button", { name: "Send", exact: true })).toBeEnabled();
});

test("large concept maps expose every group and search beyond the first sixty", async ({ page }) => {
  await fixture(page);
  let releaseConnections!: () => void;
  const pendingConnections = new Promise<void>(resolve => { releaseConnections = resolve; });
  await page.route("**/concepts/*/prerequisites", async route => {
    await pendingConnections;
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  const concepts = Array.from({ length: 72 }, (_, index) => ({ id: `concept-${String(index).padStart(3, "0")}`, name: `Concept ${index}` }));
  const fulfill = (body: unknown) => ({ status: 200, contentType: "application/json",
    headers: { "Access-Control-Allow-Origin": new URL(page.url()).origin, "Access-Control-Allow-Credentials": "true" }, body: JSON.stringify(body) });
  await page.route("**/contexts/*/concepts", route => route.fulfill(fulfill(concepts)));
  await page.route("**/contexts/*/adaptation", route => route.fulfill(fulfill({ decisions: [], states: concepts.map(concept => ({ concept_id: concept.id, concept_name: concept.name, state: "SUPPORTED", confidence: 80, reason: "Confirmed learning evidence" })) })));
  await page.goto("/app/map");
  await expect(page.locator(".concept-node")).toHaveCount(60);
  await expect(page.getByText("Loading confirmed connections… You can explore your concepts now.")).toBeVisible();
  releaseConnections();
  await page.getByRole("button", { name: "Next group", exact: true }).click();
  await expect(page.locator(".concept-node")).toHaveCount(12);
  const target = page.getByRole("button", { name: "Concept 71, Supported", exact: true });
  const position = await target.getAttribute("style");
  await target.click();
  await expect(page.getByRole("heading", { name: "Concept 71", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Previous group", exact: true }).click();
  await page.getByPlaceholder("Search concepts").fill("Concept 71");
  await expect(target).toBeAttached();
  expect(await target.getAttribute("style")).toBe(position);
  await expect(page.getByRole("button", { name: "Previous group", exact: true })).toBeDisabled();
  await page.getByPlaceholder("Search concepts").fill("");
  await page.getByRole("button", { name: "List", exact: true }).click();
  await expect(page.locator(".concept-list-item")).toHaveCount(72);
});

test("failed progress is retryable rather than implying zero mastery", async ({ page }) => {
  await fixture(page);
  await page.route("**/contexts/*/adaptation", route => route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"unavailable"}' }));
  await page.goto("/app");
  await expect(page.getByText("Progress is unavailable.")).toBeVisible();
  await expect(page.getByRole("img", { name: /concepts supported/ })).toHaveCount(0);
  await page.unroute("**/contexts/*/adaptation");
  await page.getByRole("button", { name: "Retry progress" }).click();
  await expect(page.getByRole("img", { name: "50% of concepts supported" })).toBeVisible();
});

test("dashboard stays interactive under CPU throttling and repeated workspace navigation", async ({ page }, testInfo) => {
  await fixture(page);
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  const start = Date.now();
  await page.goto("/app");
  await expect(page.getByRole("img", { name: "50% of concepts supported" })).toBeVisible({ timeout: 20_000 });
  const elapsed = Date.now() - start;
  expect(elapsed).toBeLessThan(20_000);
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 1 });
  for (let cycle = 0; cycle < 3; cycle++) {
    await page.getByRole("navigation", { name: "Workspace", exact: true }).getByRole("link", { name: "Knowledge map", exact: true }).click();
    await expect(page.locator(".constellation")).toBeVisible();
    await page.getByRole("navigation", { name: "Workspace", exact: true }).getByRole("link", { name: "Dashboard", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Continue learning", exact: true })).toBeVisible();
    await expect(page.locator(".ambient canvas")).toHaveCount(1);
    await expect(page.locator(".shell-side")).toHaveCount(1);
  }
  await testInfo.attach("current-performance-baseline", { body: JSON.stringify({ developmentDashboardReadyMs: elapsed, cpuThrottle: 4, navigationCycles: 3, note: "Frontend fixtures; this is a current baseline, not a pre-change comparison or production performance claim." }), contentType: "application/json" });
});

test("palette selection persists and follows another tab", async ({ page, context }) => {
  await fixture(page);
  await page.goto("/app");
  const other = await context.newPage();
  await fixture(other);
  await other.goto("/app");
  await page.getByRole("button", { name: "Palette settings" }).click();
  await page.getByRole("button", { name: "Select Noir Silk palette" }).click();
  await expect(other.locator("html")).toHaveAttribute("data-theme", "noir");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "noir");
  await other.close();
});

test("palette controls work when storage writes are blocked", async ({ page }) => {
  await fixture(page);
  await page.addInitScript(() => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function (key: string, value: string) {
      if (key === "aria.palette" || key === "aria.gold") throw new DOMException("Storage full", "QuotaExceededError");
      return original.call(this, key, value);
    };
  });
  await page.goto("/app");
  await page.getByRole("button", { name: "Palette settings" }).click();
  await page.getByRole("button", { name: "Select Noir Silk palette" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "noir");
  await page.getByRole("button", { name: "Palette settings" }).click();
  await page.getByRole("button", { name: "Toggle gold accents" }).click();
  await expect(page.locator("html")).toHaveClass(/noir-gold/);
});

for (const viewport of [{ name: "mobile", width: 390, height: 844 }, { name: "desktop", width: 1440, height: 900 }, { name: "landing", width: 1440, height: 900 }]) {
test(`records ${viewport.name} animation frame pacing and navigation resource growth`, async ({ page }, testInfo) => {
  test.setTimeout(120_000);
  await fixture(page);
  if (viewport.name === "landing") await page.route("**/api/v1/**", route => route.fulfill({ status: 401, contentType: "application/json", body: '{"detail":"anonymous"}' }));
  await page.setViewportSize({ width: viewport.width, height: viewport.height });
  await page.goto(viewport.name === "landing" ? "/" : "/app");
  await expect(page.locator(".ambient canvas")).toHaveCount(1);
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Performance.enable");
  await cdp.send("HeapProfiler.enable");
  const metrics = async () => {
    await cdp.send("HeapProfiler.collectGarbage");
    const result = await cdp.send("Performance.getMetrics");
    return Object.fromEntries(result.metrics.filter(item => ["Nodes", "JSEventListeners", "JSHeapUsedSize"].includes(item.name)).map(item => [item.name, item.value]));
  };
  const sampleFrames = () => page.evaluate(() => new Promise<{ frames: number; p95GapMs: number; gapsOver32Ms: number; longTasks: number; longTaskMs: number }>(resolve => {
    const gaps: number[] = [];
    const tasks: number[] = [];
    const observer = new PerformanceObserver(list => tasks.push(...list.getEntries().map(entry => entry.duration)));
    observer.observe({ type: "longtask" });
    const start = performance.now();
    let previous = start;
    const frame = (now: number) => {
      gaps.push(now - previous);
      previous = now;
      if (now - start < 1800) return requestAnimationFrame(frame);
      observer.disconnect();
      gaps.sort((a, b) => a - b);
      resolve({ frames: gaps.length, p95GapMs: gaps[Math.min(gaps.length - 1, Math.floor(gaps.length * .95))], gapsOver32Ms: gaps.filter(gap => gap > 32).length, longTasks: tasks.length, longTaskMs: tasks.reduce((total, duration) => total + duration, 0) });
    };
    requestAnimationFrame(frame);
  }));
  const visit = async (name: string) => {
    if (viewport.name === "landing") {
      await page.getByRole("button", { name: name === "Dashboard" ? /Your path/ : /Connected ideas/ }).click();
      await expect(page.locator(".preview-scene")).toBeVisible();
      await settleUI(page);
      return;
    }
    await page.getByRole("navigation", { name: viewport.name === "mobile" ? "Primary" : "Workspace", exact: true }).getByRole("link", { name, exact: true }).click();
    await expect(name === "Dashboard" ? page.getByRole("heading", { name: "Continue learning", exact: true }) : page.locator(".constellation")).toBeVisible();
    await settleUI(page);
  };
  await visit("Knowledge map");
  await visit("Dashboard");
  const before = await metrics();
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  const animated = await sampleFrames();
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(page.locator(".ambient canvas")).toHaveCount(0);
  const reduced = await sampleFrames();
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 1 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  const navigationCycles = viewport.name === "mobile" ? 20 : 5;
  const checkpoints: { cycle: number; metrics: Record<string, number> }[] = [];
  for (let cycle = 0; cycle < navigationCycles; cycle++) {
    await visit("Knowledge map"); await visit("Dashboard");
    if ((cycle + 1) % 5 === 0) checkpoints.push({ cycle: cycle + 1, metrics: await metrics() });
  }
  const after = await metrics();
  const report = { surface: viewport.name, viewport: `${viewport.width}x${viewport.height}`, cpuThrottle: 4, animated, reduced, navigationCycles, checkpoints, before, after,
    note: `${process.env.ARIA_UI_RUNTIME ?? "development"} runtime with network fixtures. Frame gaps measure this host, not a production device guarantee. Resource samples follow forced garbage collection and route warmup.` };
  const path = testInfo.outputPath("animation-profile.json");
  await writeFile(path, JSON.stringify(report, null, 2));
  await testInfo.attach("animation-profile", { path, contentType: "application/json" });
  expect(animated.frames).toBeGreaterThan(0);
  expect(reduced.frames).toBeGreaterThan(0);
});
}
