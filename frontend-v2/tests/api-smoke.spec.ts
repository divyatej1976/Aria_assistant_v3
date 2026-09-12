import { expect, request, test, type APIRequestContext } from "@playwright/test";

/**
 * API smoke across every endpoint family, against the isolated E2E backend.
 * Complements the UI specs: catches backend regressions on paths the UI
 * does not exercise (transcribe failure mode, idempotent resubmit,
 * cross-owner isolation, reminder-check duplication behaviour).
 */

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

type Ctx = { ctx: APIRequestContext; csrf: string };

async function registerAndLogin(device: string): Promise<{ user: Ctx; email: string; password: string }> {
  const email = `api-smoke-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
  const password = "testing-12345";
  const boot = await request.newContext({ baseURL: API });
  const reg = await boot.post("/api/v1/auth/register", {
    data: { display_name: "API Smoke", email, password },
  });
  expect(reg.status(), await reg.text()).toBe(201);
  await boot.dispose();

  const ctx = await request.newContext({ baseURL: API });
  const login = await ctx.post("/api/v1/auth/login", {
    data: { email, password, device_label: device },
  });
  expect(login.status()).toBe(200);
  const csrf = login
    .headersArray()
    .filter((h) => h.name.toLowerCase() === "set-cookie" && h.value.startsWith("aria_csrf="))
    .map((h) => /aria_csrf=([^;]+)/.exec(h.value)?.[1])
    .find(Boolean) ?? "";
  return { user: { ctx, csrf }, email, password };
}

function authed(ctx: Ctx): Record<string, string> {
  return { "X-CSRF-Token": ctx.csrf };
}

let family: Ctx;
let email: string;
let password: string;
let contextId = "";

test.beforeAll(async () => {
  const reg = await registerAndLogin("api-smoke-main");
  family = reg.user;
  email = reg.email;
  password = reg.password;
});

test.afterAll(async () => {
  await family.ctx.dispose();
});

async function createContext(title: string): Promise<string> {
  const res = await family.ctx.post("/api/v1/contexts", {
    headers: authed(family),
    data: { title, configuration: { mastery_level: "beginner" } },
  });
  expect(res.status(), await res.text()).toBe(201);
  return (await res.json()).id as string;
}

// Order-isolation: tests share the module-level contextId set by the
// contexts test. If ordering/retries shift, downstream tests would send an
// empty context_id and get 422s. Lazily create it instead of assuming order.
async function ensureContextId(): Promise<string> {
  if (!contextId) contextId = await createContext("Smoke Context");
  return contextId;
}

const MATERIAL_TEXT =
  "A function is a reusable block of code. def defines a function. "
  + "Arguments are passed when calling a function. A function returns a value with return. "
  + "Loops repeat a block while a condition holds true in Python programs.";

async function seedMaterial(cid: string): Promise<string> {
  const res = await family.ctx.post("/api/v1/resources/text", {
    headers: authed(family),
    data: { context_id: cid, title: "Smoke Material", text: MATERIAL_TEXT },
  });
  expect(res.status()).toBe(201);
  return ((await res.json()) as { id: string }).id;
}

test("health endpoint responds", async () => {
  const res = await family.ctx.get("/health");
  expect(res.status()).toBe(200);
  expect(((await res.json()) as { status: string }).status).toBe("ok");
});

test("auth: me, profile update, and password change revoking other sessions", async () => {
  const me = await family.ctx.get("/api/v1/auth/me");
  expect(me.status()).toBe(200);
  expect(((await me.json()) as { email: string }).email).toBe(email);

  const patched = await family.ctx.patch("/api/v1/auth/profile", {
    headers: authed(family),
    data: { display_name: "Renamed Smoke" },
  });
  expect(patched.status()).toBe(200);
  expect(((await patched.json()) as { display_name: string | null }).display_name).toBe("Renamed Smoke");

  // second session for the same user
  const second = await registerAndLogin("unused"); // registers extra user; ignore
  void second;
  const other = await request.newContext({ baseURL: API });
  const login2 = await other.post("/api/v1/auth/login", {
    data: { email, password, device_label: "smoke-second" },
  });
  expect(login2.status()).toBe(200);

  const pw = await family.ctx.post("/api/v1/auth/password", {
    headers: authed(family),
    data: { current_password: password, new_password: "rotated-pw-987654" },
  });
  expect(pw.status()).toBe(200);

  // old session is now dead
  const after = await other.get("/api/v1/auth/me");
  expect(after.status()).toBe(401);
  // main session survives
  expect((await family.ctx.get("/api/v1/auth/me")).status()).toBe(200);

  // rotate back so later families keep using `password`
  const back = await family.ctx.post("/api/v1/auth/password", {
    headers: authed(family),
    data: { current_password: "rotated-pw-987654", new_password: password },
  });
  expect(back.status()).toBe(200);
  await other.dispose();
});

test("contexts: create, list, get; preferences round-trip", async () => {
  contextId = await createContext("Smoke Context");
  const list = await family.ctx.get("/api/v1/contexts").then((r) => r.json());
  expect(Array.isArray(list)).toBe(true);
  expect(list.some((c: { id: string }) => c.id === contextId)).toBe(true);

  for (const [key, value] of [["smoke_key", "v1"], ["notify_reminders", "true"]] as const) {
    const put = await family.ctx.put("/api/v1/me/preferences", {
      headers: authed(family),
      data: { key, value },
    });
    expect(put.status()).toBe(200);
    const prefs = await family.ctx.get("/api/v1/me/preferences").then((r) => r.json());
    expect(prefs.find((p: { key: string }) => p.key === key)?.value).toBe(value);
  }
});

test("study: session create/list + fallback message with sources metadata", async ({ page }) => {
  void page;
  await ensureContextId();
  const created = await family.ctx.post("/api/v1/study/sessions", {
    headers: authed(family),
    data: { context_id: contextId, mode: "CHAT" },
  });
  expect(created.status()).toBe(201);
  const sessionId = ((await created.json()) as { id: string }).id;

  const listed = await family.ctx
    .get(`/api/v1/study/sessions?context_id=${contextId}`)
    .then((r) => r.json());
  expect(listed.some((s: { id: string }) => s.id === sessionId)).toBe(true);

  const msg = await family.ctx.post(`/api/v1/study/sessions/${sessionId}/messages`, {
    headers: authed(family),
    data: { content: "Explain Python functions" },
  });
  expect(msg.ok(), `message failed: ${msg.status()} ${await msg.text()}`).toBe(true);
  const body = await msg.json();
  expect(body.content.length).toBeGreaterThan(0);
  expect(typeof body.fallback_used).toBe("boolean");

  const messages = await family.ctx
    .get(`/api/v1/study/sessions/${sessionId}/messages`)
    .then((r) => r.json());
  expect(messages.length).toBeGreaterThanOrEqual(2); // learner + aria

  // delete the session; messages cascade
  const del = await family.ctx.delete(`/api/v1/study/sessions/${sessionId}`, { headers: authed(family) });
  expect(del.status()).toBe(200);
  const listedAfter = await family.ctx
    .get(`/api/v1/study/sessions?context_id=${contextId}`)
    .then((r) => r.json());
  expect(listedAfter.some((s: { id: string }) => s.id === sessionId)).toBe(false);
});

test("assessments: full lifecycle incl. idempotent resubmit", async () => {
  await ensureContextId();
  await seedMaterial(contextId);
  await family.ctx.post(`/api/v1/contexts/${contextId}/concepts/sync`, { headers: authed(family) });

  const created = await family.ctx.post("/api/v1/assessments", {
    headers: authed(family),
    data: { context_id: contextId, format: "mcq", question_count: 3, difficulty: "easy" },
  });
  expect(created.status(), await created.text()).toBe(201);
  const aid = ((await created.json()) as { id: string }).id;

  const started = await family.ctx.post(`/api/v1/assessments/${aid}/attempts`, { headers: authed(family) });
  expect(started.status()).toBe(201);
  const attempt = await started.json();
  const answers = Object.fromEntries(
    (attempt.questions as { id: string; options: string[] }[]).map((q) => [q.id, q.options[0]]),
  );

  const saved = await family.ctx.put(
    `/api/v1/assessments/${aid}/attempts/${attempt.attempt_id}/answers`,
    { headers: authed(family), data: { answers } },
  );
  expect(saved.status()).toBe(200);

  const key = `smoke-${Date.now()}`;
  const first = await family.ctx.post(
    `/api/v1/assessments/${aid}/attempts/${attempt.attempt_id}/submit`,
    { headers: authed(family), data: { idempotency_key: key, answers } },
  );
  expect(first.status()).toBe(200);
  const result = await first.json();

  // idempotent replay returns the SAME evaluation, not a duplicate
  const replay = await family.ctx.post(
    `/api/v1/assessments/${aid}/attempts/${attempt.attempt_id}/submit`,
    { headers: authed(family), data: { idempotency_key: key, answers } },
  );
  expect(replay.status()).toBe(200);
  expect(((await replay.json()) as { attempt_id: string }).attempt_id).toBe(result.attempt_id);
  expect(((await replay.json()) as { evaluation_id: string }).evaluation_id).toBe(result.evaluation_id);

  // scoring consistency: details length equals question count, score within range
  expect(result.details.length).toBe(attempt.questions.length);
  expect(result.score).toBeGreaterThanOrEqual(0);
  expect(result.score).toBeLessThanOrEqual(result.total);
});

test("notes: create, generate-from-session, review, download PDF, delete", async () => {
  await ensureContextId();
  // create
  const made = await family.ctx.post("/api/v1/notes", {
    headers: authed(family),
    data: { context_id: contextId, title: "Manual Note", body: "Remember to revise functions." },
  });
  expect(made.status()).toBe(201);
  const note = await made.json();

  // generate from the study material (no session -> chunk path)
  const gen = await family.ctx.post("/api/v1/notes/generate", {
    headers: authed(family),
    data: { context_id: contextId },
  });
  expect(gen.status(), await gen.text()).toBe(201);

  // spaced repetition: good outcome advances the interval
  const reviewed = await family.ctx.post(`/api/v1/notes/${note.id}/review`, {
    headers: authed(family),
    data: { outcome: "good" },
  });
  expect(reviewed.status()).toBe(200);
  const reviewedBody = await reviewed.json();
  expect(reviewedBody.interval_days).toBeGreaterThan(1);

  // due list is reachable
  const due = await family.ctx.get(`/api/v1/notes/due?context_id=${contextId}`);
  expect(due.status()).toBe(200);

  // PDF download
  const pdf = await family.ctx.get(`/api/v1/notes/${note.id}/download`);
  expect(pdf.status()).toBe(200);
  expect(pdf.headers()["content-type"]).toContain("application/pdf");

  // delete cleans up
  const del = await family.ctx.delete(`/api/v1/notes/${note.id}`, { headers: authed(family) });
  expect(del.status()).toBe(200);
});

test("audio: generate from resource, play bytes, progress round-trip, delete", async () => {
  await ensureContextId();
  const resources = await family.ctx
    .get(`/api/v1/resources?context_id=${contextId}`)
    .then((r) => r.json());
  expect(resources.length).toBeGreaterThan(0);
  const rid = resources[0].id as string;

  const gen = await family.ctx.post(`/api/v1/audio/resources/${rid}/generate`, { headers: authed(family) });
  expect(gen.status(), await gen.text()).toBe(201);
  const artifact = await gen.json();
  expect(artifact.status).toBe("READY");

  const played = await family.ctx.get(`/api/v1/audio/${artifact.id}/play`);
  expect(played.status()).toBe(200);
  expect(played.headers()["content-type"]).toContain("audio/");

  const put = await family.ctx.put(`/api/v1/audio/${artifact.id}/progress`, {
    headers: authed(family),
    data: { position_seconds: 12, completed: false },
  });
  expect(put.status()).toBe(200);
  const got = await family.ctx.get(`/api/v1/audio/${artifact.id}/progress`).then((r) => r.json());
  expect(got.position_seconds).toBe(12);
  expect(got.completed).toBe(false);

  const del = await family.ctx.delete(`/api/v1/audio/${artifact.id}`, { headers: authed(family) });
  expect(del.status()).toBe(200);
});

test("settings: BYO LLM key round-trip never exposes plaintext", async () => {
  const empty = await family.ctx.get("/api/v1/settings/llm-key").then((r) => r.json());
  expect(empty.configured).toBe(false);

  const bad = await family.ctx.post("/api/v1/settings/llm-key", {
    headers: authed(family),
    data: { key: "not-a-groq-key" },
  });
  expect(bad.status()).toBe(422);

  const key = `gsk_e2e${"k".repeat(36)}`;
  const saved = await family.ctx.post("/api/v1/settings/llm-key", {
    headers: authed(family),
    data: { key, model: "openai/gpt-oss-20b" },
  });
  expect(saved.status(), await saved.text()).toBe(201);
  const savedBody = await saved.json();
  expect(savedBody.configured).toBe(true);
  expect(savedBody.hint).toBe(`...${key.slice(-4)}`);
  expect(JSON.stringify(savedBody)).not.toContain(key);

  const status = await family.ctx.get("/api/v1/settings/llm-key").then((r) => r.json());
  expect(status.configured).toBe(true);
  expect(status.provider).toBe("groq");
  expect(JSON.stringify(status)).not.toContain(key);

  const del = await family.ctx.delete("/api/v1/settings/llm-key", { headers: authed(family) });
  expect(del.status()).toBe(200);
  const gone = await family.ctx.delete("/api/v1/settings/llm-key", { headers: authed(family) });
  expect(gone.status()).toBe(404);
});

test("transcribe degrades gracefully without an STT key", async () => {
  const res = await family.ctx.post("/api/v1/audio/transcribe", {
    headers: authed(family),
    multipart: { file: { name: "clip.webm", mimeType: "audio/webm", buffer: Buffer.from("not-real-audio") } },
  });
  // Either 422 (provider rejects payload) or 501/503 when unconfigured — never 500.
  expect([400, 422, 501, 503]).toContain(res.status());
});

test("planner: deadline/task CRUD, reminders check, duplicate-call probe", async () => {
  await ensureContextId();
  // 7 days out so the default 5-day reminder window is still in the future
  // (a reminder date in the past fails deadline validation with 422).
  const dueAt = new Date(Date.now() + 7 * 86_400_000).toISOString();
  const exam = await family.ctx.post("/api/v1/planner/deadlines", {
    headers: authed(family),
    data: { context_id: contextId, title: "Smoke Exam", due_at: dueAt, reminder_days_before: 5 },
  });
  expect(exam.status()).toBe(201);
  const examId = ((await exam.json()) as { id: string }).id;

  const task = await family.ctx.post("/api/v1/planner/tasks", {
    headers: authed(family),
    data: { context_id: contextId, title: "Smoke Task" },
  });
  expect(task.status()).toBe(201);
  const taskId = ((await task.json()) as { id: string }).id;

  const doneTask = await family.ctx.post(`/api/v1/planner/tasks/${taskId}/complete`, { headers: authed(family) });
  expect(doneTask.ok()).toBe(true);

  const upcoming = await family.ctx.get("/api/v1/planner/upcoming?days=30");
  expect(upcoming.ok()).toBe(true);

  const firstCheck = await family.ctx.post("/api/v1/planner/reminders/check", { headers: authed(family) });
  expect(firstCheck.ok()).toBe(true);
  const firstCount = ((await firstCheck.json()) as { notifications_created: number }).notifications_created;

  const before = await family.ctx.get("/api/v1/notifications").then((r) => r.json());
  const secondCheck = await family.ctx.post("/api/v1/planner/reminders/check", { headers: authed(family) });
  const secondCount = ((await secondCheck.json()) as { notifications_created: number }).notifications_created;
  const after = await family.ctx.get("/api/v1/notifications").then((r) => r.json());

  if (secondCount > 0 || after.length > before.length) {
    console.log(`NOTE: reminders/check is not deduped (first=${firstCount}, second=${secondCount}) — duplicates possible on repeat calls`);
  }

  // cleanup exam
  const delExam = await family.ctx.delete(`/api/v1/planner/deadlines/${examId}`, { headers: authed(family) });
  expect(delExam.ok()).toBe(true);
});

test("notifications: unread count, mark read, read-all", async () => {
  const list = await family.ctx.get("/api/v1/notifications").then((r) => r.json());
  const unreadBefore = list.filter((n: { read_at: string | null }) => n.read_at === null).length;

  const countRes = await family.ctx.get("/api/v1/notifications/unread-count").then((r) => r.json());
  expect(countRes.unread).toBe(unreadBefore);

  if (unreadBefore > 0) {
    const target = list.find((n: { read_at: string | null }) => n.read_at === null);
    const marked = await family.ctx.post(`/api/v1/notifications/${target.id}/read`, { headers: authed(family) });
    expect(marked.status()).toBe(200);
  }
  const all = await family.ctx.post("/api/v1/notifications/read-all", { headers: authed(family) });
  expect(all.status()).toBe(200);
  const zero = await family.ctx.get("/api/v1/notifications/unread-count").then((r) => r.json());
  expect(zero.unread).toBe(0);
});

test("progress + adaptation surfaces respond with real shapes", async () => {
  await ensureContextId();
  const consistency = await family.ctx.get("/api/v1/progress/consistency").then((r) => r.json());
  expect(typeof consistency.current_streak).toBe("number");
  expect(Array.isArray(consistency.heatmap)).toBe(true);
  expect(consistency.heatmap.length).toBeGreaterThan(0);

  const badges = await family.ctx.get("/api/v1/progress/badges").then((r) => r.json());
  expect(badges.length).toBeGreaterThanOrEqual(8);

  const activity = await family.ctx.get("/api/v1/progress/activity").then((r) => r.json());
  expect(Array.isArray(activity)).toBe(true);

  const adaptationRes = await family.ctx.get(`/api/v1/contexts/${contextId}/adaptation`);
  const adaptation = await adaptationRes.json();
  expect(adaptationRes.status(), JSON.stringify(adaptation)).toBe(200);
  expect(Array.isArray(adaptation.states)).toBe(true);

  const evidence = await family.ctx
    .get(`/api/v1/contexts/${contextId}/evidence`)
    .then((r) => r.json());
  expect(Array.isArray(evidence)).toBe(true);

  if (evidence.some((e: { valid: boolean }) => e.valid)) {
    const target = evidence.find((e: { valid: boolean }) => e.valid);
    const inv = await family.ctx.post(
      `/api/v1/contexts/${contextId}/evidence/${target.id}/invalidate`,
      { headers: authed(family) },
    );
    expect(inv.status()).toBe(200);
  }
});

test("data controls: export contains learner data; context deletion cascades", async () => {
  const reg = await registerAndLogin("api-smoke-data");
  const { ctx, csrf } = reg.user;
  const h = { "X-CSRF-Token": csrf };
  try {
    const ctxRes = await ctx.post("/api/v1/contexts", {
      headers: h,
      data: { title: "Export Context", configuration: { mastery_level: "beginner" } },
    });
    expect(ctxRes.status()).toBe(201);
    const cid = ((await ctxRes.json()) as { id: string }).id;

    await ctx.post("/api/v1/resources/text", {
      headers: h,
      data: { context_id: cid, title: "Exp Res", text: MATERIAL_TEXT_SMOKE },
    });
    const note = await ctx.post("/api/v1/notes", {
      headers: h,
      data: { context_id: cid, title: "Exp Note", body: "remember this" },
    });
    expect(note.status()).toBe(201);

    // export is a JSON attachment containing our context/note/resource
    const exp = await ctx.get("/api/v1/account/export");
    expect(exp.status()).toBe(200);
    expect(exp.headers()["content-type"]).toContain("application/json");
    expect(exp.headers()["content-disposition"]).toContain("attachment");
    const body = (await exp.json()) as {
      profile: { email: string };
      contexts: { title: string }[];
      notes: { title: string }[];
      resources: { title: string }[];
    };
    expect(body.profile.email).toBe(reg.email);
    expect(body.contexts.some((c) => c.title === "Export Context")).toBe(true);
    expect(body.notes.some((n) => n.title === "Exp Note")).toBe(true);
    expect(body.resources.some((r) => r.title === "Exp Res")).toBe(true);

    // deleting the context cascades: gone from list, children 404
    const del = await ctx.delete(`/api/v1/contexts/${cid}`, { headers: h });
    expect(del.status()).toBe(200);
    const after = await ctx.get("/api/v1/contexts").then((r) => r.json());
    expect(after.some((c: { id: string }) => c.id === cid)).toBe(false);
    const notesAfter = await ctx.get(`/api/v1/notes?context_id=${cid}`);
    // 404 explicit or 422 via the domain ValidationError contract.
    expect([404, 422]).toContain(notesAfter.status());
  } finally {
    await ctx.dispose();
  }
});

// shared material text for the export test above
const MATERIAL_TEXT_SMOKE =
  "A function is a reusable block of code. def defines a function. Arguments are passed when calling.";

test("push: subscribe, list, unsubscribe round-trip (endpoint-only body like the UI)", async () => {
  const sub = { endpoint: "https://push.example/smoke-1", p256dh: "k1", auth: "a1" };
  const on = await family.ctx.post("/api/v1/push/subscribe", { headers: authed(family), data: sub });
  expect(on.status()).toBe(201);

  const listed = await family.ctx.get("/api/v1/push/subscriptions").then((r) => r.json());
  expect(listed.some((s: { endpoint: string }) => s.endpoint === sub.endpoint)).toBe(true);

  // The browser teardown only knows the endpoint (keys may be gone):
  // endpoint-only must unsubscribe successfully (regression for the old 422).
  const off = await family.ctx.post("/api/v1/push/unsubscribe", {
    headers: authed(family),
    data: { endpoint: sub.endpoint },
  });
  expect(off.status()).toBe(200);
  expect(((await off.json()) as { unsubscribed: boolean }).unsubscribed).toBe(true);

  // Unknown endpoint reports not-unsubscribed rather than erroring.
  const offAgain = await family.ctx.post("/api/v1/push/unsubscribe", {
    headers: authed(family),
    data: { endpoint: sub.endpoint },
  });
  expect(offAgain.status()).toBe(200);
  expect(((await offAgain.json()) as { unsubscribed: boolean }).unsubscribed).toBe(false);
});

test("cross-owner isolation: learner B cannot touch learner A's data", async () => {
  await ensureContextId();
  const other = await registerAndLogin("api-smoke-other");
  try {
    const contextsB = await other.user.ctx.get("/api/v1/contexts").then((r) => r.json());
    expect(contextsB.some((c: { id: string }) => c.id === contextId)).toBe(false);

    const notesB = await other.user.ctx
      .get(`/api/v1/notes?context_id=${contextId}`)
      .then((r) => r.status());
    // Foreign/unknown context: 404 (explicit) or 422 (domain ValidationError
    // contract) — never learner A's notes.
    if (notesB === 200) {
      const body = await other.user.ctx.get(`/api/v1/notes?context_id=${contextId}`).then((r) => r.json());
      expect(body.length).toBe(0);
    } else {
      expect([404, 422]).toContain(notesB);
    }

    const adaptB = await other.user.ctx.get(`/api/v1/contexts/${contextId}/adaptation`);
    expect([403, 404, 422]).toContain(adaptB.status());

    const sessionsB = await other.user.ctx.get("/api/v1/auth/sessions");
    expect(sessionsB.status()).toBe(200); // own sessions only; just must not leak A's
  } finally {
    await other.user.ctx.dispose();
  }
});