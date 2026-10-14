# ARIA frontend enhancement plan

Status: Frontend enhancement implemented and verified; capability limits and optional follow-ups are recorded below.
Date: 5 October 2026
Target: `frontend-v2`, the canonical learner frontend.

## 1. Intended experience

Make ARIA feel like a living learning universe: connected concepts, a responsive assistant, and fluid movement from a goal into a study session. The everyday workspace should remain comfortable for long reading sessions. More expressive moments belong on the landing page, when exploring knowledge, and when completing meaningful milestones.

Guiding principle: **When you learn something, your universe visibly grows.**

The design direction is a **celestial learning studio**: layered surfaces, fine constellation lines, generous spacing, clear typography, and controlled light from the current palette. Light mode receives an equally considered treatment with soft surfaces and crisp contrast.

Success means that learners can immediately identify their next action, understand changes through motion, and enjoy a few memorable interactions without waiting for animation to finish.

## 2. Current foundation and scope

- `frontend-v2` includes Anime.js and Motion. Ambient canvas flow uses Anime.js; React layout and presence transitions use Motion. Large continuously animated blur layers were removed after profiling.
- The landing page has a wordmark, rotating captions, and capability cards. The dashboard already contains learner progress and next-action data.
- `components/app-shell.tsx` provides the shared workspace shell; this is the natural place for navigation polish.
- The map page already loads concept states, evidence, and prerequisites. A richer graph can build on those data sources, subject to a performance audit.
- `docs/theme-system.md` establishes dark and light parity, semantic color tokens, accessible focus states, and restrained effects. This proposal extends that foundation. Any revised visual rules should be recorded there during implementation.

Initial work is frontend focused. Backend additions are separate decisions where a proposed interaction requires data the current APIs do not expose.

## 3. Experience rules

1. Every significant animation should explain entry, selection, progress, or completion.
2. Give each screen one main visual focal point. Reading areas receive stable, opaque surfaces.
3. Preserve context during transitions: keep the shell visible and carry titles or selection indicators between states where practical.
4. Let users interact immediately; decorative sequences must not delay navigation or input.
5. Match motion to context: expressive on the landing page, responsive on the dashboard, quiet during study, brief at milestones.
6. Provide equivalent keyboard, touch, light-theme, and reduced-motion experiences.

## 4. Priority and sequence

| Phase | Scope | Reviewable result | Exit condition |
|---|---|---|---|
| 0 | Audit and design prototype | Motion inventory, screen baselines, and a dashboard/map visual prototype | Direction and scope are clear before broad changes |
| 1 | Shared visual and motion foundation | Reusable motion settings, surfaces, buttons, loading states, and reduced-motion handling | Components behave consistently in both themes and on mobile |
| 2 | Shell and dashboard | Fluid navigation, stronger next-action hierarchy, and animated progress | Everyday navigation and dashboard are polished and usable |
| 3 | Knowledge map | Interactive concept constellation grounded in actual learner data | Selection, filtering, and prerequisite exploration remain accessible and fast |
| 4 | Study, materials, and roadmaps | Focus mode, assistant states, meaningful processing feedback, and roadmap progression | Core learning workflows feel connected without interrupting reading |
| 5 | Landing page and milestones | Interactive product story and restrained achievement moments | Public introduction reflects the real product and celebrations reflect real events |
| 6 | Verification and refinement | Responsive, accessibility, lifecycle, and performance fixes | Defined checks pass and remaining limitations are documented |

Recommended first implementation release: **Phases 0–2**. Add Phase 3 as the next release to introduce ARIA's signature visual. Each phase should be independently usable and reviewable.

## 5. Proposed screen changes

### Shell and navigation — highest priority

- Animate the active navigation indicator between items.
- Use a short fade and slight positional change for newly loaded page content while keeping the shell stable.
- Animate drawers and menus with consistent entrance, exit, and focus behavior.
- Avoid replaying the full entrance sequence after small data updates.
- Prototype a card-to-workspace expansion for “Continue learning.” Use a simple transition if a cross-route shared element proves fragile with the installed Next.js version.

### Dashboard — highest priority

- Make “Continue learning” the dominant card, with the current topic, next step, and clear action.
- Arrange secondary tools and progress summaries with varied visual weight and adequate breathing room.
- Reveal major sections in a short stagger on initial entry.
- Animate progress indicators once when meaningful data arrives. Keep values legible throughout.
- Add subtle hover lift and press feedback; pointer effects apply only on suitable devices.
- Show loading placeholders that preserve the final layout, then transition into content.

