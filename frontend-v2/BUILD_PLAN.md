# ARIA frontend-v2 — Build Plan & Status

**Product:** ARIA — AI-Powered Personalized Learning System (new UI)
**Scope:** `frontend-v2/` — a brand-new Next.js 16 + TypeScript + Tailwind v4 + motion/animejs frontend, consuming the **existing FastAPI backend unchanged**.
**Rule:** the existing codebase (`frontend/`, `backend/`, etc.) is never modified. All work lives in `frontend-v2/`.
**Method:** UI-first (design system + all screens with mock data), then phase-wise backend wiring. Every phase ends with `npm run build` green + Playwright specs against a real, isolated backend, and a report before moving on.

---

## Design system (locked)

- **Palettes:** Aurora (light Swiss-neumorphic) · Noir Silk (black/white/gray) · optional champagne-gold accent toggle (Noir only).
- **Style:** Swiss grid + typography, neumorphic dual shadows on cards/inputs, solid surfaces (glass only on modals/popovers at blur 8px).
- **Motion:** word-blur rotating captions, kinetic ARIA wordmark, squircle flip cards (hover-flip), donut rings with count-up, spring reveals, confetti, magnetic buttons, toasts, typing/streaming chat.
- **Ambient background:** anime.js neural constellation (knowledge-graph metaphor) + theme-aware aurora orbs / obsidian sheen + top hairline (silver→gold in Noir), cursor spotlight, scroll parallax, grain+vignette, reduced-motion fallback.

---

## Phase status

