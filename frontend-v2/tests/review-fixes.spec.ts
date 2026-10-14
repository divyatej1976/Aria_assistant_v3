import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import ts from "typescript";

async function fixture(page: Page, options: { anonymous?: boolean; roadmapFailure?: boolean; logoutFailure?: boolean; roadmapMode?: "ai" | "starter" | "legacy"; keyUsable?: boolean; personalKeysEnabled?: boolean; assessment?: boolean; audio?: boolean } = {}) {
  await page.route("**/api/v1/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = [];
    let status = 200;
    if (path.endsWith("/auth/me")) {
      status = options.anonymous ? 401 : 200;
      body = options.anonymous ? { detail: "Not authenticated" } : { id: "review-learner", email: "review@example.com", verified: true };
    } else if (path.endsWith("/auth/signout") && options.logoutFailure) {
      status = 503; body = { detail: "Unavailable" };
    } else if (path === "/api/v1/contexts") {
      body = [{ id: "review-context", title: "Review Subject", description: null, status: "active" }];
    } else if (path === "/api/v1/roadmaps" && options.roadmapFailure) {
      status = 503; body = { detail: "Unavailable" };
    } else if (path.startsWith("/api/v1/roadmaps") && options.roadmapMode) {
      const roadmap = { id: "review-roadmap", goal: "Biology", level: "Beginner", status: "ACTIVE", created_at: "2026-10-06", total: 0, done: 0, tiers: [], generation_mode: options.roadmapMode === "legacy" ? null : options.roadmapMode, fallback_reason: options.roadmapMode === "starter" ? "provider_failed" : null };
      body = path === "/api/v1/roadmaps" ? [roadmap] : roadmap;
    } else if (path === "/api/v1/assessments" && options.assessment) {
      body = [{ id: "review-assessment", context_id: "review-context", format: "mcq", mode: "BASELINE", status: "READY", question_count: 1, created_at: "2026-10-06" }];
    } else if (path === "/api/v1/assessments/review-assessment/attempts" && options.assessment) {
      body = { attempt_id: "review-attempt", questions: [{ id: "review-question", position: 1, prompt: "Select an answer", options: ["First option", "Second option"], concept_id: null }] };
    } else if (path === "/api/v1/audio" && options.audio) {
      body = [{ id: "review-audio", source_type: "NOTE", source_id: "review-note", title: "Review recording", status: "READY", content_type: "audio/wav", duration_seconds: 10, position_seconds: 0, completed: false, created_at: "2026-10-06" }];
    } else if (path === "/api/v1/audio/review-audio/play" && options.audio) {
      await route.fulfill({ contentType: "audio/wav", body: Buffer.alloc(44) });
      return;
    } else if (path === "/api/v1/settings/capabilities") {
      body = { cloud_speech_configured: false, allowed_models: ["deployment-custom-model"], model: "deployment-custom-model", personal_keys_enabled: options.personalKeysEnabled ?? true, personal_key: { configured: options.keyUsable !== undefined, usable: options.keyUsable ?? false, provider: "groq", model: null, hint: "...test" } };
    } else if (path === "/api/v1/settings/llm-key" && options.keyUsable !== undefined) {
      body = { configured: true, usable: options.keyUsable, issue: options.keyUsable ? null : "credential_unreadable", provider: "groq", model: "openai/gpt-oss-120b", hint: "...test" };
    } else if (path.endsWith("/adaptation")) body = { states: [] };
    else if (path.endsWith("/unread-count")) body = { unread: 0 };
    if (route.request().method() === "OPTIONS") { status = 200; body = {}; }
    await route.fulfill({ status, contentType: "application/json", headers: {
      "Access-Control-Allow-Origin": route.request().headers()["origin"] ?? "http://localhost:3101",
      "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type,X-CSRF-Token",
      "Access-Control-Allow-Credentials": "true",
    }, body: JSON.stringify(body) });
  });
}

test("anonymous workspace visitors reach sign-in with a return path", async ({ page }) => {
  await fixture(page, { anonymous: true });
  await page.goto("/app/audio");
  await expect(page).toHaveURL(/\/signin\?next=/);
  expect(new URL(page.url()).searchParams.get("next")).toBe("/app/audio");
});

