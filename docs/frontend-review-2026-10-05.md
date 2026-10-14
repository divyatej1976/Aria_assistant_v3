# ARIA frontend review — 5 October 2026

## Scope and evidence

Reviewed the current `frontend-v2` working tree, its shared components, all learner-screen source files, authentication/API helpers, backend contracts relevant to those screens, configuration, and test coverage. This review includes browser probes on the preview at port 3101 and 21 real-backend integration cases using the isolated backend at port 8010 and frontend at port 3100. Application code was not changed as part of this review.

Current typecheck and full-source ESLint passed. The new integration run reported **19 passes and 2 failures**. Correct sign-in reached onboarding; that failure is an obsolete heading selector, not a failed login. Audio generation returned a FAILED artifact, so audio playback/resume could not be verified by that test. The local speech engine reported COM access denied. This is an environment-specific provider failure, not evidence that every production TTS provider fails.

Earlier final enhancement verification passed 20 browser checks against an optimized production build, as recorded in `docs/frontend-magic-plan.md`. Those checks cover the enhanced visual/interaction layer, but do not cover every failure reported here. In particular, passing automated accessibility checks does not prove correct modal focus behavior or real microphone availability. This review is not a production deployment, penetration test, live-cloud-provider validation, or exhaustive device/browser certification.

## 1. Problems and inconsistencies

Priority: P1 = fix before relying on the affected workflow; P2 = important correctness/usability improvement; P3 = polish or documentation drift. “Browser confirmed” and “integration confirmed” describe observations; “source confirmed” identifies a concrete code path that was inspected but not exercised end to end.

### R1 — P1: The microphone feature is blocked by the frontend's own policy

**Evidence:** `frontend-v2/next.config.ts:26`; voice capture in `frontend-v2/app/app/learn/page.tsx:217`. Browser confirmed: `document.featurePolicy.allowsFeature('microphone')` returned false on the served page.

The application offers Speak question and calls `getUserMedia`, while the response header sets `microphone=()`. This prevents voice capture even when the browser and hardware support it. Mocking getUserMedia in a test bypasses this real policy restriction.

**Recommendation:** allow the microphone for the application origin, retain the other permission restrictions, and test the actual served policy. Then validate permission denial, recording, transcription failure, and stream cleanup with real hardware separately.

### R2 — P1: Subject switches can show and operate on the previous subject's data

**Evidence:** `frontend-v2/app/app/planner/page.tsx:75`, particularly `setTasks(t)` at line 83. Browser confirmed with delayed responses: switch from subject A to B, observe B's task, then release A's response; A's task replaces it while the active-context selector still says B.

The effect's cancelled flag guards errors/finalization, but the load function itself updates state without a request/context guard. An old response can therefore overwrite current data. A learner could complete or delete the wrong subject's task while trusting the current header.

Related source risks exist in Audio, Assessments, and Roadmaps. The assessment screen also retains its active attempt and review state when the context changes; follow-up adaptation/retest calls use the current context rather than a captured attempt context. Dashboard, Materials, Learn, and Map have stronger context isolation, making behavior inconsistent across the product.

**Recommendation:** apply one subject-isolation pattern everywhere: context-keyed workspaces or request versions plus cancellation inside data loaders. Define what happens when a learner switches subjects during an assessment; retain a correctly scoped draft or ask them to leave the attempt explicitly. Add delayed-response and mid-attempt context-switch coverage.

### R3 — P1: Failed audio generation is announced as success

**Evidence:** `frontend-v2/app/app/audio/page.tsx:119–140`; backend generation returns a FAILED artifact in `backend/app/services/audio.py:222`. Integration confirmed: the artifact displayed `FAILED · 0:07`, while the frontend success path unconditionally calls `toast('Audio ready.')`.

HTTP success means the artifact record was returned, not that synthesis succeeded. The client also invents a duration from text length when duration is absent, including for failed generation, and offers playback without checking READY.

The observed local cause was `LocalTTSProvider` COM access denied. The UI bug remains applicable to any provider/storage failure that produces a FAILED artifact.