### Knowledge map — signature feature

- Position concepts in a stable graph and draw genuine prerequisite connections.
- Use color, shape or icon, and text labels together to communicate existing concept states.
- Highlight the selected concept and its immediate connections; present evidence and suggested actions in a detail panel.
- Support search, state filters, zoom controls, keyboard selection, and a readable list alternative.
- Introduce connections with one short drawing sequence; stop continuous node pulsing after attention is established.
- Use deterministic placement so refetching does not randomly rearrange the learner's map.
- Begin with SVG for a bounded graph. Decide on larger-graph rendering only after measuring realistic concept counts.
- Audit the current per-concept prerequisite requests before expanding the graph; a batch API may be a separately scoped improvement.

### Study and assistant

- Add an abstract ARIA mark with truthful idle, pending, responding, and error states based on actual application state.
- Reveal newly added messages gently. Keep existing messages and the reading position stable.
- Do not repeatedly animate streamed text or force scrolling when the learner is reading earlier messages.
- Add an optional focus mode that reduces surrounding visual activity and emphasizes the lesson.
- Provide a session recap using existing data where available. Scope any new tracking separately.

### Materials and roadmaps

- Show upload and processing stages only when supported by actual state. Use indeterminate feedback when detailed stages are unavailable.
- Reveal extracted concepts as cards when results arrive, with an optional transition into the map.
- Draw roadmap segments toward the current step; distinguish completed, current, and upcoming steps clearly.
- Celebrate a newly completed step briefly and once, with a stable final state.

### Landing page and milestones

- Create a short constellation-to-wordmark introduction that can be skipped through immediate interaction.
- Add an interactive walkthrough: choose a sample topic, then explore its roadmap, example conversation, and concept map.
- Clearly label sample content and keep the signup action prominent.
- Keep scroll reveals gentle and retain native scrolling.
- Animate genuine achievements once. An exportable achievement card is an optional later enhancement with accurate completion data.

## 6. Animation architecture

| Tool | Responsibility |
|---|---|
| Anime.js | SVG drawing, coordinated introduction sequences, and brief milestone choreography |
| Motion | React component entrances/exits, layout changes, selection indicators, drawers, and gestures |
| CSS | Hover, focus, press, border, color, and simple opacity transitions |

Give each animated property one owner. If a card needs both layout movement and an Anime.js illustration, use separate wrapper and illustration elements.

Create a small reusable layer for motion tokens, section reveals, presence transitions, progress indicators, and the assistant mark. Avoid converting every element into an animated component.

Use scoped Anime.js instances with cleanup. Ensure unmounting, rapid navigation, development remounts, and theme changes do not leave duplicate timelines, listeners, or animation loops. Check installed Next.js guides before implementation.

Prefer transform and opacity for repeated movement. Limit large blur effects, animated shadows, and simultaneous background layers. Lazy-load optional showcase visuals where useful. Pause ambient work when hidden or offscreen.

Reduced motion must cover JavaScript timelines, pointer parallax, canvas loops, and CSS. Retain immediate state feedback through static changes or modest fades.

## 7. Starting motion specification

These are initial design targets, to be adjusted after visual review.

| Interaction | Initial duration | Behavior |
|---|---|---|
| Button press / hover | 120–180 ms | Small displacement or surface change |
| Tabs / menus / drawers | 180–300 ms | Smooth settling with limited overshoot |
| Page content entry | 220–350 ms | Fade with 8–16 px movement |
| Section stagger | 35–60 ms between items | Cap total delay; show important content first |
| Progress update | 400–700 ms | Ease toward the actual value |
| Signature introduction | 600–900 ms | One coordinated sequence |
| Milestone feedback | Under 1.2 seconds | Brief accent, then a stable result |

Use gentle springs for spatial movement and restrained easing for opacity. Ambient movement should be slow, sparse, and largely absent behind dense study content.

## 8. Verification and acceptance criteria

