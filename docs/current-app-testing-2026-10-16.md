# Current ARIA acceptance review — 2026-10-16

This review tests the current implementation, rather than repeating the earlier improvement list. Product code was not changed during the review.

## Environment and scope

Used an isolated frontend on port 3160 and backend on port 8160, a fresh SQLite test database, and blank cloud-provider keys. The user's normal app and data were left separate. This verifies offline behavior and integration contracts; it does not establish live LLM answer quality, physical microphone access, real speech-provider availability, or PostgreSQL behavior.

TypeScript and ESLint both passed. The full backend suite returned **586 passed, 10 skipped, 1 failed**. The failure was `test_audio_heartbeat_keeps_slow_work_out_of_recovery`: a very short lease/heartbeat timing check observed PROCESSING instead of READY. Three subsequent isolated runs all passed. Treat this as an unresolved timing-sensitive test result, not a fully green backend run or a confirmed production failure.

The broad browser review covers 153 unique tests across the original run and a continuation: **150 passed, 2 failed, 1 timed out/stalled**. The two failures are the stale onboarding assertion and inconsistent audio fixture described below. The stalled subject-switch case was interrupted, then the remaining tests were run separately (44 passed, 1 failed, including two overlapping passes from the initial run). This is not a fully green suite. Four additional exploratory tests intentionally assert recovery/keyboard behavior and expose the four reproducible bugs below; those failures are separate from the existing suite.

## Confirmed issues

All four findings affect the assessment player and are functional P2 issues.

### 1. Timed assessments regain time after reload

In a real 60-second exam, advance six seconds, reload, and resume. The display goes from **54 seconds back to 60 seconds**. Answers survive, but the timer does not.

`frontend-v2/components/quiz-player.tsx:51` initializes remaining time from the full limit. The draft in `frontend-v2/app/app/assess/page.tsx:39` holds answers and marked state, without timing state. Persist a deadline and derive remaining time on resume; use a server deadline if enforcing exam timing is a requirement.

Evidence: `frontend-v2/test-results-acceptance-exploratory-final/exploratory-total-timed-as-7e576-remaining-time-after-reload/resumed-timer.png`.

### 2. Failed timed auto-submit repeatedly sends requests

Force submission to return HTTP 503. With a 10-second timer, advancing to 15 seconds produces **six submission POSTs**, rather than one failed submission followed by an explicit retry option.

The expiry effect at `frontend-v2/components/quiz-player.tsx:121` runs again on each negative countdown tick. Add a one-shot expiry/submission guard, retain answers, and expose a deliberate retry. Keep the submission idempotency key stable across retries. Duplicate evaluations were **not** observed; the backend also checks for an existing evaluation for the attempt.

Evidence: `frontend-v2/test-results-acceptance-exploratory-final/exploratory-timer-submits--7f4c8-n-the-submit-endpoint-fails/` and `verification-acceptance-exploration-final-20261016.log`.

### 3. Review flags disappear after reload

Answer and flag question 1, reload, resume, and return to question 1. The answer remains selected, but the flag is gone.

The player's local flagged state at `frontend-v2/components/quiz-player.tsx:47` is not connected to the parent's persisted marked state (`frontend-v2/app/app/assess/page.tsx:170`). Persist and restore the actual player flags.

Evidence: `frontend-v2/test-results-acceptance-exploratory-final/exploratory-flags-are-rest-b4a4d-her-with-saved-quiz-answers/resumed-flag.png`.

### 4. Enter on “Flag to review” advances the question

Focus the flag button on question 1 and press Enter. The player advances to question 2 instead of remaining on the question while flagging it.

The global Enter handler at `frontend-v2/components/quiz-player.tsx:144` invokes the primary action even when an interactive control has focus. Scope the shortcut or ignore button/link/select targets so native keyboard activation performs just the focused action.

Evidence: `frontend-v2/test-results-acceptance-exploratory-final/exploratory-keyboard-flag--37111-es-not-advance-the-question/keyboard-flag.png`.

## Verified improvements