**Recommendation:** branch on artifact status. Show ready/play controls only for READY, processing feedback only for actual processing, and a readable failure/retry state for FAILED. Keep unknown duration unknown, or explicitly label an estimate. Check provider readiness independently of HTTP/database health.

### R4 — P1: Failed sign-out can appear successful while the session remains valid

**Evidence:** `frontend-v2/components/auth-provider.tsx:46–52`, `frontend-v2/components/app-shell.tsx:340`, and the cookie-revoking backend sign-out route.

Source confirmed: signout catches every request failure, clears the in-memory user, and resolves successfully. The shell then navigates home. If the backend did not receive/revoke the session, the HttpOnly session cookie remains valid and refreshing can restore authentication. The ordinary successful sign-out integration case passes; the failure path is not covered.

**Recommendation:** distinguish successful server logout from an interrupted request. Do not claim the session was revoked when it was not. Offer retry or an explicit offline/local-only outcome, and cover network failure plus subsequent refresh.

### R5 — P2: Anonymous visitors can enter workspace routes and get stuck loading

**Evidence:** `frontend-v2/components/context-guard.tsx:21,38`; Audio's effect returns immediately without a context. Browser confirmed: an anonymous visit to `/app/audio` remained on that URL with the workspace shell and “your audio studio…” loading content.

This is a route-state problem, not a demonstrated bypass of backend authorization. The guard handles authenticated users without a subject but deliberately does nothing for unauthenticated visitors. Several screens require a context to finish loading.

**Recommendation:** once authentication resolves, send unauthenticated workspace visitors to sign-in with a return destination. Preserve a real authentication/network-error state instead of treating every failure to load the current user as ordinary anonymous access.

### R6 — P2: Overlapping toasts leak notifications and repeating timers

**Evidence:** `frontend-v2/lib/toast.ts:31–35`. Browser confirmed: emit two toasts, wait three seconds; the first toast remains after the second disappears.

The interval returns whenever its captured id is not the latest global counter. Older intervals then neither remove their toast nor clear themselves. They keep waking for the lifetime of the page. Every toast also uses a success icon, including failure messages, and the container lacks a live-region announcement.

**Recommendation:** give each toast its own finite timeout and lifecycle, independent of newer toasts. Support success/error/info semantics and accessible announcements. Test overlapping messages, not just one toast at a time.

### R7 — P2: Dialog and popover keyboard behavior is inconsistent

**Evidence:** `frontend-v2/components/confirm.tsx:22–30`; modal markup in Materials, Planner, Audio, and Assessments. Browser confirmed: Tab escapes an open confirmation dialog.

The confirmation component focuses Cancel and handles Escape, but has no focus trap, background inertness, or explicit focus restoration. Several create dialogs are plain divs without dialog semantics. Palette settings also has less complete dismissal/focus handling than the upgraded notification/profile popovers.

**Recommendation:** reuse an accessible dialog primitive across all modals. Trap focus while open, restore the trigger, label the dialog, and handle Escape/backdrop consistently. Use the same popover interaction rules for palette settings.

### R8 — P2: Loaded fonts are not being applied through the shared tokens

**Evidence:** `frontend-v2/app/globals.css:252–253`, `frontend-v2/app/layout.tsx:34`. Browser confirmed: the body's local-font variable contains Jakarta, but root `--font-sans` resolves empty; body and concept nodes use the system font stack.

Font aliases are defined on the root, while their dependent local-font variables are defined on the body. Root variables cannot resolve values supplied only by a descendant. Font files can load successfully without the shared token actually applying them.

**Recommendation:** put font variables on the same element as the aliases, or define aliases where the local-font variables exist. Verify computed fonts on headings, form controls, buttons, graph nodes, and code blocks. This is a concrete typography inconsistency, not just a preference for another typeface.

### R9 — P2: Roadmap request failures masquerade as an empty account

**Evidence:** `frontend-v2/app/app/roadmaps/page.tsx:92–93,147–148,156–163`.