- Validate dashboard, navigation, map selection, study messages, and materials states at representative phone, tablet, and desktop widths.
- Check all existing palettes in dark and light appearances; preserve contrast, visible focus, and readable surfaces.
- Verify keyboard access, menu focus management, reduced motion, and the map's list alternative.
- Exercise slow requests, errors, empty states, rapid route changes, repeated theme changes, and component unmounting.
- Check that streaming chat preserves deliberate user scrolling and does not animate entire histories.
- Run the frontend's typecheck and lint, then relevant existing Playwright and accessibility checks. Add targeted coverage for new behavioral risks rather than testing decorative timing.
- Compare performance with Phase 0 baselines on a representative mobile viewport and a throttled browser. Investigate animation-related long tasks, visible stutter, layout shifts, and resource growth after repeated navigation.
- Aim for smooth movement on the selected test devices; simplify effects if measurements show they impair interaction.
- Confirm animations do not imply invented processing stages, prerequisite links, mastery, or achievements.

## 9. Optional enhancements after the main release

- Palette-change color wash, provided it preserves contrast and reduced-motion behavior.
- Planner drag-and-drop with smooth reordering, keyboard alternatives, and reliable persistence; scope this as functional work.
- Saved achievement images with a reviewed export design.
- Richer personal-universe overview across subjects, if the available data supports it.

Large 3D scenes, sound effects, and a custom cursor are outside the initial release. Their value should be assessed after the main experience is polished.

## 10. Decisions for review

Suggested defaults:

- Visual direction: celestial learning studio, retaining current palette choices and typography.
- First release: shared foundation, shell, and dashboard.
- Signature feature: concept constellation with genuine prerequisite links.
- Study behavior: calm focus mode and minimal ambient movement.
- Technology: existing Anime.js + Motion + CSS; add dependencies only for a demonstrated need.
- Review cadence: a working preview after each phase, with findings and adjustments recorded here.

To begin later, ask: **“Implement Phases 0–2 of the frontend magic plan, and give me a working preview before proceeding to the knowledge map.”**

## 11. Implementation log — 5 October 2026

The initial implementation now includes:

- Shared Motion configuration, live reduced-motion preferences, section reveals, and animated concept progress rings.
- Persistent desktop navigation with a sliding selection surface, route content entry, and improved popover keyboard focus and dismissal.
- A redesigned dashboard with a dominant Continue Learning card, direct tool links, a recommendation, and a retryable progress state. Switching contexts resets dashboard data.
- A selectable concept constellation with genuine prerequisite edges, stable placement across filters, zoom, a list alternative, and evidence details. Graph rendering uses stable groups of up to 60 concepts with previous/next controls; search reveals matching concepts outside the first group, and empty groups are skipped under filters. The list includes every visible concept. Only connections within the displayed group are drawn, with all recorded prerequisites retained in details. Prerequisite fetching is bounded to six concurrent requests and unavailable data stays explicitly unknown.
- Assistant presence driven by request state, focus mode, new-message entry, and scroll preservation with Jump to latest. Loaded conversation history is not animated as new messages.
- A roadmap milestone trail, real topic selection, and brief completion feedback that compares completion snapshots within the browser session.
- Indeterminate materials processing feedback tied to the request, resource entry, and a link from ready resources to the map. The API does not expose detailed extraction stages, so those stages are not simulated.
- A finite Anime.js constellation wordmark and an interactive, clearly labeled landing sample with topic and stage controls.
- Ambient timeline cancellation on cleanup, live reduced-motion handling, hidden-page handling, and static backgrounds during study and assessment.
- Improved Noir secondary-text contrast and mobile navigation contrast.
- Simplified onboarding language to topic, familiarity, and an explicitly optional goal. Native form submission supports Enter; invalid topics return focus to the field, and setup disables inputs and guards duplicate requests. The existing palettes remain in place; the proposed Midnight Observatory direction is still a design suggestion.

Verification is recorded through `frontend-v2/tests/frontend-motion.spec.ts` with `frontend-v2/ui.config.ts`. These tests use explicit network fixtures; they do not prove backend integration. The default integration runner remains separate.

### Remaining verification and refinement

