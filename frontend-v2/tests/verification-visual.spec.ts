import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import AxeBuilder from "@axe-core/playwright";

const subject = { id: "visual-subject", title: "Database Management Systems", status: "active" };
const session = { id: "visual-session", context_id: subject.id, title: "✨ Primary keys and tables", preview: "Understanding unique identifiers", mode: "BASELINE", status: "ACTIVE", message_count: 2, created_at: "2026-10-14T10:00:00Z" };
const topics = [
  { id: "completed", title: "Tables and primary keys", state: "SUPPORTED", confidence: 85, ticked: true, prerequisites: [] },
  { id: "next", title: "Functional dependencies", state: "NOT_STARTED", confidence: 0, ticked: false, prerequisites: [] },
  { id: "developing", title: "Normalization", state: "DEVELOPING", confidence: 45, ticked: false, prerequisites: [] },
  { id: "review", title: "Database constraints", state: "NEEDS_REVIEW", confidence: 35, ticked: false, prerequisites: [] },
  { id: "pending", title: "Transaction isolation", state: "NOT_STARTED", confidence: 0, ticked: false, prerequisites: ["Normalization"] },
  { id: "upcoming", title: "Index design", state: "NOT_STARTED", confidence: 0, ticked: false, prerequisites: [] },
].map(item => ({ ...item, key_skills: [item.title], description: `Explore ${item.title.toLowerCase()} with examples.` }));
const roadmap = { id: "visual-roadmap", goal: "Understand relational databases", level: "Beginner", status: "ACTIVE", generation_mode: "ai", total: 6, done: 1,
  tiers: [{ name: "Foundation", icon: "book", topics: topics.slice(0, 4) }, { name: "Advanced topics", icon: "target", topics: topics.slice(4) }] };
const scores = [{ attempt_id: "first", score: 2, total: 4, completed_at: "2026-10-12T10:00:00Z" }, { attempt_id: "second", score: 3, total: 4, completed_at: "2026-10-13T10:00:00Z" }, { attempt_id: "last", score: 4, total: 4, completed_at: "2026-10-14T10:00:00Z" }];
const review = { id: "visual-review", context_id: subject.id, mode: "DAILY_REVIEW", format: "mcq", status: "READY", question_count: 4, created_at: "2026-10-14T10:00:00Z", submitted_attempt_count: 3, completed_scores: scores };

type State = { activity: boolean; progress: boolean; ready: boolean; assessments: boolean; creationError: boolean; reply: "success" | "error" | "held"; release: Promise<void> };
async function fixture(page: Page, state: State) {
  await page.route("**/api/v1/**", async route => {
    const path = new URL(route.request().url()).pathname;
    const method = route.request().method();
    let body: unknown = [];
    let status = 200;
    if (path.endsWith("/auth/me")) body = { id: "visual-learner", email: "learner@example.com", display_name: "Learner", verified: true };
    else if (path === "/api/v1/contexts") body = [subject];
    else if (path.endsWith("/unread-count")) body = { unread: 0 };
    else if (path.endsWith("/consistency")) body = { current_streak: state.activity ? 4 : 0, today_active: state.activity };
    else if (path.endsWith("/adaptation")) body = { decisions: [], states: state.progress ? topics.slice(0, 4).map((item, index) => ({ concept_id: item.id, concept_name: item.title, state: index < 2 ? "SUPPORTED" : "DEVELOPING", confidence: 70 })) : [] };
    else if (path === "/api/v1/roadmaps") body = [roadmap];
    else if (path === "/api/v1/roadmaps/visual-roadmap") body = roadmap;
    else if (path === "/api/v1/study/sessions") body = method === "POST" ? session : state.activity ? [session] : [];
    else if (path.endsWith("/messages")) {
      if (method === "POST") {
        if (state.reply === "held") await state.release;
        if (state.reply === "error") { status = 503; body = { detail: "The tutor is temporarily unavailable. Please retry." }; }
        else body = { content: "A primary key uniquely identifies each row. For example, a student ID distinguishes students with the same name.", role: "assistant", sources: [] };
      } else body = [{ role: "user", content: "What is a primary key?" }, { role: "assistant", content: "A primary key uniquely identifies a row. A student ID is one example." }];
    } else if (path.endsWith("/finish-day")) body = { assessment_id: "visual-review" };
    else if (path === "/api/v1/assessments/formats") body = [{ name: "mcq", label: "Multiple choice" }];
    else if (path === "/api/v1/assessments") {
      if (method === "POST" && state.creationError) { status = 422; body = { detail: "Add more detail to your study material to create useful questions." }; }
      else body = state.assessments ? [review] : [];
    } else if (path === "/api/v1/resources") body = state.ready ? [{ id: "visual-resource", context_id: subject.id, title: "Relational database lecture", resource_type: "TEXT", processing_status: "READY", error_detail: null, chunk_count: 4 }] : [];
    else if (path === "/api/v1/notes") body = state.activity ? [{ id: "visual-note", context_id: subject.id, title: "Primary keys: study notes", body: "Primary keys uniquely identify rows. A student ID is one example.", concept_id: null, study_session_id: session.id, created_at: "2026-10-14T10:00:00Z", state: "new", interval_days: 1, next_review_at: null, last_outcome: null }] : [];
    else if (path === "/api/v1/audio") body = [{ id: "visual-audio", source_type: "NOTE", source_id: "visual-note", title: "Primary keys: audio review", status: "READY", content_type: "audio/wav", duration_seconds: 180, position_seconds: 30, completed: false, created_at: "2026-10-14T10:00:00Z" }];
    else if (path === "/api/v1/settings/capabilities") body = { cloud_speech_configured: false, personal_keys_enabled: false };
    await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
  });
}