test("audio explains available speech in user-facing language", async ({ page }) => {
  await fixture(page, { keyUsable: true });
  await page.goto("/app/audio");
  const setup = page.getByRole("status").filter({ hasText: "local speech" });
  await expect(setup).toBeVisible();
  await expect(setup).not.toContainText("deployment");
  await expect(setup).not.toContainText("personal tutor key");
  await expect(page.getByRole("button", { name: "Convert to Audio", exact: true }).first()).toBeEnabled();
});

test("switching audio subjects discards a delayed previous-subject response", async ({ page }) => {
  await fixture(page);
  await page.route("**/api/v1/contexts", route => route.fulfill({ contentType: "application/json", body: JSON.stringify([
    { id: "subject-a", title: "Subject A", status: "active" },
    { id: "subject-b", title: "Subject B", status: "active" },
  ]) }));
  let release = () => {};
  const held = new Promise<void>(resolve => { release = resolve; });
  let started = () => {};
  const firstRequest = new Promise<void>(resolve => { started = resolve; });
  await page.route("**/api/v1/audio?**", async route => {
    const cid = new URL(route.request().url()).searchParams.get("context_id");
    if (cid === "subject-a") { started(); await held; }
    await route.fulfill({ contentType: "application/json", body: JSON.stringify([{
      id: cid + "-audio", source_type: "NOTE", source_id: cid + "-note",
      title: cid === "subject-a" ? "Previous subject recording" : "Current subject recording",
      status: "READY", content_type: "audio/wav", duration_seconds: 10,
      position_seconds: 0, completed: false, created_at: "2026-10-06",
    }]) });
  });
  await page.goto("/app/audio");
  await firstRequest;
  await page.getByLabel("Active learning context", { exact: true }).selectOption("subject-b");
  await expect(page.getByText("Current subject recording", { exact: true })).toBeVisible();
  const oldResponse = page.waitForResponse(response => response.url().includes("/api/v1/audio?") && response.url().includes("subject-a"));
  release();
  await (await oldResponse).finished();
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect(page.getByText("Previous subject recording", { exact: true })).not.toBeVisible();
  await expect(page.getByText("Current subject recording", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Active learning context", { exact: true })).toHaveValue("subject-b");
});

test("failed audio conversion reports failure and a retry restores playback", async ({ page }) => {
  await fixture(page);
  await page.route("**/api/v1/notes?**", route => route.fulfill({
    contentType: "application/json", body: JSON.stringify([{ id: "review-note", title: "Review note" }]),
  }));
  let attempts = 0;
  await page.route("**/api/v1/audio/notes/review-note/generate", route => {
    attempts += 1;
    return route.fulfill({ contentType: "application/json", body: JSON.stringify({
      id: "review-audio", source_type: "NOTE", source_id: "review-note", text: "Review note",
      status: attempts === 1 ? "FAILED" : "READY", error_detail: null,
      content_type: "audio/wav", duration_seconds: 10, created_at: "2026-10-06",
    }) });
  });
  await page.goto("/app/audio");
  const convert = async () => {
    await page.getByRole("button", { name: "Convert to Audio", exact: true }).first().click();
    await page.getByLabel("Source", { exact: true }).selectOption("note:review-note");
    await page.getByRole("button", { name: "Create Audio", exact: false }).click();
  };
  await convert();
  await expect(page.getByRole("alert").filter({ hasText: "Use Convert to Audio to retry" })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "Please retry or check audio setup" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Play NOTE audio", exact: true })).toBeDisabled();
  await expect(page.getByText("Audio ready.", { exact: true })).not.toBeVisible();
  await convert();
  await expect(page.getByRole("button", { name: "Play NOTE audio", exact: true })).toBeEnabled();
  await expect(page.getByText("Audio ready.", { exact: true })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "Use Convert to Audio to retry" })).toHaveCount(0);
  expect(attempts).toBe(2);
});

test("leaving audio studio releases the playback object URL", async ({ page }) => {
  await page.addInitScript(() => {
    const lifecycle = { created: [] as string[], revoked: [] as string[] };
    Object.assign(window, { reviewAudioLifecycle: lifecycle });
    const create = URL.createObjectURL.bind(URL);
    const revoke = URL.revokeObjectURL.bind(URL);
    URL.createObjectURL = blob => { const url = create(blob); lifecycle.created.push(url); return url; };
    URL.revokeObjectURL = url => { lifecycle.revoked.push(url); revoke(url); };
  });
  await fixture(page, { audio: true });
  await page.goto("/app/audio");
  await page.getByRole("button", { name: "Play NOTE audio", exact: true }).click();
  await expect.poll(() => page.evaluate(() => (window as unknown as { reviewAudioLifecycle: { created: string[] } }).reviewAudioLifecycle.created.length)).toBe(1);
  await page.locator('a[href="/app/roadmaps"]').first().click();
  await expect(page.getByRole("heading", { name: "Roadmaps", exact: true })).toBeVisible();
  const lifecycle = await page.evaluate(() => (window as unknown as { reviewAudioLifecycle: { created: string[]; revoked: string[] } }).reviewAudioLifecycle);
  expect(lifecycle.revoked).toEqual(lifecycle.created);
});

for (const delayed of [false, true]) {
  test(`deleting audio ${delayed ? "during download prevents stale URLs" : "releases its playback URL"}`, async ({ page }) => {
    await page.addInitScript(() => {
      const lifecycle = { created: [] as string[], revoked: [] as string[] };
      Object.assign(window, { reviewAudioLifecycle: lifecycle });
      const create = URL.createObjectURL.bind(URL);
      const revoke = URL.revokeObjectURL.bind(URL);
      URL.createObjectURL = blob => { const url = create(blob); lifecycle.created.push(url); return url; };
      URL.revokeObjectURL = url => { lifecycle.revoked.push(url); revoke(url); };
    });
    await fixture(page, { audio: true });
    let release = () => {};
    const gate = new Promise<void>(resolve => { release = resolve; });
    let started = () => {};
    const downloadStarted = new Promise<void>(resolve => { started = resolve; });
    if (delayed) await page.route("**/api/v1/audio/review-audio/play", async route => {
      started();
      await gate;
      await route.fulfill({ contentType: "audio/wav", body: Buffer.alloc(44) });
    });
    await page.goto("/app/audio");
    await page.getByRole("button", { name: "Play NOTE audio", exact: true }).click();
    if (delayed) await downloadStarted;
    else await expect(page.getByRole("button", { name: "Pause", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Delete NOTE audio", exact: true }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Delete audio", exact: true }).click();
    await expect(page.getByText("Review recording", { exact: true })).not.toBeVisible();
    if (delayed) {
      const response = page.waitForResponse("**/api/v1/audio/review-audio/play");
      release();
      await (await response).finished();
      await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    }
    const lifecycle = await page.evaluate(() => (window as unknown as { reviewAudioLifecycle: { created: string[]; revoked: string[] } }).reviewAudioLifecycle);
    expect(lifecycle.created).toHaveLength(delayed ? 0 : 1);
    expect(lifecycle.revoked).toEqual(lifecycle.created);
    await expect(page.locator("audio")).toHaveCount(0);
  });
}

test("leaving audio saves the position beyond the last periodic update", async ({ page }) => {
  await fixture(page, { audio: true });
  const updates: { position_seconds: number; completed: boolean }[] = [];
  await page.route("**/api/v1/audio/review-audio/progress", async route => {
    const update = route.request().postDataJSON();
    updates.push(update);
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(update) });
  });
  await page.goto("/app/audio");
  await page.getByRole("button", { name: "Play NOTE audio", exact: true }).click();
  await expect(page.locator("audio")).toHaveCount(1);
  await page.locator("audio").evaluate(audio => {
    const player = audio as HTMLAudioElement;
    player.currentTime = 6;
    player.dispatchEvent(new Event("timeupdate"));
  });
  await expect.poll(() => updates.some(update => update.position_seconds === 6)).toBe(true);
  await page.locator("audio").evaluate(audio => {
    const player = audio as HTMLAudioElement;
    player.currentTime = 7;
    player.dispatchEvent(new Event("timeupdate"));
  });
  await page.locator('a[href="/app/roadmaps"]').first().click();
  await expect.poll(() => updates.some(update => update.position_seconds === 7 && !update.completed)).toBe(true);
});