- Mobile profiling at 390×844 and 4× CPU throttling found expensive ambient motion: 95th-percentile frame gaps were 66.8 ms with 13 long tasks in a 1.8-second sample. Small screens now use static gradient depth, a smaller constellation, capped canvas resolution, and no large animated blur layers or pointer parallax. The repeat sample measured 16.8 ms frame gaps and zero long tasks. After five navigation cycles, DOM nodes stayed at 700 and listeners at 671; post-GC heap rose about 1.48 MB, which needs a longer trend check before drawing a memory-leak conclusion.
- Desktop profiling at 1440×900 found 283.4 ms frame gaps and eight long tasks under 4× CPU throttling. Workspace pages retain static gradient depth and the animated constellation without large continuously animated blur layers or pointer parallax. The first repeat measured 33.4 ms frame gaps with zero long tasks; reduced motion measured 16.7 ms. DOM nodes stayed at 701 and listeners at 671 after five navigation cycles, with post-GC heap up about 1.45 MB. The subsequent landing optimization also reduced workspace particle density; these earlier desktop measurements predate that additional reduction.
- Landing profiling initially measured 333.4 ms frame gaps and seven long tasks. Steady layered gradients replaced the large rotating blur surfaces, and particle density/connection calculations were reduced. The repeat measured 16.8 ms frame gaps with zero long tasks under 4× CPU throttling. The finite Anime.js wordmark and interactive sample remain. After five preview-interaction cycles, listeners stayed at 631, nodes changed from 651 to 652, and post-GC heap rose about 0.46 MB. Reports are saved in `screenshots/frontend-magic/animation-profile*.json`. These are development/fixture measurements, not production guarantees or a historical pre-enhancement baseline.
- Progress errors, delayed materials context switches, and milestone updates have targeted browser coverage. Milestone feedback now survives development effect restarts, clears on schedule after live reduced-motion changes, and does not replay after reload.
- Tutor conversation loads and replies now check a conversation version before updating the visible chat; switching subjects remounts the tutor workspace. Session switches reset pending assistant state and drafts, stop recording, and prevent late attachment/transcription callbacks from entering another conversation. Delayed-reply isolation and existing reading-position/focus behavior have browser coverage; microphone hardware and live transcription still require integration verification.
- Real-backend checks now run using the isolated Python environment and independent local servers; broader final integration verification is ongoing.
- The mobile selection indicator now slides between routes using a separate Motion layout group. Notification and profile menus use Motion entrance and exit transitions; closing menus become inert immediately, and focus moves to the newly opened menu or returns to the trigger on Escape. Responsive, reduced-motion, route-selection, and menu-switching browser checks pass. A 72-concept browser fixture verifies group navigation, searching beyond the first 60, stable filtered positions, and the complete list alternative. Larger-scale request batching remains a separately scoped API improvement.
- Resource responses expose status and chunk counts, and the chunks endpoint exposes processed text, but no resource-to-concept association. A confirmed extracted-concept reveal requires additional API support; do not infer those associations from context-wide concept lists. The current processing feedback and map link remain in place.
- Materials now remount their workspace on context changes, preventing delayed previous-subject results from replacing the new subject's materials or retaining an upload dialog from another subject.
- Decide whether broader progress achievements need additional celebration work after reviewing this first implementation.

### Verified first-pass results

- Production build passed, including TypeScript checking and prerendering all 19 pages.
- A fresh production build after the map, tutor, onboarding, ambient-performance, and integration refinements passed again, including TypeScript and all 19 prerendered pages. It used `.next-verification` to preserve the running previews.
- Separate typecheck passed. Scoped lint passed for all enhancement files; whole-project lint findings are listed below.
- All 14 behavioral and accessibility browser checks passed together after navigation, onboarding, milestone, materials, and tutor refinements. They cover dashboard palette accessibility, map keyboard selection and filtering, chat scroll preservation and focus, landing sample controls, materials processing and context switching, roadmap selection and one-time completion feedback, keyboard onboarding, delayed tutor replies, retryable progress failure, live reduced motion, and throttled navigation. After the mobile ambient optimization, the responsive/reduced-motion check and new profiling check passed again. The suite now contains 15 checks.
- The enhanced learning screens passed serious/critical Axe checks in Aurora, Noir, and Noir gold, with overflow checks at 320, 375, 768, 1024, and 1440 pixels.
- Desktop screenshots were inspected. A tutor back-button overlap found during review was corrected; chat behavior and the full learning-screen palette/width sweep passed again afterward.
- Saved screenshot previews live in `screenshots/frontend-magic/`. They use controlled test fixtures and are not evidence of live learner data or backend integration.

### Environment findings

The existing `.venv` references a Microsoft Store Python 3.11 executable that is unavailable on this host. The bundled Python 3.12 runtime starts, but it does not contain SQLAlchemy or the backend dependency set. Frontend browser checks therefore run independently using explicit network fixtures.