for (const palette of ["aurora", "noir"] as const) for (const width of [375, 1440]) {
  test(`visual evidence ${palette} ${width}`, async ({ page }) => {
    test.setTimeout(240_000);
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ reducedMotion: width === 375 ? "reduce" : "no-preference" });
    await page.addInitScript(value => { localStorage.setItem("aria.palette", value); localStorage.setItem("aria.gold", "0"); }, palette);
    const state: State = { activity: false, progress: false, ready: false, assessments: false, creationError: false, reply: "success", release: Promise.resolve() };
    await fixture(page, state);
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    const directory = resolve("../docs/screenshots/verification");
    await mkdir(directory, { recursive: true });
    const snap = async (name: string) => {
      await page.evaluate(async () => { await document.fonts.ready; window.scrollTo({ top: 0, behavior: "instant" }); });
      await expect.poll(() => page.evaluate(() => document.getAnimations()
        .filter(animation => animation.effect?.getComputedTiming().iterations !== Infinity)
        .every(animation => animation.playState === "finished" || animation.playState === "idle"))).toBe(true);
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(2);
      const accessibility = await new AxeBuilder({ page }).analyze();
      expect(accessibility.violations.filter(item => item.impact === "serious" || item.impact === "critical"), name).toEqual([]);
      await page.screenshot({ path: resolve(directory, `${palette}-${width}-${name}.png`), fullPage: true, animations: "disabled" });
    };
    await page.goto("/app");
    await expect(page.locator(".first-chapter")).toBeVisible();
    const guideWidth = await page.locator(".first-chapter").evaluate(element => element.getBoundingClientRect().width);
    const panelWidth = await page.locator(".learning-progress").evaluate(element => element.getBoundingClientRect().width);
    expect(guideWidth).toBeGreaterThan(panelWidth - 80);
    await snap("dashboard-new");
    state.activity = true; state.progress = true; state.ready = true; state.assessments = true;
    await page.reload();
    await expect(page.getByRole("img", { name: "50% of concepts supported" })).toBeVisible();
    await expect(page.locator(".learning-ring strong")).toHaveText("50%");
    await snap("dashboard-progress");
    await page.goto("/app/roadmaps");
    const foundation = page.getByRole("button", { name: /Foundation/ });
    await expect(foundation).toHaveAttribute("aria-expanded", "true");
    await foundation.click();
    await expect(page.locator(".phase-preview")).toHaveCount(2);
    await snap("roadmap-collapsed");
    await foundation.click();
    await page.getByRole("button", { name: /Advanced topics/ }).click();
    for (const name of ["completed", "in-progress", "up-next", "needs-review", "prerequisite-pending", "upcoming"]) await expect(page.locator(`.roadmap-topic-card.${name}`)).toHaveCount(1);
    await snap("roadmap-expanded-states");
    await page.goto("/app/learn?session=visual-session");
    await expect(page.locator(".msg")).toHaveCount(2);
    await page.clock.install();
    let release!: () => void;
    state.reply = "held"; state.release = new Promise<void>(resolve => { release = resolve; });
    await page.getByPlaceholder("Ask ARIA anything…").fill("Explain how primary keys help with duplicates");
    await page.getByRole("button", { name: "Send", exact: true }).click();
    await expect(page.locator(".request-status")).toBeVisible();
    await page.clock.fastForward(8100);
    await expect(page.locator(".request-status")).toContainText("Still working…");
    if (width === 375) expect(await page.locator(".request-lines span").first().evaluate(element => getComputedStyle(element).animationName)).toBe("none");
    await snap("learn-thinking-eight-seconds");
    state.reply = "error"; release();
    await expect(page.getByRole("button", { name: "Retry reply" })).toBeVisible();
    await snap("learn-reply-error");
    state.reply = "success";
    await page.getByRole("button", { name: "Retry reply" }).click();
    await expect(page.locator(".request-status")).toHaveCount(0);
    await page.getByRole("button", { name: "Done for today", exact: true }).click();
    await expect(page.locator(".daily-review-ready")).toBeVisible();
    if (width === 375) expect(await page.locator(".daily-review-ready").evaluate(element => getComputedStyle(element).animationName)).toBe("none");
    await snap("learn-daily-review");
    await page.getByRole("button", { name: "Focus", exact: true }).click();
    await expect(page.locator(".learn-side")).not.toBeVisible();
    await snap("learn-focus");
    state.assessments = false;
    await page.goto("/app/assess");
    await expect(page.getByRole("button", { name: "Create your first assessment" })).toBeVisible();
    await snap("assess-empty");
    state.ready = false;
    await page.getByRole("button", { name: "Create assessment", exact: true }).first().click();
    const modal = page.getByRole("dialog", { name: "Create assessment" });
    await expect(modal.getByRole("button", { name: "Create assessment", exact: true })).toBeDisabled();
    await snap("assess-disabled");
    await page.keyboard.press("Escape");
    state.ready = true; state.creationError = true;
    await page.getByRole("button", { name: "Create assessment", exact: true }).first().click();
    await expect(modal.getByRole("button", { name: "Create assessment", exact: true })).toBeEnabled();
    await modal.getByRole("button", { name: "Create assessment", exact: true }).click();
    await expect(modal.getByRole("alert")).toContainText("Add more detail");
    await snap("assess-modal-error");
    await page.keyboard.press("Escape");
    state.assessments = true; state.creationError = false;
    await page.reload();
    await expect(page.locator(".assessment-score-trend")).toBeVisible();
    await snap("assess-scores");
    await page.goto("/app/materials");
    await expect(page.locator(".resource-card")).toBeVisible();
    await snap("materials");
    await page.goto("/app/audio");
    await expect(page.getByText("Primary keys: audio review", { exact: true })).toBeVisible();
    await snap("audio");
    expect(errors).toEqual([]);
  });
}
