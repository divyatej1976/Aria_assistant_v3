# ARIA UI polish release verification — 2026-10-14

This follow-up closes the six polish phases and the assessment score-history gap. The release branch is `codex/ui-polish`, created from the existing `master` checkout and merged with `origin/main` before the new commits. The PR therefore also includes the previously unmerged master work; its scope is the complete frontend/backend integration, rather than only visual changes.

## Verification

| Check | Result |
| --- | --- |
| Full backend pytest | 536 passed, 10 skipped, 4 warnings |
| TypeScript `npx tsc --noEmit` | Passed |
| ESLint `npx eslint app components lib` | Passed |
| Full hermetic Playwright | 156 passed in 17.3 minutes |
| Auth/smoke recheck after final landmark fix | 11 passed; sign-in Axe reports zero violations |
| Visual/accessibility matrix | 4 groups passed; 56 screenshots |
| Credential scan | No Groq/OpenAI-like credentials found among Git candidates or reachable history |

The 10 backend skips require PostgreSQL; Docker was unavailable. These results verify SQLite and local integration, not PostgreSQL concurrency or a live cloud-model response. The E2E backend uses blank LLM, embedding, and cloud-speech keys and a disposable SQLite database. The application `.env` and normal user database were preserved.

The full run exposed two moderate sign-in Axe findings: `landmark-one-main` (missing main landmark) and `region` (content outside landmarks). A separate diagnostic confirmed both. Changing the shared auth wrapper to a semantic main landmark cleared them, and all 11 affected auth/smoke tests passed again after that final change. TypeScript and ESLint were rerun. The targeted 56-state visual matrix has no serious/critical findings. These checks do not establish universal accessibility compliance.

Visual scenarios use explicit response fixtures to reliably expose rare states. Separate connected Playwright tests exercise the actual backend. Screenshots cover Aurora/light and Noir/dark at 1440 and 375 pixels; mobile uses reduced motion. Automated checks assert no serious/critical Axe findings, no horizontal page overflow, and no uncaught page errors. Representative screenshots were also inspected visually.

For this run, the isolated frontend/backend ports were 3140/8040 and the disposable database was `e2e-review-verification.db`. With those servers running, the browser command was `npx playwright test --output=test-results-review-final` from `frontend-v2`, with `ARIA_INTEGRATION_EXTERNAL_SERVER=1`, `ARIA_UI_BASE_URL=http://localhost:3140`, and `NEXT_PUBLIC_API_URL=http://localhost:8040`. The backend launcher is `frontend-v2/tests/run_integration_backend.py`; stop it before resetting its database. TypeScript and ESLint ran from `frontend-v2`; backend verification used `python -m pytest tests` with the integration environment and `PYTHONPATH=backend`.

## Changes and regressions fixed

- Recreate only validated disposable `e2e-*.db` files before schema creation; regression coverage verifies missing columns are restored and application/outside paths are refused.
- Add completed assessment scores to the existing list response and show an accessible, chronological sparkline on a fixed 0–100% scale. No schema migration is needed. Empty history does not imply a zero score.
- Remove unused `.hero-orbits` CSS; ignore `.claude/launch.json`, temporary Next build directories, test results, logs, and disposable databases.
- Keep tutor notifications clear of recording controls; update the roadmap integration test to its current phase/tile UI while retaining mastery assertions.
- Give the first-session checklist the full mobile width; make modal panels opaque; correct selected-chip contrast in Noir.
- Give roadmap panels stable IDs and the scrollable conversation keyboard access. Wait for finite counters to settle before snapshot accessibility checks.
- Give authentication pages a semantic main landmark; assert a single main landmark in the sign-in smoke test.

## Commit organization

Backend persistence/provider/workflow changes, deployment hygiene, shared UI, roadmap, tutor, dashboard, assessments, materials/audio, map/progress, planner/account, onboarding, tests, and documentation are separate commits. The upstream planning-document merge is retained without rewriting existing history.

## Next features

Weekly goals and badges, per-concept assessment trends, and an optional onboarding tour remain future work. Assessment score history is now implemented.

## Screenshot index

The following matrix links all 56 captured states. Development screenshots contain the Next.js development indicator; it is not application UI.