A separate ignored environment at `venv/frontend-integration` now contains the declared `requirements-dev.txt` dependency set using the working Python 3.12 runtime. Installation completed successfully, core imports passed, and `pip check` reports no broken requirements. The backend starts successfully and returns a healthy response on port 8010. The integration frontend uses `.next-playwright` through `ARIA_NEXT_DIST_DIR`, so its server can run alongside the preview without sharing Next's output directory. Existing onboarding integration selectors have been updated for the new questions and Start learning button; configuration/selector typecheck and scoped lint pass.

The current 18-check frontend fixture suite passed together after the map/background refinements. The first real-backend smoke run exposed low contrast in landing preview-step numbers and an obsolete greeting assertion. Step numbers now use full opacity, and the context-switch test checks the actual subject in Continue Learning. The rerun reports passing outcomes for all seven cases in `smoke.spec.ts`, `contexts.spec.ts`, and `chat-reload.spec.ts`: landing/sign-in/dashboard accessibility, real context creation, returning sign-in, no-reload context switching, and persisted tutor replies. Landing reports zero accessibility violations. The Windows runner remains in server cleanup after reporting those outcomes; broader materials, roadmap, and map integration checks remain open.

The targeted real-backend roadmap checks now pass with a clean runner exit. The test verifies that a requested Functions concept reaches Supported and the matching milestone visibly completes. This exposed a deterministic quiz targeting bug: filtering chunks by a requested concept still assigned questions to an unrestricted dominant concept in the same chunk. The generator now restricts evidence attribution to the requested linked concepts. All 15 backend assessment tests pass, including a regression with a more frequent competing concept; scoped Ruff checks pass.

Real-backend map checks also exposed a missing active-subject label after the constellation redesign; the map now identifies its actual subject beneath the heading. Materials tests explicitly select Paste Text and confirm resource deletion rather than swallowing deletion failures. All nine combined materials/map/roadmap checks passed with a clean runner exit: real concepts and evidence, evidence invalidation, retry recovery, empty states, text-resource creation/deletion, note PDF download, and mastery-driven milestone completion.

For independently running integration servers on frontend port 3100 and backend port 8010, `ARIA_INTEGRATION_EXTERNAL_SERVER=1` skips Playwright-owned server startup and avoids the observed Windows server-cleanup hang. `tests/run_integration_backend.py` configures the isolated local database and deterministic providers before starting the backend.

Whole-project source lint now passes. Palette hydration uses a browser-storage subscription with an SSR snapshot rather than synchronous effect-driven state updates; theme changes also follow storage events from other tabs. The learning-agent voice mocks use explicit browser event/stream types and remove an unused import. Typecheck and the dashboard palette/accessibility plus mobile/live reduced-motion checks passed after these changes.

For an independently running frontend at port 3101, use:

```powershell
$env:ARIA_UI_EXTERNAL_SERVER = '1'
npx playwright test --config ui.config.ts
```

Without that environment variable, the UI test configuration starts its own frontend server. The normal integration tests remain under `playwright.config.ts`.

### Completion audit checkpoint

| Requirement | Current evidence | Remaining scope |
|---|---|---|
| Shared motion, shell, dashboard hierarchy | Motion configuration, persistent shell, dominant Continue Learning, actual progress; responsive and keyboard browser checks. Progress rings fill on first appearance and update toward actual values; reduced motion is immediate | No remaining core behavior identified |
| Knowledge constellation | Genuine prerequisite fixtures and real concept/evidence integration; 72-concept group/search/list checks | Larger graph batch API is separate work |
| Study and assistant | Request-driven orb, focus mode, session counts, reading-position and delayed-reply isolation checks; persisted real-backend chat | Live microphone/transcription hardware review |
| Materials and roadmaps | Nine real-backend checks pass; indeterminate processing, actual resource deletion, PDF download, actual mastery-driven milestone | Extracted-concept reveal needs resource association API; current UI does not invent it |
| Landing and milestone story | Finite wordmark, labeled interactive sample, actual roadmap completion feedback with once-per-session behavior | Broader badge celebrations need a separate product decision |
| Light/dark and accessibility | Aurora is light; Noir and Noir gold are dark. Palette/width sweep, reduced-motion/menu checks, cross-tab persistence and blocked writes pass; whole-project source lint passes | No remaining enhancement gate |
| Production readiness and animation lifecycle | Final production build and all 20 checks pass; bounded ambient work and production profiles inspected | Measured heap retention is documented; no universal leak-free claim |