test("roadmap failures display recovery instead of empty state", async ({ page }) => {
  await fixture(page, { roadmapFailure: true });
  await page.goto("/app/roadmaps");
  await expect(page.getByText("This screen could not be loaded.")).toBeVisible();
  await expect(page.getByRole("button", { name: /retry|try again/i })).toBeVisible();
  await expect(page.getByText(/No roadmap yet/)).not.toBeVisible();
});

test("overlapping toasts expire independently", async ({ page }) => {
  await fixture(page);
  await page.goto("/app/roadmaps");
  await expect(page.getByRole("heading", { name: "Roadmaps", exact: true })).toBeVisible();
  const source = readFileSync("lib/toast.ts", "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  await page.evaluate(code => {
    const exports: Record<string, (text: string) => void> = {};
    new Function("exports", code)(exports);
    exports.toast("First review notification");
    window.setTimeout(() => exports.toast("Second review notification"), 500);
  }, compiled);
  await expect(page.getByText("First review notification")).toBeVisible();
  await expect(page.getByText("Second review notification")).toBeVisible();
  await expect(page.getByText("First review notification")).not.toBeVisible({ timeout: 5000 });
  await expect(page.getByText("Second review notification")).not.toBeVisible({ timeout: 5000 });
});

test("shared font tokens resolve the loaded font on the root element", async ({ page }) => {
  await fixture(page);
  await page.goto("/app/roadmaps");
  await expect(page.getByRole("heading", { name: "Roadmaps", exact: true })).toBeVisible();
  const fonts = await page.evaluate(() => {
    const style = getComputedStyle(document.documentElement);
    return { jakarta: style.getPropertyValue("--font-aria-sans").trim(), sans: style.getPropertyValue("--font-sans").trim() };
  });
  expect(fonts.jakarta).not.toBe("");
  expect(fonts.sans).toContain(fonts.jakarta);
});