- Assessment presets, source choices, question formats/count, difficulty, timing options, practice/exam feedback, one-question navigation, answer persistence and results are implemented. The core creation/completion/resume browser checks pass; the edge cases above still need work.
- The real roadmap wizard sends and saves the goal, intermediate level, four hours/week, interview focus and a 2026-12-01 deadline correctly. The offline result is visibly labeled a general starter plan. AI-generated curriculum quality was not tested with live keys.
- Existing browser checks verify chat persistence, attachment isolation, end-of-day review, direct audio from text/upload/selected chats, and orchestrated audio action-card retry/lost-response recovery.
- The UI has clearer Home guidance, cleaner Learn controls and more actionable roadmap Study/Quiz actions than the earlier version.

## Visual checks

A separate real-user visual audit passed at **1440px and 375px**, in both **Aurora and Noir**, with reduced motion. It captured Home, Roadmaps, Learn, Materials, Audio and quiz setup, plus the roadmap confirmation: **25 screenshots**. No document horizontal overflow was detected; quiz-dialog overflow checks and serious/critical axe checks also passed. The existing responsive sweep additionally passed across five breakpoints and both palettes; accessibility sweeps across all app routes and auth routes passed. Score-trend chronology, its accessible alternative and empty-score behavior passed.

Screenshots: `frontend-v2/test-results-acceptance-probes/visual-real-roadmap-setup--27940-at-both-widths-and-palettes/`.

Selected screenshots are also preserved in `docs/screenshots/acceptance-20261016/`: [mobile Home](screenshots/acceptance-20261016/home-mobile.png), [desktop Roadmaps](screenshots/acceptance-20261016/roadmap-desktop.png), [desktop Learn](screenshots/acceptance-20261016/learn-desktop.png), and [mobile quiz setup](screenshots/acceptance-20261016/quiz-setup-mobile.png).

The existing tracked screenshot sets were deliberately not overwritten. These checks do not cover every possible content length or every animation state. Aurora/Noir checks should not be read as a comprehensive light-mode audit.

## Existing-test maintenance

The sign-in test in `frontend-v2/tests/auth.spec.ts:17` expects the old heading “Start your learning journey”. Authentication correctly navigates to `/onboarding`, whose current heading is “Welcome to ARIA”. This is a stale assertion, separate from a product login failure.

The audio retry test at `frontend-v2/tests/review-fixes.spec.ts:97` also fails: its generation mock returns an episode, but the subsequent authoritative list mock returns an empty list. The card is removed, so its disabled-play-button assertion cannot find the card. Its error-message checks pass first. Correct the persistence fixture before interpreting this as a product retry failure. The separate subject-switch test at line 64 times out with a held mocked response and stalls teardown; it was interrupted and excluded from the remaining run. That check remains unverified.

## Opinion and next priority

The user is right that most earlier suggestions are already implemented. Another broad redesign or feature list is not warranted by this review. Keep the current visual direction and fix assessment timing, failed-submission recovery, saved flags and keyboard activation first. Then update stale assertions and investigate the short-lease audio test under load.

One optional refinement: the mobile quiz setup is long. A sticky “Start quiz” footer or progressive settings could reduce scrolling. This is a usability suggestion, not a failed test.

## Reproduction and logs

- Backend: `venv/frontend-integration/Scripts/python.exe -m pytest tests -q -p no:cacheprovider --tb=short` with `PYTHONPATH=backend`, `PYTHONUTF8=1`.
- Static checks: `npx tsc --noEmit` and `npx eslint app components lib` in `frontend-v2`.
- Browser environment: `ARIA_INTEGRATION_EXTERNAL_SERVER=1`, `ARIA_UI_BASE_URL=http://localhost:3160`, `NEXT_PUBLIC_API_URL=http://localhost:8160`.
- Browser suite log: `verification-acceptance-playwright-20261016.log`.
- Continuation log: `verification-acceptance-remaining-20261016.log`.
- Backend log: `verification-acceptance-backend-20261016.log`.
- Exploratory repro log: `verification-acceptance-exploration-final-20261016.log`.
- Visual audit log: `verification-acceptance-visual-20261016.log`.
- Isolated repro scripts: `frontend-v2/test-results-acceptance-exploration/` (ignored test artifacts, not additions to the CI suite).