The longer mobile profile passed with 20 dashboard/map navigation cycles. Under 4× CPU throttling, the animated sample measured 16.8 ms 95th-percentile frame gaps, no gaps over 32 ms, and zero long tasks. Nodes stayed at 700 and listeners at 669 throughout. Post-GC heap increased from 11.65 MB to 13.93 MB; checkpoints at cycles 5/10/15/20 were 13.14/13.43/13.74/13.93 MB. This does not establish a leak-free result: retained development/runtime memory still needs investigation or comparison against the production runtime. The report is saved as `screenshots/frontend-magic/animation-profile-mobile-20-cycles.json`. Scoped lint for the expanded profiling test passed.

The Midnight Observatory theme remains a proposal. Existing palettes are retained pending a reviewed visual direction.

The same 20-cycle mobile profile also passed against the optimized production build on port 3102: 16.7 ms frame gaps, zero long tasks, nodes fixed at 393, listeners fixed at 365. Post-GC heap rose from 5.99 MB to 7.39 MB; cycle checkpoints were 6.96/7.22/7.29/7.39 MB, showing smaller and slowing retention compared with development. This is evidence against accumulating DOM/listener resources over the measured run, not proof that all retained memory is harmless. The saved production report is `screenshots/frontend-magic/animation-profile-mobile-production-20-cycles.json`; its original generic note says development, but the run used `next start` with `.next-verification` on port 3102. The profiling harness now supports an explicit `ARIA_UI_RUNTIME` label and `ARIA_UI_BASE_URL` for future production comparisons. ESLint ignores the isolated generated build directories, avoiding noisy generated-code scans.

Dashboard progress rings now start from an empty stroke on their first client appearance when motion is allowed, then ease to the actual supported percentage. Previously `initial={false}` skipped that first fill. Reduced-motion users receive the actual stroke immediately, and displayed values remain truthful throughout. The dashboard palette/accessibility, mobile/live reduced-motion, and throttled navigation checks passed again (three checks).

The final 20-check development suite reported 19 passes and one large-map readiness failure while a production build ran concurrently. Both new palette checks passed: persisted selection follows another tab, and blocked writes retain working in-memory palette/gold controls. The failure exposed that concept rendering waited for all per-concept prerequisite requests. The map now publishes confirmed concept and evidence data immediately, shows an explicit connection-loading status, and adds only confirmed edges when the bounded prerequisite requests finish. The large-map regression deliberately holds those requests while verifying concept exploration is available. Both map checks passed after the correction. A subsequent development run passed the map but hit a five-second dashboard progress wait; this was not reproduced in the final production run.

### Final acceptance evidence

- The final `next build` with `.next-verification` passed after the map and palette changes, including TypeScript and all 19 generated pages.
- Full-source ESLint passed again after the final test-harness changes. The preview on port 3101 returned HTTP 200 at handoff.
- All 20 enhancement checks passed together against that optimized build on port 3102 (3.6 minutes), with `ARIA_UI_RUNTIME=production`. This includes all palettes and responsive widths, keyboard navigation, map groups and delayed connections, chat isolation and reading position, onboarding, processing feedback, milestone behavior, retry states, cross-tab palette persistence, blocked storage writes, and profiling.
- All four real-backend map checks passed after the loading change. The earlier nine materials/map/roadmap checks and 15 backend assessment tests also passed. Seven smoke/context/chat cases previously reported passing outcomes; their original Windows server-cleanup limitation is preserved above rather than represented as a clean command exit.
- Final production profiles measured 16.8 ms frame gaps on mobile/desktop and 33.4 ms on landing under 4× CPU throttling, with zero long tasks on every surface. Workspace nodes/listeners stayed constant; landing nodes changed from 272 to 276 and listeners remained 328. Forced-GC heap retention remains documented rather than claimed absent.
- Final reports are saved as `screenshots/frontend-magic/animation-profile-production-final-*.json`; reviewed production dashboard/map screenshots use the `production-final-` prefix. Screenshots and most UI tests use explicit network fixtures; real-backend results are identified separately.

The phase exit conditions are satisfied for the frontend implementation using currently available data. The existing palette choices remain; Midnight Observatory is a proposal. Resource-specific extracted-concept cards require a separately scoped association API. Batch graph APIs, broader badge celebrations, export cards, planner reordering, cross-subject universes, and real microphone hardware validation remain separate follow-ups. No deployment, commit, or pull request is part of this request.