test("failed sign-out preserves the workspace and reports the failure", async ({ page }) => {
  await fixture(page, { logoutFailure: true });
  await page.goto("/app/roadmaps");
  await expect(page.getByRole("heading", { name: "Roadmaps", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Profile", exact: true }).click();
  const responsePromise = page.waitForResponse(response => response.url().endsWith("/api/v1/auth/signout") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Sign Out", exact: true }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(503);
  await expect(page.getByRole("alert").filter({ hasText: /Sign-out failed/ })).toBeVisible();
  await expect(page).toHaveURL(/\/app\/roadmaps$/);
  await expect(page.getByRole("heading", { name: "Roadmaps", exact: true })).toBeVisible();
});

test("document policy allows microphone access on its own origin", async ({ page }) => {
  await fixture(page);
  const response = await page.goto("/app/roadmaps");
  expect(response?.headers()["permissions-policy"]).toContain("microphone=(self)");
});

test("confirmation contains focus, makes the workspace inert and restores its trigger", async ({ page }) => {
  await fixture(page);
  await page.goto("/app/account");
  const trigger = page.getByRole("button", { name: "Delete this context" });
  await trigger.click();
  const dialog = page.getByRole("alertdialog", { name: "Delete learning context" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Cancel", exact: true })).toBeFocused();
  for (let index = 0; index < 8; index++) {
    await page.keyboard.press(index < 4 ? "Tab" : "Shift+Tab");
    expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true);
  }
  await trigger.evaluate(element => (element as HTMLElement).focus());
  expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test("palette picker closes on Escape, outside click and selection", async ({ page }) => {
  await fixture(page);
  await page.goto("/app/roadmaps");
  const trigger = page.getByRole("button", { name: "Palette settings" });
  await trigger.click();
  await expect(page.getByRole("button", { name: "Select Aurora palette" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(trigger).toHaveAttribute("aria-expanded", "false");
  await expect(trigger).toBeFocused();
  await trigger.click();
  await page.getByRole("heading", { name: "Roadmaps", exact: true }).click();
  await expect(trigger).toHaveAttribute("aria-expanded", "false");
  await trigger.click();
  await page.getByRole("button", { name: "Select Noir Silk palette" }).click();
  await expect(trigger).toBeFocused();
  await expect(trigger).toHaveAttribute("aria-expanded", "false");
});

for (const [mode, label] of [["ai", "AI-generated curriculum"], ["starter", "General starter plan"], ["legacy", "Generation source unknown"]] as const) {
  test(`saved roadmap displays ${mode} provenance after reload`, async ({ page }) => {
    await fixture(page, { roadmapMode: mode });
    await page.goto("/app/roadmaps");
    await expect(page.getByText(label, { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByText(label, { exact: true })).toBeVisible();
  });
}

test("saved unreadable personal key displays recovery instead of ready status", async ({ page }) => {
  await fixture(page, { keyUsable: false });
  await page.goto("/app/account");
  await expect(page.getByRole("alert").filter({ hasText: "Your saved key cannot currently be used" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Remove my key" })).toBeVisible();
});

test("account models come from deployment capabilities", async ({ page }) => {
  await fixture(page);
  await page.goto("/app/account");
  await expect(page.getByLabel("Model", { exact: true })).toHaveValue("deployment-custom-model");
  await expect(page.getByLabel("Model", { exact: true }).locator("option")).toHaveText(["deployment-custom-model"]);
});

test("disabled personal key storage hides the save form", async ({ page }) => {
  await fixture(page, { personalKeysEnabled: false });
  await page.goto("/app/account");
  await expect(page.getByText("Personal AI keys are disabled on this deployment.", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save my key" })).not.toBeVisible();
});

for (const scope of ["own", "other-learner", "other-subject", "legacy"] as const) {
  test(`assessment only offers to resume its own scoped draft: ${scope}`, async ({ page }) => {
    await page.addInitScript((selectedScope) => {
      const key = selectedScope === "own" ? "aria_assess_draft:review-learner:review-context"
        : selectedScope === "other-learner" ? "aria_assess_draft:other-learner:review-context"
        : selectedScope === "other-subject" ? "aria_assess_draft:review-learner:other-subject"
        : "aria_assess_draft";
      localStorage.setItem(key, JSON.stringify({ assessmentId: "review-assessment", attemptId: "saved-attempt", answers: { "review-question": "First option" }, marked: {} }));
    }, scope);
    await fixture(page, { assessment: true });
    await page.goto("/app/assess");
    await expect(page.getByText(scope === "own" ? "Resume test" : "Take test", { exact: true })).toBeVisible();
    await expect(page.getByText(scope === "own" ? "Take test" : "Resume test", { exact: true })).not.toBeVisible();
  });
}

test("assessment keeps answers and warns when draft storage fails", async ({ page }) => {
  await page.addInitScript(() => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function(key, value) {
      if (key.startsWith("aria_assess_draft")) throw new DOMException("Quota exceeded", "QuotaExceededError");
      return original.call(this, key, value);
    };
  });
  await fixture(page, { assessment: true });
  await page.goto("/app/assess");
  await page.getByText("Take test", { exact: true }).click();
  await page.getByLabel("First option", { exact: true }).check();
  await expect(page.getByLabel("First option", { exact: true })).toBeChecked();
  await expect(page.getByRole("alert").filter({ hasText: "Your draft could not be saved" })).toBeVisible();
  await page.getByLabel("Second option", { exact: true }).check();
  await expect(page.getByLabel("Second option", { exact: true })).toBeChecked();
});


test("audio conversion dialog contains focus and restores its trigger", async ({ page }) => {
  await fixture(page, { audio: true });
  await page.goto("/app/audio");
  const trigger = page.getByRole("button", { name: "Convert to Audio", exact: true });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "Convert to Audio" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("Source", { exact: true })).toBeFocused();
  for (let step = 0; step < 8; step++) {
    await page.keyboard.press("Tab");
    expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
});


for (const [path, title] of [["/app/assess", "Create Assessment"], ["/app/roadmaps", "Create Roadmap"]] as const) {
  test(`${title} dialog keeps forward and reverse keyboard focus inside`, async ({ page }) => {
    await fixture(page, { assessment: true });
    await page.goto(path);
    const trigger = page.getByRole("button", { name: title, exact: true }).first();
    await trigger.click();
    const dialog = page.getByRole("dialog", { name: title });
    await expect(dialog).toBeVisible();
    if (title === "Create Roadmap") await expect(dialog.getByLabel("Learning Goal", { exact: true })).toBeFocused();
    for (const key of ["Tab", "Shift+Tab"]) {
      for (let step = 0; step < 14; step++) {
        await page.keyboard.press(key);
        expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true);
      }
    }
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
    await expect(trigger).toBeFocused();
  });
}


for (const [path, title] of [["/app/planner", "Create Exam"], ["/app/planner", "Create Task"], ["/app/materials", "Generate Notes"], ["/app/materials", "Add Resource"]] as const) {
  test(`${title} remaining form dialog supports keyboard dismissal and containment`, async ({ page }) => {
    await fixture(page);
    await page.goto(path);
    if (title === "Create Task") await page.getByRole("button", { name: "Task Planning", exact: true }).click();
    const trigger = page.getByRole("button", { name: title, exact: true }).first();
    await trigger.click();
    const dialog = page.getByRole("dialog", { name: title });
    await expect(dialog).toBeVisible();
    for (const key of ["Tab", "Shift+Tab"]) {
      for (let step = 0; step < 14; step++) {
        await page.keyboard.press(key);
        expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true);
      }
    }
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
    await expect(trigger).toBeFocused();
  });
}


for (const failed of [false, true]) {
  test(`${failed ? "failed" : "successful"} sign-out applies the learner draft cleanup policy`, async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("aria_assess_draft:review-learner:review-context", "own");
      localStorage.setItem("aria_assess_draft:other-learner:review-context", "other");
      localStorage.setItem("aria_assess_draft", "legacy");
    });
    await fixture(page, { logoutFailure: failed });
    await page.goto("/app/roadmaps");
    await page.getByRole("button", { name: "Profile", exact: true }).click();
    await page.getByRole("button", { name: "Sign Out", exact: true }).click();
    if (failed) await expect(page.getByRole("alert").filter({ hasText: "Sign-out failed" })).toBeVisible();
    else await expect(page).toHaveURL(/\/$/);
    const saved = await page.evaluate(() => ({ own: localStorage.getItem("aria_assess_draft:review-learner:review-context"), other: localStorage.getItem("aria_assess_draft:other-learner:review-context"), legacy: localStorage.getItem("aria_assess_draft") }));
    expect(saved).toEqual({ own: failed ? "own" : null, other: "other", legacy: failed ? "legacy" : null });
  });
}


test("blocked draft removal reports remaining device data without failing sign-out", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("aria_assess_draft:review-learner:review-context", "remaining");
    const original = Storage.prototype.removeItem;
    Storage.prototype.removeItem = function(key) {
      if (key.startsWith("aria_assess_draft")) throw new DOMException("Blocked", "SecurityError");
      return original.call(this, key);
    };
  });
  await fixture(page);
  await page.goto("/app/roadmaps");
  await page.getByRole("button", { name: "Profile", exact: true }).click();
  await page.getByRole("button", { name: "Sign Out", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "saved assessment drafts could not be removed" })).toBeVisible();
  await expect(page).toHaveURL(/\/$/);
  expect(await page.evaluate(() => localStorage.getItem("aria_assess_draft:review-learner:review-context"))).toBe("remaining");
});


test("signing into a different learner clears only the previous learner drafts", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("aria_assess_draft:review-learner:review-context", "previous");
    localStorage.setItem("aria_assess_draft:next-learner:review-context", "next");
  });
  await fixture(page);
  const initialIdentity = page.waitForResponse(response => response.url().endsWith("/api/v1/auth/me"));
  await page.goto("/signin");
  await initialIdentity;
  await page.getByLabel("Email", { exact: true }).fill("next@example.com");
  await page.getByLabel("Password", { exact: true }).fill("test-password");
  await page.route("**/api/v1/auth/me", route => route.fulfill({ contentType: "application/json", body: JSON.stringify({ id: "next-learner", email: "next@example.com", verified: true }) }));
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
  const drafts = await page.evaluate(() => ({ previous: localStorage.getItem("aria_assess_draft:review-learner:review-context"), next: localStorage.getItem("aria_assess_draft:next-learner:review-context") }));
  expect(drafts).toEqual({ previous: null, next: "next" });
});


test("regenerating audio revokes old playback and downloads a fresh URL", async ({ page }) => {
  await page.addInitScript(() => {
    const lifecycle = { created: [] as string[], revoked: [] as string[] };
    Object.assign(window, { reviewAudioLifecycle: lifecycle });
    const create = URL.createObjectURL.bind(URL);
    const revoke = URL.revokeObjectURL.bind(URL);
    URL.createObjectURL = blob => { const url = create(blob); lifecycle.created.push(url); return url; };
    URL.revokeObjectURL = url => { lifecycle.revoked.push(url); revoke(url); };
  });
  await fixture(page, { audio: true });
  await page.route("**/api/v1/notes?**", route => route.fulfill({ contentType: "application/json", body: JSON.stringify([{ id: "review-note", title: "Review note" }]) }));
  await page.route("**/api/v1/audio/notes/review-note/generate", route => route.fulfill({ contentType: "application/json", body: JSON.stringify({ id: "review-audio", source_type: "NOTE", source_id: "review-note", title: "Regenerated recording", status: "READY", content_type: "audio/wav", duration_seconds: 10, created_at: "2026-10-06" }) }));
  await page.goto("/app/audio");
  await page.getByRole("button", { name: "Play NOTE audio", exact: true }).click();
  await expect(page.locator("audio")).toHaveCount(1);
  const previous = await page.locator("audio").getAttribute("src");
  await page.getByRole("button", { name: "Convert to Audio", exact: true }).click();
  await page.getByLabel("Source", { exact: true }).selectOption("note:review-note");
  await page.getByRole("button", { name: "Create Audio", exact: false }).click();
  await expect(page.getByText("Audio ready.", { exact: true })).toBeVisible();
  await expect(page.locator("audio")).toHaveCount(0);
  await page.getByRole("button", { name: "Play NOTE audio", exact: true }).click();
  await expect(page.locator("audio")).toHaveCount(1);
  const current = await page.locator("audio").getAttribute("src");
  expect(current).not.toBe(previous);
  const lifecycle = await page.evaluate(() => (window as unknown as { reviewAudioLifecycle: { created: string[]; revoked: string[] } }).reviewAudioLifecycle);
  expect(lifecycle.created).toEqual([previous, current]);
  expect(lifecycle.revoked).toEqual([previous]);
  await page.locator('a[href="/app/roadmaps"]').first().click();
  await expect(page.getByRole("heading", { name: "Roadmaps", exact: true })).toBeVisible();
  expect(await page.evaluate(() => (window as unknown as { reviewAudioLifecycle: { revoked: string[] } }).reviewAudioLifecycle.revoked)).toEqual([previous, current]);
});


test("switching audio tracks flushes the previous track's latest position", async ({ page }) => {
  await fixture(page, { audio: true });
  const recordings = ["first", "second"].map(id => ({ id, source_type: "NOTE", source_id: id + "-note", title: id + " recording", status: "READY", content_type: "audio/wav", duration_seconds: 20, position_seconds: 0, completed: false, created_at: "2026-10-07" }));
  await page.route("**/api/v1/audio?**", route => route.fulfill({ contentType: "application/json", body: JSON.stringify(recordings) }));
  await page.route("**/api/v1/audio/*/play", route => route.fulfill({ contentType: "audio/wav", body: Buffer.alloc(44) }));
  const updates: { id: string; position_seconds: number; completed: boolean }[] = [];
  await page.route("**/api/v1/audio/*/progress", route => {
    const data = route.request().postDataJSON();
    updates.push({ id: new URL(route.request().url()).pathname.split("/").at(-2)!, ...data });
    return route.fulfill({ contentType: "application/json", body: JSON.stringify(data) });
  });
  await page.goto("/app/audio");
  const play = page.getByRole("button", { name: "Play NOTE audio", exact: true });
  await play.first().click();
  await expect(page.locator("audio")).toHaveCount(1);
  await page.locator("audio").evaluate(element => {
    const audio = element as HTMLAudioElement;
    audio.currentTime = 6;
    audio.dispatchEvent(new Event("timeupdate"));
  });
  await expect.poll(() => updates.some(update => update.id === "first" && update.position_seconds === 6)).toBe(true);
  await page.locator("audio").evaluate(element => {
    const audio = element as HTMLAudioElement;
    audio.currentTime = 7;
    audio.dispatchEvent(new Event("timeupdate"));
  });
  await play.click();
  await expect.poll(() => updates.some(update => update.id === "first" && update.position_seconds === 7 && !update.completed)).toBe(true);
  await expect(page.locator("audio")).toHaveCount(1);
  await expect(page.locator(".audio-card").filter({ hasText: "second recording" }).locator("audio")).toHaveCount(1);
});


test("regenerating during a held playback download rejects the stale response", async ({ page }) => {
  await page.addInitScript(() => {
    const lifecycle = { created: [] as string[], revoked: [] as string[] };
    Object.assign(window, { reviewAudioLifecycle: lifecycle });
    const create = URL.createObjectURL.bind(URL);
    const revoke = URL.revokeObjectURL.bind(URL);
    URL.createObjectURL = blob => { const url = create(blob); lifecycle.created.push(url); return url; };
    URL.revokeObjectURL = url => { lifecycle.revoked.push(url); revoke(url); };
  });
  await fixture(page, { audio: true });
  await page.route("**/api/v1/notes?**", route => route.fulfill({ contentType: "application/json", body: JSON.stringify([{ id: "review-note", title: "Review note" }]) }));
  await page.route("**/api/v1/audio/notes/review-note/generate", route => route.fulfill({ contentType: "application/json", body: JSON.stringify({ id: "review-audio", source_type: "NOTE", source_id: "review-note", title: "Fresh recording", status: "READY", content_type: "audio/wav", duration_seconds: 10, created_at: "2026-10-07" }) }));
  let release = () => {};
  const gate = new Promise<void>(resolve => { release = resolve; });
  let started = () => {};
  const pending = new Promise<void>(resolve => { started = resolve; });
  let downloads = 0;
  await page.route("**/api/v1/audio/review-audio/play", async route => {
    downloads += 1;
    if (downloads === 1) { started(); await gate; }
    await route.fulfill({ contentType: "audio/wav", body: Buffer.alloc(44) });
  });
  await page.goto("/app/audio");
  await page.getByRole("button", { name: "Play NOTE audio", exact: true }).click();
  await pending;
  await page.getByRole("button", { name: "Convert to Audio", exact: true }).click();
  await page.getByLabel("Source", { exact: true }).selectOption("note:review-note");
  await page.getByRole("button", { name: "Create Audio", exact: false }).click();
  await expect(page.getByText("Audio ready.", { exact: true })).toBeVisible();
  const oldResponse = page.waitForResponse("**/api/v1/audio/review-audio/play");
  release();
  await (await oldResponse).finished();
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect(page.locator("audio")).toHaveCount(0);
  expect(await page.evaluate(() => (window as unknown as { reviewAudioLifecycle: { created: string[] } }).reviewAudioLifecycle.created)).toHaveLength(0);
  await page.getByRole("button", { name: "Play NOTE audio", exact: true }).click();
  await expect(page.locator("audio")).toHaveCount(1);
  expect(downloads).toBe(2);
  expect(await page.evaluate(() => (window as unknown as { reviewAudioLifecycle: { created: string[] } }).reviewAudioLifecycle.created)).toHaveLength(1);
});


test("expired sign-in notice renders without a server/client hydration mismatch", async ({ page }) => {
  const hydrationErrors: string[] = [];
  page.on("console", message => {
    if (message.type() === "error" && /hydration|didn't match|server rendered/i.test(message.text())) {
      hydrationErrors.push(message.text());
    }
  });
  await fixture(page, { anonymous: true });
  await page.goto("/signin?reason=expired");
  await expect(page.getByText("Your session expired. Sign in again to continue.")).toBeVisible();
  await expect(page.getByLabel("Email")).toBeEnabled();
  expect(hydrationErrors).toEqual([]);
});
