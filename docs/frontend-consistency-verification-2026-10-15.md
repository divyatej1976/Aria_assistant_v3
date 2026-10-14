# Frontend consistency follow-up — 2026-10-15

This follows the [UI-polish release verification](ui-polish-release-verification-2026-10-14.md) on `codex/ui-polish` and draft PR #1. The assessment score chart, safe E2E database reset, dead orbit CSS removal, ignored local launch/build files and logical commit split were already completed; they are not open tasks.

## Consistency scope

- Friendly note-review labels for New, Reviewing, Learning and Mastered states, with readable fallback text.
- Theme tokens for achievement gradients and foreground colours in the tutor and account avatar.
- Shared layout classes for repeated card headers, dialog headings/actions, gaps and empty-state cards. Dynamic styles remain local where they represent data.
- Shared loading states for account, tutor and planner, and the shared error component for tutor retry feedback.
- Sentence case for screen headings, buttons and related accessible labels; typographic ellipses; “Building your roadmap…” during creation.

The named dataviz skill is not available in this session; chart colours continue to use the app's palette tokens and accessible text alternatives.

## CI issues discovered

The first PR checks failed before reaching a complete browser run. These were separate from the earlier SQLite schema problem:

- Python lint: sorted imports and formatted long expressions without changing service behavior.
- Fresh migrations: the metadata-driven foundation already creates the daily-review column/constraint; the later migration now checks both before adding them. A repeat-upgrade regression check preserves data and uniqueness.
- Frontend contract build: supply the backend import path and blank cloud keys to the E2E schema helper.
- PostgreSQL tests: enable the vector extension before creating ORM tables, then seed required parent rows in six service fixtures instead of relying on SQLite's unenforced foreign keys.
- Secret scanning: nine exact historical fingerprints refer to public synthetic test keys/passwords and a `generation_token=token` expression. Exceptions are confined to those commits, paths, rules and lines. The default scanner remains enabled and its CI check passes.
- Dependency audits: update cryptography to 50.0.2 or newer within the 50.x series; the Python audit passes with the repository's pre-existing two exclusions and no added exclusions. [Upstream changelog](https://cryptography.io/en/latest/changelog/) and [OpenSSL advisory](https://github.com/advisories/GHSA-537c-gmf6-5ccf).

Next.js and its matching lint configuration are now 16.4.1, with resolved transitive dependencies refreshed. The production audit reports zero vulnerabilities, and the production build passes. [Upstream Next.js advisory](https://github.com/advisories/GHSA-vcvr-r3jv-pc5j).

The full npm audit remains a merge blocker: it reports five high-severity package entries from one development-tool chain (`eslint-config-next` → its plugin → `fast-glob` → `micromatch` → `braces`). The [braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) lists no patched release. The audit command and severity gate are unchanged. It now runs after the browser tests, with `if: always()`, so browser verification can execute while the audit continues to fail the job. No downgrade to the obsolete Next.js 14 lint configuration or additional security exception was applied.

## Verification

| Check | Result |
| --- | --- |
| Fresh browser baseline before UI edits | 156 passed in 18.8 minutes |
| Backend after cryptography update | 536 passed, 10 PostgreSQL-specific skips |
| PostgreSQL CI | 546 passed; full migration upgrade/downgrade/upgrade round-trip passed |
| Corrected service fixtures, local | 56 passed |
| TypeScript and ESLint | Passed |
| Production build, Next.js 16.4.1 | Passed |
| Production npm audit | Zero vulnerabilities |
| Full npm audit | Blocked by the unpatched development dependency above |
| Python dependency audit | Passed with two pre-existing exclusions |
| Full browser run after consistency edits | 162 passed in 17.6 minutes, including all six new consistency tests |
| Expanded Account/Progress visual recheck | 2 passed; eight screenshots across both widths/palettes |

PostgreSQL, backend, backup/restore, secret scanning, build and production preflight passed in CI at revision `1c0e87b`. The remaining commits adjust two escaped headings, profile-note spacing, screenshot capture and documentation; backend code is unchanged. The full npm audit remains blocking. The separate backend run verifies SQLite locally, while PostgreSQL and migration round-trip validation run in CI.

The final browser run used blank cloud keys, disposable `e2e-consistency-verification.db`, frontend port 3150 and backend port 8050. The [56-state screenshot index](ui-polish-release-verification-2026-10-14.md#screenshot-index) is refreshed for the current labels and layouts. No live Groq call was made.

The eight additional Account/Progress captures below use explicit response fixtures and reduced motion, with accessibility and overflow checks at both widths. They extend the evidence to 64 screenshots. Representative captures were also inspected visually.

| Page | Aurora desktop | Aurora mobile | Noir desktop | Noir mobile |
| --- | --- | --- | --- | --- |
| Account | [View](screenshots/consistency/aurora-1440-account.png) | [View](screenshots/consistency/aurora-375-account.png) | [View](screenshots/consistency/noir-1440-account.png) | [View](screenshots/consistency/noir-375-account.png) |
| Progress | [View](screenshots/consistency/aurora-1440-progress.png) | [View](screenshots/consistency/aurora-375-progress.png) | [View](screenshots/consistency/noir-1440-progress.png) | [View](screenshots/consistency/noir-375-progress.png) |

## Deferred features

Learn shortcuts, dashboard links into the last session, milestone follow-up prompts, weekly goals/badges and per-concept history remain separate feature work after the polish ships. A “Mark as studied” action should record study coverage without asserting mastery; a quick check should supply evidence. An onboarding tour remains conditional on real-user feedback about the existing checklist.