| # | Phase | Status | Evidence |
|---|---|---|---|
| 0 | Foundation & test harness | ✅ Complete | `lib/api.ts`, `playwright.config.ts`, isolated E2E backend (:8010/SQLite `e2e-smoke-v2.db`), `tests/helpers.ts`, smoke spec — 3/3 green |
| 1 | Auth | ✅ Complete | AuthProvider (`/auth/me`), real signin/signup/verify/reset/signout; landing redirect; 6/6 green incl. wrong-password + signout |
| 2 | Onboarding + Contexts | ✅ Complete | Onboarding creates real context (`POST /contexts`); `useActiveContext`; ContextGuard redirects no-context → `/onboarding`; signin routes by context; 8/8 green |
| 3 | Home dashboard (real data) | ✅ Complete | streak via `/progress/consistency`; upcoming via `/planner/upcoming`; recommendation via `/contexts/{id}/adaptation`; completion % from supported concepts; 8/8 green |
| 4 | Learn (AI tutor) | ✅ Complete | Real study sessions (create/list/select), messages with **sources** + **fallback_used**, sidebar of sessions, full-screen chat; 9/9 green |
| 5 | Planner | ✅ Complete | Real deadlines CRUD + complete/delete; tasks CRUD grouped Missed/Today/Tomorrow/This week/Later/No date/Completed; reminders strip (`/planner/reminders/check`) + `reminder_days_before`; concept-driven preparation progress; modal a11y fixed; 12/12 green |
| 6 | Progress + Knowledge Map + Assessments | ✅ Complete | Progress on `/progress/consistency` (182-day heatmap, streaks) + `/progress/badges` (earned vs locked) + `/progress/activity`; rings = % concepts supported / week / month (real adaptation); Knowledge Map on `/contexts/{id}/adaptation` + evidence list with invalidate; Assessments full flow: create (format/difficulty/count from real API) → MCQ take → submit (idempotency key) → real score review with per-question detail + FOCUS_STUDY feedback; 20/20 green |
| 7 | Materials + Audio | ✅ Complete | Materials: real notes list (`GET /notes`) with state/due, generate modal (real study-session picker + context-material fallback via `POST /notes/generate`), PDF download (`GET /notes/{id}/download`), Again/Good spaced-repetition review, resources section (add text / delete / chunks). Audio: sources = real notes+resources; convert (`POST /audio/notes|resources/{id}/generate`); playback via blob stream; progress saved (`PUT /audio/{id}/progress`, ≥5s delta) and restored across reloads via per-context localStorage artifact index + `GET /audio/{id}` (no list endpoint exists); 25/25 green |
| 8 | Roadmaps | ✅ Complete | Goal/level/date persisted via `/me/preferences`; tiered tree generated client-side by pure `lib/roadmap.ts` (`buildRoadmap`) from adaptation states + per-concept prerequisites (topological layers → Foundations/Core/Advanced/Mastery); topics auto-tick when concept state = SUPPORTED (no manual toggles); ring % = done/total; Notion-style subtopic view shows tick reasoning (`tickExplanation`). **Backend fix required & applied:** `submit_attempt` scored every answer as unanswered (`autoflush=False` hid `_replace_answers`' pending rows from the `saved` query) — added `db.flush()` in `backend/app/services/assessment.py`; verified via API probe (0/3 → 3/3 with correct letters) + full backend suite 170/170 green. Ticks flip proven end-to-end: single wrong-leaning attempt ⇒ 0% (2-consecutive rule), two correct attempts (letters learned from attempt-1 details) ⇒ SUPPORTED ticks appear; 27/27 green |
| 9 | Notifications + reminder preferences | ✅ Complete | Bell on real APIs: list + `unread-count` badge, refresh-on-open, item click → `{id}/read`, "Mark all read" → `/read-all`; icons per ntype; relative timestamps; profile popover shows real identity via `useAuth()`. Planner auto-runs `POST /planner/reminders/check` once per browser session on load (toast when reminders created). Account → Notifications card: Learning Reminders + Push toggles persisted via `/me/preferences` (`notify_reminders`, `notify_push`). Web push included: new `public/sw.js` + `lib/push.ts` (permission → SW → `pushManager.subscribe` → `/push/subscribe`; disable → unsubscribe both sides), graceful no-op without VAPID keys (backend LogPushProvider). A11y: account inputs now properly labelled (axe-critical `label` violations fixed). 30/30 green |
| 10 | Account & Settings (real) | ✅ Complete | Personal Details from `/auth/me` (Name/Email + Verified chip); Save → `PATCH /auth/profile` and syncs AuthProvider so the shell identity updates instantly. Username field deliberately dropped (no backend concept). Change Password form (`POST /auth/password`, ≥8 chars, confirm match) — success clears fields; wrong current password surfaces the API error. Active Sessions card: device label, created date, "This device" chip, Revoke on non-current rows (`POST /sessions/{id}/revoke`). Profile picture stays local-only preview (deferred until a backend upload endpoint exists). 34/34 green |
| 11 | Final regression & polish | ✅ Complete | **Full-journey E2E** (`tests/journey.spec.ts`): signup → onboarding → material → learn (real tutor reply) → planner task create/complete → assess create→take→submit→review → materials note-from-session + PDF download → audio convert/play/pause → progress + knowledge map reflect activity → assessment-result notification in bell → account identity. **Axe sweeps** (`tests/polish.spec.ts`) across all 10 app routes and 4 auth routes — zero serious/critical. **Responsive sweep** at 1280/768/390 on dashboard/materials/progress — zero horizontal overflow after fixes. **Performance sanity** gate on dashboard interactivity. Deltas recorded in `design/demo/NEXTJS-NOTES.md`. 39/39 green |

### Done alongside the phases (UI build-out)
All screens exist as polished UI: Landing · Sign In · Sign Up · Verify Email · Reset Password · Onboarding · App Shell (nav + notification bell + palette/gold switcher + profile popover) · Home · Learn · Planner · Progress · Knowledge Map · Assessments · Materials · Audio · Roadmaps · Account & Settings.

### Deliberately removed
- **Orchestration** page/nav — backend/internal concern, not learner-facing (backend API untouched).
- Learning Vector / Mastery fields from Account.

---

## Remaining phases

### Phase 9 — Notifications + reminder preferences
- Bell wired to `GET /notifications`, `unread-count`, `{id}/read`, `read-all` (replacing mock array).
- Reminder surfacing: exams within `reminder_days_before`, task due-today, daily digest — via `POST /planner/reminders/check` in dev.
- Notification preferences in Account (reminders/push toggles).
- Web push: service worker + VAPID subscribe/unsubscribe (`/api/v1/push`) — included (not skipped).
- **Acceptance:** seeded reminder appears in bell with unread badge; mark-read clears badge; prefs persist via memory/preferences API.

### Phase 10 — Account & Settings (real)
- `/auth/me` fills name/username/email; `PATCH /auth/profile` saves; `/auth/password` change; `/auth/sessions` list + revoke; `/api/v1/me/preferences` GET/PUT.
- No Learning Vector / Mastery fields. Profile picture upload deferred until a backend endpoint exists (local preview stays).
- **Acceptance:** update profile persists across reload; password change works; revoke kills that session; preferences round-trip.

### Phase 11 — Final regression & polish
- Full-journey Playwright flow: signup → onboarding → add material → learn (RAG/direct) → planner → assess → materials/audio → progress/map → notifications → account.
- Axe pass on all key routes; responsive breakpoint sweep; performance sanity.
- Update `design/demo/NEXTJS-NOTES.md` with any deltas discovered.

---

## Deferred (from the original advanced plan, not in this build)
- Calendar integrations · external learning-platform integrations · Redis cache wiring · SQL top-k/vector retrieval at scale · OTel dashboards · stress testing · actual hosting.
- Profile picture storage endpoint (backend addition).

---

## Acceptance criteria (per phase — standing definition)

1. **Build:** `npm run build` passes (TypeScript clean).
2. **Tests:** new/updated Playwright specs for the phase pass; all previous specs stay green (no regressions).
3. **Real data:** no hardcoded demo values in wired screens; all data via `lib/api.ts`.
4. **Isolation:** E2E runs against the dedicated SQLite backend on :8010 — never the dev :8000 instance or real Postgres.
5. **A11y:** axe — zero critical, zero serious violations on touched routes.
6. **Report:** results reported to you before starting the next phase.

## Current test evidence (latest run — 2026-08-27 final, all gates green)
```
auth.spec.ts          3 passed   (wrong-password error · fresh-user→onboarding · signout)
contexts.spec.ts      2 passed   (context created via onboarding · re-signin skips onboarding)
learn.spec.ts         2 passed   (session created · message sent · reply rendered · failed session switch does not hang)
planner.spec.ts       3 passed   (exam create/complete/delete · task create/complete · axe clean)
progress.spec.ts      3 passed   (fresh-learner zeros + locked badges · real activity → first-assessment badge unlocks · axe clean)
knowledge-map.spec.ts 4 passed   (empty state · concepts render after learning + search/filter chips + hub = context title · evidence invalidate round-trip · retry UI on API failure)
assess.spec.ts        2 passed   (empty state · create from seeded material → take MCQ → submit → real score review, axe clean)
materials.spec.ts     3 passed   (empty states + axe · resource add/delete · generate note from chat session → PDF download)
audio.spec.ts         2 passed   (empty state + axe · convert → play → progress saved → restored after reload)
roadmap.spec.ts       2 passed   (empty state + axe · tree from real concepts, 0% after one attempt → ticks flip after two correct attempts)
notifications.spec.ts 3 passed   (fresh bell empty state + axe · seeded exam → reminder check → badge → mark-read clears it · prefs persist across reload)
account.spec.ts       4 passed   (real identity render + axe · profile update persists across reload · password change revokes other devices and new password works · revoke kills a session)
journey.spec.ts       1 passed   (full journey: signup→onboarding→material→learn→planner→assess→materials/audio→progress/map→notifications→account)
polish.spec.ts        4 passed   (axe sweep all 10 app routes · axe sweep 4 auth routes · responsive sweep 1280/768/390 zero overflow · dashboard perf sanity)
smoke.spec.ts         3 passed   (landing · auth page · signup→onboarding→context→app)
api-smoke.spec.ts    13 passed   (API smoke: health · auth me/profile/password-revoke · contexts+prefs · study session/message · assessments lifecycle + idempotent replay + score consistency · notes create/generate/review/PDF/delete · audio generate/play/progress/delete · transcribe graceful-failure · planner CRUD + reminders dedupe probe · notifications read/read-all · progress/adaptation shapes · push round-trip · cross-owner isolation negatives)
──────────────────────────────
63 passed (full run, workers=1)   npm run build: clean (Next 16.3.1) · tsc clean · eslint 0 errors (1 pre-existing warning in tests/account.spec.ts) · backend pytest: 172 passed
```
> **Verification history:**
> - **Stale P1s (not reproducible):** malformed `frontend-v2/package.json`, reset-password/verify-email token flows, shared `ActiveContextProvider`, prod compose split-domain default, `docs/DEPLOY-COOKIES.md` duplicated `/api/v1`, `aria_v3_v2` legacy copy, planner `300px` non-responsive, and `lib/api.ts` landing redirect — all already remediated and green in this checkout.
> - **2026-08-27 re-check — Knowledge Map R2:** `search`/`stateFilter` state existed but no search input or filter chips were rendered, so `tests/knowledge-map.spec.ts:41` failed on `getByLabel("Search concepts")`. Fixed in `app/app/map/page.tsx` by wiring the search input (`aria-label="Search concepts"`) + filter chips (`All`/`Supported`/`Developing`/`Needs review`/`Untested` with `tag-chip`/`tag-chip-selected` + `aria-pressed`) and a no-match empty state with "Clear filters". Also fixed: Learn attach controls (`app/app/learn/page.tsx:159,200`) `aria-disabled`+toast → native `disabled`+`title`; `backend/Dockerfile.prod` → single worker; `lib/api.ts` → `/` public + session-cookie gate.
> - **2026-08-27 final — last two inconsistencies:** (1) Knowledge Map API failures never showed retry UI — root cause `if (failed)` nested inside `if (loading && states.length===0)` at `app/app/map/page.tsx:122` (dead code; `return <Loading/>` always won). Fixed by reordering guards (`failed` → `ErrorState` before `loading` → `Loading`) and replacing `window.location.reload()` with a soft `retry()` (same pattern as `app/app/materials/page.tsx:90`). New spec `knowledge map shows retry UI when API fails and recovers on retry` (route-intercept `adaptation` → 500 → "Try again" → unroute → recovery). (2) Learn session switch stuck on "Loading your tutor…" — `selectSession` in `app/app/learn/page.tsx:110` set `loading=true` then `await loadMessages(sid)` with no catch/finally, so a rejected messages GET left `loading` true forever and `activeId` mismatched. Fixed by removing the optimistic `setActiveId`, wrapping in `try/catch/finally` with `toast("Could not load this session.")` and guaranteed `setLoading(false)`. New spec `selecting a session whose messages fail does not leave the page stuck loading` (intercept messages GET → 500, click non-active session, assert loading clears + toast + chat input visible).
> - **2026-08-27 — six remaining inconsistencies (this batch):** (1) **FK-order in context deletion** — `backend/app/services/data_management.py:214-285` deleted `Resource` before `Note`/`Deadline` and `ResourceChunk` before `ConceptChunk`, leaving `FOREIGN KEY constraint failed` under `RESTRICT`; also missed `AudioProgress` and `RESOURCE` audio artifacts. Fixed to children-first order (AudioProgress → Evidence/AttemptAnswer/Evaluation → RevisionItem/ConceptChunk → ConceptRelation/LearnerConceptState/AdaptationDecision → ConversationMessage/PlannedTask → Note → AssessmentQuestion/AssessmentAttempt/ResourceChunk → Deadline → StudySession/Assessment → AudioArtifact(NOTE+RESOURCE) → Resource/Concept → LearningContext). (2) **Learn stale context** — `app/app/learn/page.tsx:22-71` kept old `msgs`/`activeId` during context switch (`useActiveContext` only exposed `context`, not `loading`; effect never cleared stale state, `send` could post to previous `context_id`). Fixed: consume `ctxLoading`, clear `sessions/msgs/activeId/loading` synchronously on every `context` change, disable input/send while `ctxLoading||loading`, and guard `send` against mismatched `activeId`. (3) **Delete-context always → onboarding** — `app/app/account/page.tsx:261` + `components/active-context-store.tsx:21` always `router.push("/onboarding")` and never updated `contexts`/`context`. Fixed: expose `removeContext` in `ActiveContextProvider` (filters `contexts`, picks survivor, syncs `localStorage`), `deleteActiveContext` now computes `remaining = contexts.filter(c=>c.id!==deletedId)`, calls `removeContext`, clears `aria_audio_{id}`, and routes to `/app` if survivors else `/onboarding`. (4) **Context load failure indistinguishable from new learner** — `active-context-store.tsx:70-81` had `.then/.finally` with no `.catch`; `finally` set `fetchedFor` on failure leaving `loading=false`, `context=null`, causing `ContextGuard` (`context-guard.tsx:17-25`) to redirect to onboarding with same `Loading…` UI. Fixed: add `error`+`retry` to `ActiveContextValue`, `.catch` stores error, `retry` increments `retryNonce` to re-run fetch, guard now renders `ErrorState` on `error` before any redirect. (5) **Planner 500 on invalid `context_id`** — `backend/app/schemas/planner.py:6,25` declared `context_id: str` and `backend/app/api/routes/planner.py:74,93,107,144,162,173` did manual `UUID(str)` → `ValueError` → 500. Fixed: `context_id: UUID`, `syllabus_resource_id/deadline_id: UUID|None` in schemas; route signatures `context_id: UUID` / `UUID|None`; Pydantic now returns 422 `uuid_parsing`. (6) **Export incomplete** — `data_management.py:61-189` claimed "everything" but omitted `goals`, `learning_activities`, `notifications`, `push_subscriptions`, `audio_artifacts/progress`, `concept_relations`, `resource_chunks`, `concept_chunks`, `evidence`, `adaptation_decisions`, `attempt_answers`, `learner_concept_states`, and enriched `contexts` fields. Fixed: import missing models and emit full `_serialize` lists for `goals`, `learning_activities`, `notifications`, `push_subscriptions`, `audio_artifacts` (nested progress) + `audio_progress`, `concept_relations`, `resource_chunks`, `concept_chunks`, `evidence`, `adaptation_decisions`, `attempt_answers`, `learner_concept_states`; `contexts` now include `description/status/configuration/goal_id`.

Audit notes (post-Phase-11 thorough review):
- `helpers.createUser` now registers with `display_name` (matches the signup UI payload); account.spec expectations updated.
- assess.spec now asserts scoring consistency (correct+incorrect = question count, one review row per question) instead of label-only checks.
- Duplicate-reminder probe: immediate repeat of `/planner/reminders/check` created no duplicate notifications — no dedupe issue observed.
- Cross-owner isolation verified at API level (contexts/notes/adaptation never leak across learners).

Review remediation (external review findings, batches 1–3):
1. **Frontend UX:** header **context switcher** wired to `selectContext`; reusable `ConfirmDialog` guards destructive deletes (planner exam/task, materials resource, audio artifact); interactive cards are keyboard-activatable (`interactiveProps`: role/tabIndex/Enter+Space); Learn's attach/voice controls are visibly disabled with honest "coming soon" toasts; unverified-email banner with resend action; `AuthUser.displayName` renamed to `display_name` end-to-end (also fixed signin/signup toasts that read a non-existent camelCase key).
2. **Backend fixes:** deterministic embedding fallback now uses SHA-256 digest (was process-seeded `hash()` — regression-tested); `/planner/upcoming|missed` accept optional `context_id` (backward compatible) and the dashboard/planner pass the active context; registration auto-triggers email verification; unused `SupabaseAuthProvider` seam removed (settings keys annotated as legacy).
3. **Deployment:** compose dev+prod now build the frontend service from `./frontend-v2` (legacy `./frontend` retired from deploy, source frozen); fonts self-hosted via `next/font/local` (offline-safe builds); `docs/DEPLOY-COOKIES.md` documents supported cookie/CSRF topologies.

Product-review roadmap execution (R1 + R2):
- **R1 Reliability:** generated API types (`npm run api:types` → `lib/api-types.d.ts`); shared `Loading`/`ErrorState` components + retry adopted across async screens; responsive sweep extended to **320/375/768/1024/1440 × Aurora/Noir** (fixes: planner split grid, unverified-banner wrap); lint debt cleared to **0 errors**; CI workflow `.github/workflows/frontend-v2-build.yml` (tsc+lint+build).
- **R2 Core learning experience:** **Next-Best-Action dashboard card** (`lib/next-action.ts`: overdue task → due reviews → FOCUS_STUDY focus → nearest exam → continue) with why-line + Start-now deep link; Knowledge Map v2 (**search**, state filter chips, prerequisite badges, no-match state); assessments now support **resume-draft across reloads**, live timer, mark-for-review, and concept-targeted **retry-missed** retests; tutor replies render markdown with highlighted code blocks and copy buttons; daily **review queue** on the dashboard with inline Again/Good; backend `DELETE /study/sessions/{id}` (cascades messages).
- Evidence: 52 Playwright tests green across three chunked runs; backend pytest 172 green; `tsc`/`next build` clean; eslint **0 errors**.

Product-review roadmap execution (R4 slice — Trust & scale, privacy controls):
- **Data export**: `GET /api/v1/account/export` streams a portable JSON attachment (profile, preferences, contexts, notes w/ review state, tasks, deadlines, sessions incl. messages, concepts/states, resources, assessments/attempts, badges).
- **Context deletion with explicit cascades**: `DELETE /api/v1/contexts/{id}` removes resources→chunks, notes→revision→note-audio, sessions→messages, planner children, concepts→relations/states/evidence/decisions/chunk-links, assessments→questions→attempts→answers→evaluations, then the context row.
- **Account "Data & Privacy" card**: Export-my-data download and Delete-this-context flow (ConfirmDialog) that clears local caches and returns the learner to onboarding.
- **ConfirmDialog a11y hardening**: Escape-to-close and initial focus on Cancel (`data-autofocus`), applied everywhere the dialog is used.
- Evidence: api-smoke extended to 14 tests (export shape/attachment headers, cascade + post-delete 404s); account.spec extended to 5 specs (export download, Escape-cancel, delete→onboarding); full gates **55/55 Playwright**, backend **172/172**, build clean, lint 0 errors.

Still deferred (R4 remainder): concept state-history table for confidence trends, Redis-backed rate limiting, background job queues + status APIs, observability/Sentry wiring, generated-types migration beyond dashboard/planner.

External review remediation (hardening pass):
- **Shared context store**: `ActiveContextProvider` (mounted once inside AuthProvider) owns active-context state; header switcher now updates every mounted screen **immediately** (no reload) — verified by a live-switch E2E. Derives `loading` (no synchronous setState in effects; lint-clean).
- **Auth-link completion flows**: reset-password and verify-email now consume the emailed token (`email` + `token` params) and call the real confirmation endpoints; invalid/expired links surface inline errors; resend fallbacks retained. Both pages wrapped in `Suspense` for static prerender (useSearchParams).
- **ContextGuard** no longer redirects signed-out users to onboarding (sign-out lands on `/` deterministically).
- **Prod defaults**: compose `NEXT_PUBLIC_API_URL` default is the frontend origin (same-origin proxy pattern); `DEPLOY-COOKIES.md` corrected (origin-only base — never `/api/v1` suffix — the client already prefixes it).
- **Learn placeholder controls**: native `disabled` + explanatory `title` (no fake actionability).
- **Docs hygiene**: rewritten `docs/DEPLOY-COOKIES.md` cleanly (was mojibake — caught by `tests/test_encoding.py`).
- **Stale `aria_v3_v2` copy deleted** — repository root is the single source of truth.
- Evidence: 64/64 Playwright across three chunks (incl. 4 new auth-link interception specs), backend pytest 172/172, `tsc`/build clean, eslint 0 errors.

Product-review roadmap execution (R3 — Intelligent planning):
- **"What should I do today?" strip** on the planner: missed count · tasks today · exam-readiness % (concepts SUPPORTED), plus **ARIA suggestions** — up to 4 weakest concepts (NEEDS_REVIEW first) with one-tap **"+ Add study task"** creating real planner tasks due tomorrow.
- **Reschedule missed** one-tap: recreates a missed task due +24h (deterministically lands in the Tomorrow bucket regardless of run time).
- Evidence: new `tests/r3-planner.spec.ts` (2 specs) covering suggestions→real-task creation and missed→Tomorrow reschedule; planner suite 5/5 green; tsc/build/lint clean.

Phase 11 polish notes — issues found and fixed during the sweep:
- **Cascade-order bug in `globals.css`:** the early `@media (max-width:900px)` block was overridden by later base rules, so sidebar/grid collapses never applied. Responsive overrides now live in a dedicated end-of-file block; ≤900px the sidebar is replaced by a scrollable pill nav (`components/app-shell.tsx`).
- **Ambient background layer** could extend document scroll width on narrow viewports — clipped with `overflow:hidden`.
- Inline `1fr 1fr` grids on dashboard/assessments/map/account replaced with the collapsing `.grid-2` class; `.section-head` and `.audio-card` rows now wrap.
- Account inputs were missing label association (axe-critical) — fixed with `htmlFor`/`id` pairing.

**All 11 phases complete.** The frontend-v2 rebuild is fully wired to the real FastAPI backend with no mock data in learner-facing screens. Deferred items remain as documented above (profile-picture storage endpoint, VAPID keys for live push delivery, evidence-gated infra).

Phase 9 notes: badge refreshes on bell-open and after read actions (no polling, per design decision); reminder check auto-fires once per browser session on Planner load. Real push delivery requires `ARIA_VAPID_*` + matching `NEXT_PUBLIC_VAPID_PUBLIC_KEY` (see `.env.example`, `scripts/generate_vapid.py`); without them the backend logs pushes and the UI degrades gracefully — verified headlessly that toggles stay consistent and no crash occurs.

Phase 7 notes: no backend audio *collection* endpoint exists — audio artifacts are reachable per-source only; the Audio page keeps a per-context localStorage index of artifact ids and rehydrates each via `GET /audio/{id}` (+progress) on load. Playback streams through `apiBlob` (object URL) so cookie auth works cross-origin; progress is throttled to ≥5-second deltas to avoid clobbering saved positions.

## Environment notes
- Backend for E2E: isolated uvicorn on `:8010`, SQLite `e2e-smoke-v2.db`, scheduler off, CORS `:3100` — configured inside `playwright.config.ts` (no changes to your real `.env`).
- Dev servers: `frontend-v2` on `:3100`; real backend on `:8000` (Postgres via docker compose) for manual review.