Source confirmed: both detail and list loaders catch errors and set the roadmap to null. The outer catch cannot set the page's failure state because these loaders swallow the error. A network/server failure can therefore show “No roadmap yet.” Detail requests also lack protection against out-of-order goal selection responses.

**Recommendation:** separate loading, genuinely empty, failed, and ready states. Propagate failures or return an explicit result; protect detail selection with a request version. Retain useful loaded data during a recoverable refresh error.

### R10 — P2: Storage failure handling is not consistent across features

**Evidence:** `frontend-v2/components/active-context-store.tsx:82,115,123`; `frontend-v2/app/app/assess/page.tsx:75–77,117`.

Source confirmed: palette controls handle blocked writes, but context selection/creation and assessment drafts call localStorage without comparable protection. Creating a subject can succeed on the server, then throw while saving the active id, causing onboarding to report failure despite the new subject existing. An assessment draft write can throw from an effect. Drafts use one global key rather than a learner/context namespace.

**Recommendation:** make local persistence optional and guarded. Scope drafts to learner/context/attempt, validate restored payloads, and clear them according to an explicit logout/account-switch policy. Never let a storage write reverse the UI's interpretation of a successful server mutation.

### R11 — P2: Audio object URLs are never released

**Evidence:** `frontend-v2/app/app/audio/page.tsx:160,180–190`; no `revokeObjectURL` call in that screen.

Source confirmed: each played artifact creates a blob URL retained in state. Deleting audio or leaving the page does not revoke the URL. This retains audio buffers for long sessions. The earlier dashboard/map memory profiles do not cover audio buffers.

**Recommendation:** revoke URLs on deletion, replacement, and unmount; track URL ownership independently of render state. Preserve and save playback position when changing tracks or leaving the subject.

### R12 — P2: Profile-photo changes are temporary but look like account settings

**Evidence:** `frontend-v2/app/app/account/page.tsx:84,153–156,366`.

Source confirmed: a FileReader updates local component state only. The profile save request includes name and email, not a photo; the picture disappears after reload/navigation. The rest of the account profile does persist, so this is inconsistent behavior within one form.

**Recommendation:** implement persistence with validation and size limits, or clearly label this as a temporary preview/remove the upload affordance until supported.

### R13 — P2: Configuration and tests contain misleading drift

- Account offers two hard-coded model options (`account/page.tsx:19`), while backend configuration allows more (`backend/app/core/config.py:27`). A saved model outside those options cannot be represented faithfully by the select.
- `tests/auth.spec.ts:28` expects an “onboarding” heading that was renamed; the current flow reaches the correct onboarding URL. Update the assertion to the user-visible heading.
- `tests/learning-agent-features.spec.ts:4` writes screenshots to a developer-specific absolute directory outside this workspace. Use Playwright's output paths.
- Microphone tests replace getUserMedia/MediaRecorder, so they can pass despite the real permissions policy blocking capture. Add a policy/capability check rather than interpreting a mocked transcription path as proof of working voice.
- Frontend defaults to API port 8000; default backend CORS only permits frontend port 3000. The current port-3101 preview works because the backend was started with explicit overrides. The earlier network error was a missing backend, not an invalid account. A repeatable local startup/readiness check is still needed.

**Recommendation:** centralize capability/model configuration, make test artifacts portable, and document one reliable startup command. Treat API reachability, database readiness, and provider readiness as different checks.

### R14 — P3: Theme and product copy do not always match the implemented behavior

- Theme documentation calls dark mode the default, while layout/provider default to light Aurora. Decide which rule is current and align both.
- Palette accessibility text says “Midnight Aurora” although Aurora declares `color-scheme: light`.
- Landing promises a 52-week heatmap (`app/page.tsx:16`); backend uses 182 days (`backend/app/services/progress.py:36`), and progress fallback copy says 26 weeks.
- Roadmap empty-state copy uses implementation language such as “isolated curriculum tree.” Learners would benefit from a plain explanation of what they can do next.