| State | Aurora desktop | Aurora mobile | Noir desktop | Noir mobile |
| --- | --- | --- | --- | --- |
| dashboard-new | [View](screenshots/verification/aurora-1440-dashboard-new.png) | [View](screenshots/verification/aurora-375-dashboard-new.png) | [View](screenshots/verification/noir-1440-dashboard-new.png) | [View](screenshots/verification/noir-375-dashboard-new.png) |
| dashboard-progress | [View](screenshots/verification/aurora-1440-dashboard-progress.png) | [View](screenshots/verification/aurora-375-dashboard-progress.png) | [View](screenshots/verification/noir-1440-dashboard-progress.png) | [View](screenshots/verification/noir-375-dashboard-progress.png) |
| roadmap-collapsed | [View](screenshots/verification/aurora-1440-roadmap-collapsed.png) | [View](screenshots/verification/aurora-375-roadmap-collapsed.png) | [View](screenshots/verification/noir-1440-roadmap-collapsed.png) | [View](screenshots/verification/noir-375-roadmap-collapsed.png) |
| roadmap-expanded-states | [View](screenshots/verification/aurora-1440-roadmap-expanded-states.png) | [View](screenshots/verification/aurora-375-roadmap-expanded-states.png) | [View](screenshots/verification/noir-1440-roadmap-expanded-states.png) | [View](screenshots/verification/noir-375-roadmap-expanded-states.png) |
| learn-thinking-eight-seconds | [View](screenshots/verification/aurora-1440-learn-thinking-eight-seconds.png) | [View](screenshots/verification/aurora-375-learn-thinking-eight-seconds.png) | [View](screenshots/verification/noir-1440-learn-thinking-eight-seconds.png) | [View](screenshots/verification/noir-375-learn-thinking-eight-seconds.png) |
| learn-reply-error | [View](screenshots/verification/aurora-1440-learn-reply-error.png) | [View](screenshots/verification/aurora-375-learn-reply-error.png) | [View](screenshots/verification/noir-1440-learn-reply-error.png) | [View](screenshots/verification/noir-375-learn-reply-error.png) |
| learn-daily-review | [View](screenshots/verification/aurora-1440-learn-daily-review.png) | [View](screenshots/verification/aurora-375-learn-daily-review.png) | [View](screenshots/verification/noir-1440-learn-daily-review.png) | [View](screenshots/verification/noir-375-learn-daily-review.png) |
| learn-focus | [View](screenshots/verification/aurora-1440-learn-focus.png) | [View](screenshots/verification/aurora-375-learn-focus.png) | [View](screenshots/verification/noir-1440-learn-focus.png) | [View](screenshots/verification/noir-375-learn-focus.png) |
| assess-empty | [View](screenshots/verification/aurora-1440-assess-empty.png) | [View](screenshots/verification/aurora-375-assess-empty.png) | [View](screenshots/verification/noir-1440-assess-empty.png) | [View](screenshots/verification/noir-375-assess-empty.png) |
| assess-disabled | [View](screenshots/verification/aurora-1440-assess-disabled.png) | [View](screenshots/verification/aurora-375-assess-disabled.png) | [View](screenshots/verification/noir-1440-assess-disabled.png) | [View](screenshots/verification/noir-375-assess-disabled.png) |
| assess-modal-error | [View](screenshots/verification/aurora-1440-assess-modal-error.png) | [View](screenshots/verification/aurora-375-assess-modal-error.png) | [View](screenshots/verification/noir-1440-assess-modal-error.png) | [View](screenshots/verification/noir-375-assess-modal-error.png) |
| assess-scores | [View](screenshots/verification/aurora-1440-assess-scores.png) | [View](screenshots/verification/aurora-375-assess-scores.png) | [View](screenshots/verification/noir-1440-assess-scores.png) | [View](screenshots/verification/noir-375-assess-scores.png) |
| materials | [View](screenshots/verification/aurora-1440-materials.png) | [View](screenshots/verification/aurora-375-materials.png) | [View](screenshots/verification/noir-1440-materials.png) | [View](screenshots/verification/noir-375-materials.png) |
| audio | [View](screenshots/verification/aurora-1440-audio.png) | [View](screenshots/verification/aurora-375-audio.png) | [View](screenshots/verification/noir-1440-audio.png) | [View](screenshots/verification/noir-375-audio.png) |