**Recommendation:** audit product claims, labels, defaults, and empty-state wording against the actual contracts. These should be corrected rather than solved with extra animation.

## 2. Overall opinion and betterments

The new frontend is a substantial visual foundation. The dashboard has a clear primary action, semantic palettes make the light/dark treatments related, and the concept constellation gives ARIA a distinctive learning-centered visual identity. Focus mode and restrained motion during reading are good choices. Onboarding asks a reasonable minimum: topic, starting familiarity, and an optional goal.

I would keep the direction. A full theme replacement is less valuable right now than fixing font application and making all controls/screen states consistent. Soft shadows and luminous accents work well when they establish hierarchy; applying equally strong treatment to every card, input, and secondary control makes the interface harder to scan. Small 10–12 px supporting labels deserve a readability pass, particularly in dense forms and concept details. This is a design judgement, not a claim that every small label fails contrast or accessibility.

The main weakness is that ARIA still feels like a collection of tools in some workflows. A selected concept's Continue studying link goes to generic `/app/learn`; the learner's immediate intent is lost. The polished dashboard/map/study areas also use different error, loading, and dialog patterns from older screens. Confidence in the app depends on those workflows being truthful and predictable, not only attractive.

### Suggested order

1. **Reliability:** fix microphone policy, context races, failed audio handling, and false logout success.
2. **Consistency:** repair fonts, unify dialogs and notifications, make storage optional, and distinguish request failures from empty results.
3. **Learning continuity:** carry selected subject, concept, source, and goal through study/practice/review navigation.
4. **Capability clarity:** tell learners when audio/voice/AI needs setup or is unavailable, with a useful next action rather than raw infrastructure terminology.
5. **Visual refinement:** reduce competing shadows, standardize spacing and text scales, align palette names and copy, then consider a Midnight Observatory prototype if the current direction still feels insufficient.

### Enhancements worth adding

- **Study/practice this concept:** preselect the concept, show relevant source evidence, and offer a targeted quiz. Reuse existing concept-targeted assessment support instead of adding another unrelated destination.
- **An actionable session recap:** key ideas, remaining gaps, and one next action; counts of questions/replies are useful but not a learning summary. Label generated content and preserve its source/session context.
- **A first-session guided path:** choose a subject, add material if needed, learn, take a short assessment, then see the map/roadmap change. Keep it optional and avoid another long onboarding wizard.
- **A unified search:** subjects, materials, notes, concepts, and saved conversations, with clear result types and direct navigation.
- **Better source navigation:** open the specific excerpt behind an answer/concept, return to the same reading position, and connect newly processed material to confirmed concepts once the API exposes associations.
- **Evidence-based progress trends:** show what changed and why, using actual evidence history; avoid treating every interaction as proof of mastery.

Spaced review, reminders, assessments, audio, and badges already exist. Improve their connections and reliability before building duplicate feature systems. Extra particles, sound effects, 3D scenes, and more permanent movement are low-priority compared with these improvements.

## 3. What passed and what remains uncertain

**Passed in this review:** TypeScript and full-source ESLint; 19 real-backend cases covering profile persistence, password change, session revocation, export/context deletion, real assessment scoring, empty audio/source listing, invalid-password messaging, ordinary sign-out, notifications/read state/preferences, planner CRUD/accessibility, and progress/badges/accessibility.

**Confirmed browser probes:** microphone policy denial; stale overlapping toast; Planner old-subject response overwrite; confirmation focus escape; unresolved font alias; anonymous workspace loading.

**Not established:** complete working audio playback/resume on this host; real microphone/transcription; live cloud-provider quality, latency, and account model availability; production deployment/CORS/session behavior on a real public domain; comprehensive browser/device compatibility. Source-confirmed risks are not represented as successfully reproduced failures.

The app is a strong working prototype with a good design identity. I would address the P1 workflows and shared-component problems before describing it as ready for broader learner use. The next best release should make the current features feel trustworthy and connected; it does not need a large new feature list.
