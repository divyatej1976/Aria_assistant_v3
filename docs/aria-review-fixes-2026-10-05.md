# ARIA review fixes — 5 October 2026



Complete scope: [combined review](aria-full-stack-review-2026-10-05.md). Work is ongoing. The dated original findings are preserved; product enhancements remain separate.



## Recorded verification



Latest full backend run: **484 passed, 2 PostgreSQL-only skips**, three existing warnings, 201.92 seconds. This run includes the current workflow metadata fencing, backup publication/discovery and workflow read-contract changes. Separate PostgreSQL idempotency and audio contention checks are recorded below; SQLite skips do not establish PostgreSQL coverage. Current local database is **0023_idempotency_payload**, and the restarted backend reports database/schema OK. Latest full review browser run: **33 passed** in 1.4 minutes, including all migrated form dialogs, using intercepted API fixtures. Development container build and isolated speech/client-tool runtime checks passed; full Compose startup and production recovery remain open.



B17 output-limit verification: 26 AI governance/integration tests passed; targeted Ruff passed. The regression checks both text and structured generation send the exact reserved completion limit and reconcile reported usage against it. This source change has not yet been loaded into the already-running local backend; restart remains required after the budget batch.



B17 malformed-response accounting: text and structured responses now record reported token usage before extracting choices, preserving global charges and learner settlement when answer extraction fails. Structured input estimates now include the system instruction. Regression coverage checks malformed empty choices with reported usage in both paths. Governance/integration batch: 28 passed (one existing deprecation warning). Transport failures with uncertain provider billing and other B17 gaps remain open. These changes still require a local backend restart.



B17 invalid-usage verification: negative, string, boolean, fractional and NaN token metadata now use nonnegative token estimates instead of reducing spend or breaking settlement. 23 governance tests passed; targeted Ruff passed. The local backend was restarted with all current budget changes; readiness returned HTTP 200 with database/schema OK. Cancellation/uncertain transport billing, concurrent admission and audio/embedding accounting remain open.



B22 container dependency correction: development now installs espeak-ng and PostgreSQL client 16, matching production's supported local speech and backup capabilities. Both bases explicitly select python:3.12-slim-trixie to match their PGDG repository. 19 development-config/production-preflight tests passed; targeted Ruff passed. Actual image build is in progress (exec session 14953, aria-review-backend:dev); runtime speech/backup-tool smoke verification remains pending.



Consolidated verification started after B17/B22 changes: full pytest run launched; results pending. Existing Docker build session 14953 completed apt installation (espeak-ng and PostgreSQL client 16) and is installing Python dependencies. No Docker runtime or full-suite completion is claimed yet.



B12 encryption rotation correction: new encryption and rotation jobs require the primary key; an OLD-only deployment can still decrypt existing learner credentials but capabilities disable new personal-key storage. Regression verifies rejected replacement preserves the existing credential. Targeted BYO-key verification is running separately from the full suite; local backend/image must be refreshed to include this later source change.



B12 audio integration: Audio Studio now reads deployment cloud-speech capabilities and explains configured, unconfigured/local-fallback and unavailable-status cases without implying successful provider verification. Personal tutor-key scope is explicit and existing playback/conversion remains accessible. Browser regression with a usable personal tutor key and no cloud speech passed. Full backend suite and Docker build continue on their original handles.



Consolidated backend verification completed: 472 passed, 3 existing dependency/config deprecation warnings, 221.19 seconds. This run collected before the additional OLD-only encryption regression; that later key-management batch passed 13 tests and Ruff separately. The container image build remains in progress; no image/runtime completion claimed.



R11 deletion/race verification: two browser cases passed. A downloaded URL is revoked after confirmed deletion; a held playback response released after deletion creates no URL and no audio element. TypeScript and targeted ESLint passed. Container build session 14953 remains live, downloading dependencies.



R11 position preservation: track switches save the prior position; workspace cleanup sends pending progress with keepalive, and deletion removes pending updates. Older progress replies cannot overwrite newer local state. Browser navigation regression verifies second 7 is saved after the periodic save at second 6. Initial browser test passed; final static/repeated lifecycle checks pending.



R11 lifecycle batch: four browser tests passed (navigation URL cleanup, deletion cleanup, delayed-deletion race, final position flush). TypeScript passed; cleanup captures the stable pending-update map to satisfy the effect dependency check. Keepalive remains best-effort under network/server failure; actual container build remains active.



Consolidated review-browser verification: 20 passed in 49.0 seconds, covering routing, recovery, fonts, sign-out, microphone policy, keyboard focus, roadmap/key capabilities, draft failure and audio lifecycle/progress. R13 screenshot paths now use testInfo.outputPath for all three learning-agent screenshot cases; runtime screenshot scenarios remain unexecuted. Container build session 14953 is still downloading dependencies.



B23 roadmap-list batching: listing now fetches all owned milestones once and subject-scoped learner states once, reuses the existing completion rules and commits once. Roadmap/review regression batch: 59 passed and Ruff passed. New 30-roadmap regression verifies three SELECT statements, one commit and all supported milestones completed. Concept-version caching remains open. This later backend change is not loaded in the native service or in-progress image build yet.



B23 batched-list isolation verification: the scale regression now tests both a subject-filtered list and an account-wide list, with identical skill names carrying SUPPORTED versus NEEDS_REVIEW evidence in different subjects. Both retain three SELECTs and one commit; other-subject evidence does not complete or downgrade the wrong roadmap. Concept-cache implementation remains pending.



B23 concept synchronization batching: extracted names are deduplicated in order, existing concepts are fetched in one owner/subject-scoped query, missing concepts flush together, and each concept's matching terms are computed once per synchronization. 31 concept/assessment/learner-loop tests passed and Ruff passed. Persistent version caching remains open; these source changes are not yet loaded in the native service or original image build. Container session 14953 is installing the downloaded Python dependencies.



B22 actual container verification: aria-review-backend:dev build completed. Disposable container with network disabled generated valid RIFF/WAV speech (82,414 bytes, measured 2 seconds), reported pg_dump/pg_restore PostgreSQL 16.15, imported the application and verified migration files. Full Compose startup/database integration and production-image runtime remain unverified. The built source snapshot predates the later encryption/roadmap/concept edits. R3 browser verification: FAILED conversion shows both error toast and retry guidance with playback disabled; retry returning READY enables playback and removes retry guidance. Test, TypeScript and targeted ESLint passed.



R2 delayed-response verification: Audio Studio switched to subject B while subject A's listing was held; releasing A afterward did not replace B's visible recording or active selection. Browser regression, TypeScript and targeted ESLint passed. Delayed-response coverage for the other subject workspaces remains pending. Native backend restarted with current key-rotation, roadmap batching and concept batching source; readiness returned HTTP 200, database/schema OK.



B15 direct subprocess privacy: pg_dump and pg_restore now suppress inherited raw stderr. Restore command failures return a safe error-type message and exit status 1; backup failures suppress the original exception chain so standard tracebacks do not expose its command/output. 11 disaster-recovery script tests passed; targeted Ruff passed. Operators lose raw server diagnostics in these application paths by design; failures remain detectable via exit status/error type. Broader error-path audit remains open. Backup service source change requires the next native backend restart.



Backup publication reliability: dumps now write to owner-only temporary stages excluded from backup discovery, encrypt before publication when configured, and atomically rename only after success. Dump/encryption failures remove their stages and do not prune or replace existing archives. Encrypted stages are owner-only from creation; timestamp precision avoids ordinary same-second overwrite. latest_backup now includes encrypted archives. 24 recovery/weakness tests passed; Ruff passed. Regression verifies partial dump failure preserves previous bytes and invalid encryption leaves no plaintext/archive. Production disaster-recovery execution and next native backend reload remain pending.



Backup discovery/retention consistency: backup discovery, pruning and automatic restore selection now share completed_backups, accepting only regular files ending in .dump.gz or .dump.gz.enc. Partial files and directories cannot masquerade as latest backups or consume retention slots. Regression covers mixed encrypted/plain archives, misleading partial filenames and directories. 25 recovery/weakness tests passed; targeted Ruff passed. Full recovery drill and loading these later service changes remain pending.



B18 release-race repair: reservation deletion now conditionally checks the observed expiry and unfinished response status, preserving completion or renewal that occurs after lookup. Regression injects completion between lookup and deletion and verifies the stored response/status survive. This is partial fencing: caller-owned claim tokens, stale-worker record/release after takeover and PostgreSQL concurrent execution remain open. Local backend has not loaded this later source change.



B18 renewal-release regression passed: renewing expiry after lookup prevents stale deletion. 16 idempotency tests passed and full backend/tests Ruff passed. Full backend suite is running on exec session 8847. Disposable PostgreSQL verification container aria-review-postgres-20261006 launched on localhost:55432 without persistent volumes; tests and concurrency scenarios still pending. Remove this test container after verification; no application database is targeted.



Latest consolidated backend verification: 482 passed, 3 existing warnings, 203.92 seconds. PostgreSQL idempotency batch: 17 passed, one existing warning, 34.98 seconds, after initializing the disposable database's pgvector extension. Two independent PostgreSQL connections observed the same expired reservation simultaneously; exactly one returned ok and the other in_progress. Completion/renewal release regressions also passed on PostgreSQL. Full-suite collection preceded the newly added PostgreSQL-only test; its separate result is recorded here. Caller-owned stale-worker fencing remains open. Disposable PostgreSQL container is retained for the remaining database-specific checks and must be removed when those finish.



B18 caller-owned metadata fencing: workflow routes generate a unique claim ID, stored as the unreferenced internal reservation row ID. Takeover rotates it; claimed record/release use conditional SQL matching owner/scope/key/claim. Expired or replaced completion returns 409 with workflow-history guidance, preventing stale response publication. Regression verifies old release/record cannot mutate a replacement reservation or its completed response. Verification: 44 SQLite review/idempotency tests passed, one PostgreSQL-only skip; 18 PostgreSQL idempotency tests passed; 7 orchestration tests passed; targeted Ruff passed. This fences metadata, not already-running side effects: renewal/heartbeat and workflow-lease recovery alignment remain open. Native backend reload and updated full-suite verification remain pending.



PostgreSQL audio verification found seven fixture foreign-key failures: direct Note fixtures used nonexistent subject IDs. Fixtures now create/flush owned LearningContext rows explicitly. SQLite audio regression: 16 passed; Ruff passed. PostgreSQL rerun remains active on exec session 76157, with no failures in progress so far; final PostgreSQL result is not yet claimed. Native backend reload remains pending for the later backup/idempotency changes.



PostgreSQL audio rerun completed: 26 passed, one existing warning, 63.87 seconds. Native backend restarted with current backup and idempotency claim-fencing source; readiness HTTP 200. Audio tests validate independent-session lease behavior and heartbeat/recovery, but simultaneous queue-claim contention still needs a dedicated multi-thread PostgreSQL regression.



B07 PostgreSQL simultaneous claim verification: two independent connections contend for one pending artifact while synthesis is held. The losing worker returns PROCESSING, exactly one provider call occurs, the winning worker finishes READY, and one artifact/file remains with one generation attempt. Dedicated PostgreSQL test passed; targeted Ruff passed. Disposable database remains available for remaining database checks.



Workflow read contract follow-up (6 October): the task-list endpoint now returns HTTP 404 for missing or inaccessible workflows, matching workflow detail instead of the global validation handler's HTTP 422. A regression verifies successful owner access and identical missing/foreign responses for both endpoints. All **8 orchestration tests passed** (one existing dependency deprecation warning); Ruff passed for the changed route and tests. This check does not close the remaining workflow lease renewal/recovery requirements. The running native backend requires a restart to load this route change.





Local runtime follow-up: backend restarted with the workflow task-list response fix and current claim-fencing/backup code. /ready returned HTTP 200 with database/schema OK; frontend /app returned HTTP 200. A new complete backend regression run is in progress; prior full-suite counts do not establish coverage of subsequent changes.



R10 draft isolation follow-up: assessment workspace identity now includes learner ID as well as subject ID, resetting in-memory attempt state on identity changes. Four browser regressions verify only the current learner/subject draft offers Resume test; other-learner, other-subject and legacy shared-key drafts are ignored. All four passed. These tests verify initial draft selection, not a live identity-switch sequence. Existing drafts remain scoped on the device; logout cleanup/privacy policy and dynamic account-switch verification remain open.







Consolidated verification: full backend suite **484 passed, 2 PostgreSQL-only skips, 3 existing warnings**, 201.92 seconds. Full review browser suite **26 passed**, 55.7 seconds. Backend/tests Ruff passed before this run; TypeScript and changed assessment/browser-test ESLint passed after the latest frontend edit. Browser results use API fixtures and do not prove real authentication/provider, microphone hardware or push/email delivery. Workflow lease renewal, concept extraction cache, remaining subject-switch/modal coverage, full Compose and recovery verification remain required work.



B18 renewal primitive: added conditional renewal matching owner/scope/key/claim identity and requiring unfinished, unexpired ownership. Renewal cannot revive expired claims, extend replacements or mutate completed responses. Dedicated-session requirement prevents heartbeat commits from committing handler writes. Targeted regression passed (wrong owner/scope/key/token, live extension, expiry, replacement and completed-result cases). This primitive is not yet wired to workflow execution: heartbeat scheduling, lifecycle shutdown and recovery alignment remain open. Prior 484-test full run predates this primitive.



B18 heartbeat integration: keyed workflow execution now runs under a renewable claim using an independent session/thread. Renewal interval is one third of the reservation TTL, capped at 30 seconds; exit signals shutdown and joins for up to five seconds. Lost ownership, renewal errors or an unresponsive renewal thread fence successful response publication with HTTP 409. Handler exceptions propagate while shutdown still runs. Workflow/idempotency batch: 26 passed, one PostgreSQL-only skip; two heartbeat lifecycle tests passed after final shutdown-race correction; targeted Ruff passed. PostgreSQL slow-workflow overlap, renewal failure/cancellation scenarios and committed-side-effect recovery remain open. Running backend has not yet reloaded this heartbeat integration; previous full-suite result predates it.



B18 PostgreSQL heartbeat verification: all 22 idempotency tests collected before the final contention test passed on the disposable PostgreSQL database (50.30 seconds). The additional real two-connection renewal test passed separately (3.46 seconds): a 0.6-second reservation remained owned after more than its original TTL while heartbeat renewed it; a competing claim returned in_progress, and the original owner recorded its response. Three lifecycle tests also passed, including stopping renewal while preserving a handler exception. Ruff passed. This establishes reservation renewal, not transactional fencing of already-running domain side effects or full HTTP slow-workflow overlap; those recovery boundaries remain open.



B18 HTTP overlap verification: PostgreSQL-backed TestClient requests exercise the actual authenticated workflow route while a controlled handler is held beyond a 0.6-second original reservation TTL. Duplicate returns 409, first completes 201, subsequent same-key request replays its exact response, and only one handler invocation occurs. Dedicated regression passed (4.15 seconds); Ruff passed. This uses a held fake domain handler, so committed domain-write crash recovery remains open. Native backend restarted with heartbeat integration; readiness verification follows this entry.

Native heartbeat runtime readiness: HTTP 200, database/schema OK. Full-suite result remains 484 passed before heartbeat integration; targeted renewal/HTTP results are separate evidence.



B18 failure/configuration boundaries: reservation TTL and sweep interval now require positive integers, preventing immediate-expiry reservations and invalid scheduling. Regression rejects zero/negative values and accepts one second. Renewal exception regression verifies successful completion is fenced and logs retain only error type, omitting private diagnostic text. Two targeted tests and Ruff passed. The running backend already includes heartbeat integration, but the new settings validation requires its next restart. Broad workflow/idempotency rerun is pending below; earlier full-suite result predates these changes.

Final workflow/idempotency batch after timing and failure checks: 31 passed, three PostgreSQL-only skips, one existing dependency warning, 16.02 seconds. PostgreSQL renewal/HTTP results remain separately recorded.



R7 remaining modal follow-up: reusable native Modal introduced and Audio Studio conversion form migrated from a plain overlay. Browser regression verifies source-control initial focus, forward Tab containment, Escape dismissal and restoration of the opening button. Initial regression exposed DOM-order selection focusing Close before Source; explicit field-first selection repaired it, and rerun passed. Assessment, roadmap, planner and materials form overlays still require migration/verification; broad R7 completion is not claimed. Earlier 26-test browser suite predates this addition.





R7 assessment/roadmap forms: both creation overlays now use the shared native Modal. Two browser regressions passed, covering 14 forward and 14 reverse Tab steps inside each dialog, Escape dismissal, trigger-focus restoration and initial roadmap goal focus. Planner and materials forms remain open for migration and verification. Tracker status corrected to partial rather than treating confirmation-only coverage as all-dialog completion.



R7 planner/materials forms: Create Exam, Create Task, Create Material and Add Resource now use the native shared Modal. Planner close icon has an accessible Close label. Four browser regressions passed after correcting the Create Material test's trigger label to the actual Add Material button. Each verifies forward/reverse Tab containment, Escape dismissal and focus restoration. Source inventory finds modal-bg only in the shared native dialog components, rather than page-level plain overlays. Static checks and full browser rerun are tracked separately; no claim is made about every popover or assistive-technology combination.





Frontend consolidated verification after modal migration: all **33 review browser tests passed** in 1.4 minutes. This includes existing audio retry/subject-switch/cleanup/progress, auth failure, roadmap provenance, settings, draft isolation and seven form-dialog scenarios. ESLint over app/components/lib and the review test file passed. Earlier targeted TypeScript also passed. R10 explicit logout/account-switch draft policy remains open per the original review recommendation; initial scoped-draft tests do not replace that requirement.



R10 explicit draft policy implemented: successful sign-out or identity replacement clears the previous learner's scoped assessment drafts and the unsupported legacy shared draft. Other learners' drafts remain. Failed server sign-out leaves identity and drafts unchanged. Cleanup storage errors do not reverse a successful authentication mutation; an error notification explains that device drafts remain. Two browser tests passed for successful and failed sign-out. Dynamic account replacement and blocked-removal notification still need browser coverage. The successful sign-out test exposed landing-page/sign-in redirect contention; it currently verifies an anonymous destination rather than asserting the landing page, and that redirect race remains a separate open fix.



R4/R10 logout follow-up: explicit successful-sign-out state distinguishes deliberate logout from an anonymous workspace visit. ContextGuard and the profile action now agree on landing-page navigation, eliminating the observed sign-in/landing race. Five browser regressions passed: anonymous return-path redirect, failed sign-out preserving workspace, successful cleanup of current/legacy drafts, failed sign-out preserving drafts, and blocked draft removal showing a warning while landing-page sign-out completes. Other learners' drafts remain. Dynamic identity-replacement coverage remains open; earlier 33-test full browser run predates these changes.



R10 dynamic identity verification: real sign-in form starts with learner A resolved by AuthProvider, logs in to a mocked learner B session, and returns to the workspace. Browser regression confirms A's draft is removed and B's draft remains. Test passed; static results recorded separately. Authentication APIs are intercepted, so this validates frontend identity transition rather than live server session replacement.



## Consolidated finding tracker



The original combined review defines the full scope. Verified below means the stated regression behavior is proven; operational or integration limits remain explicit.



| Finding | Current evidence and remaining requirement |

| --- | --- |

| B01 Chat positions after deletion | Regression verified; next position derives from surviving messages. |

| B02 Related ownership and subject checks | Destination/reference/evidence-chain regressions and full backend suite passed. |

| B03 Assessment writes before parent validation | Parent checked before mutation; rejection preserves state. |

| B04 Roadmap completion scope | All required subject skills, prerequisites and reversals tested. |

| B05 Push outbound destinations | Allowlisted browser service hosts, redirects disabled, timeouts tested. Actual browser delivery unverified. |

| B06 Audio truncation | Segmentation and measured WAV assembly verified; real cloud provider delivery remains separate. |

| B07 Audio claims | PostgreSQL lease/lifecycle and simultaneous claim verified; one provider call/file, stale publisher fenced. |

| B08 Audio lifecycle and backup recovery | Cleanup/requeue regressions plus real encrypted PostgreSQL and separate audio-file recovery drill passed. Offsite/host-loss operations remain deployment responsibilities. |

| B09 Portable full export | Uncapped relationship-preserving export, binary semantics, real PostgreSQL concurrent-write snapshot, and cancellation cleanup verified. |

| B10 Citation grounding | Only prompt-included chunks become citations; limits and exclusions tested. |

| B11 Conversation provenance/history | Persisted fallback provenance, latest-first pagination and migration preservation tested. |

| B12 Credential/capability truth | Decryption/usability/model scopes and audio capability UI tested. Configuration is not provider verification; full runtime parity audit remains. |

| B13 Embedding outage | Lexical retrieval continues with healthy tutoring; regression passed. |

| B14 Readiness | Database/schema checks and safe configured-unverified provider reporting tested; native readiness OK. |

| B15 Error privacy | Logging, TTS/transcription, workflow and backup subprocess safe diagnostics tested. Broader direct-error audit remains. |

| B16 Roadmap validation/provenance | Four-phase schema, bounds, fallback and persisted generation origin tested, including frontend reload. |

| B17 Spending safeguards | Atomic learner/global admission, reconciliation, uncertain learner billing and month-boundary settlement implemented and targeted tested. Input/final-usage bounds, speech/embedding accounting and billing reconciliation remain. |

| B18 Idempotency | Atomic/fenced/renewable claims and durable workflow binding implemented; actual process-exit checkpoint and PostgreSQL regressions passed. Final schema/runtime alignment and full verification remain. |

| B19 Workflow database failures | Rollback, committed-handler retry suppression and durable uncertain-outcome checkpoints verified. Unknown interrupted outcomes require review instead of automatic replay. Final full verification remains. |

| B20 Resource replacement | Atomic staged replacement/version protection, preserved ready data and failed-source retry tested. |

| B21 Deterministic quizzes | Unique exact-quotation questions and learner-loop regressions passed. |

| B22 Development/production parity | Configuration, preflight, dev image build, speech/client-tool smoke verified. Full Compose and production image execution remain. |

| B23 Costly reads/extraction | Bounded/batched reads and durable extraction caching verified on SQLite and PostgreSQL, including invalidation and in-flight source-change checks. Final publication concurrency audit remains. |

| B24 Quality gates | Current full backend: 515 passed, eight PG-only skips; relevant PostgreSQL checks separately passed. Final frontend/static/runtime gates remain. |

| R1 Microphone policy | Real browser response-header regression passed; physical microphone remains unverified. |

| R2 Subject isolation | Keyed workspaces; delayed audio subject response test passed. Other subject workspace races remain. |

| R3 Audio failure truth | FAILED/retry/READY browser regression passed; processing-poll behavior needs final audit. |

| R4 Sign-out | Server failure retains identity; explicit successful-sign-out landing navigation and cleanup tested. |

| R5 Anonymous workspace | Sign-in redirect with return path verified. |

| R6 Toast lifecycle | Independent expiration and semantic notifications verified. |

| R7 Dialogs/popovers | All identified form overlays use native dialogs; keyboard containment/dismissal/restoration and palette tests passed. Final broad accessibility audit remains. |

| R8 Typography | Loaded root font tokens verified in browser. |

| R9 Roadmap loading errors | Recovery state and stale-detail protection implemented; browser failure regression passed. |

| R10 Local storage | Guarded optional persistence, scoped validated drafts, logout/account replacement cleanup, failed logout and blocked removal verified. Draft schema/attempt recovery and identity-switch in-memory state need final audit. |

| R11 Audio URLs/progress | Navigation, deletion, regeneration, held-download races and track-switch final position verified with browser API fixtures. Real synthesis and network-loss persistence are not guaranteed by these tests. |

| R12 Photo settings | Preview-only behavior stated accurately in UI. |

| R13 Configuration/test drift | Deployment models/policy fixed; screenshots use portable paths. Full screenshot integration and container startup verification remain. |

| R14 Theme/product copy | Aurora naming/default, heatmap interval and roadmap copy corrected; static checks passed. |



R11 regeneration verification: browser plays the original artifact, regenerates that source with the same artifact ID, verifies the old URL is revoked and the old audio element removed, then plays a freshly downloaded distinct URL. Navigating away revokes the replacement as well. Regression passed (7.5 seconds); TypeScript/ESLint completion tracked separately. API/audio bytes are fixtures, so actual sound quality/provider synthesis is not covered. Track-switch position and delayed-download regeneration races remain open.



7 October — R11 track-switch verification: first recording receives periodic position 6, then advances to 7 without another periodic save. Switching to the second recording issues a position-7 update for the first with completed=false and mounts only the second player. Browser regression passed. API/audio bytes are fixtures; network-loss persistence remains best-effort. Delayed-download regeneration still needs verification.



7 October — R11 delayed regeneration verification: playback download is held while the source is regenerated with the same artifact ID. Releasing the old response creates no object URL and mounts no player; replay requests fresh bytes and creates exactly one URL. Browser regression passed (6.8 seconds). Together with normal regeneration and track-switch tests, the identified URL replacement/progress scenarios are covered by API fixtures; real sound/provider and network-loss guarantees are not claimed.



7 October — B23 stable extraction inputs: context chunks now order by resource ID, chunk index and chunk ID; deterministic concept scoring breaks equal scores alphabetically instead of inheriting unordered set insertion. This prevents unchanged inputs from producing arbitrary extraction windows/fallback ordering across runs. Tie/limit regression and assessment/prompt batch passed: 22 tests, one existing warning. Durable version caching remains required; this is a prerequisite, not a cache implementation. Native backend reload pending for the ordering change.



7 October — B23 durable cache implementation: internal nullable LearningContext fingerprint/name fields and migration 0024 added, separate from editable configuration. Fingerprint includes full ordered chunk IDs/content, bounded rendered prompt/version, extraction limit, provider type and model. Cache reuse validates the owned concept names still exist, preserves concept IDs and avoids repeated extraction/link rewrites. Provider failures deliberately do not cache deterministic fallback, allowing later retries. Cross-session reuse, content/limit invalidation and failed-provider retry tests passed; concept/assessment batch 24 passed, Ruff passed. Migration preservation/runtime upgrade, additional invalidation/isolation cases and concurrent source-change audit remain pending. Native backend still uses the previous schema/source and must not reload until migration verification/upgrading completes.



7 October — B23 migration/runtime verification: seven cache/migration tests passed on SQLite and seven on PostgreSQL. Migration preserves subject/configuration data, initializes nullable cache fields as unknown, supports repeated upgrade and downgrade. Ruff passed. SQLite backup API saved a pre-0024 local snapshot, then Alembic upgraded aria_host.db to 0024_concept_sync_cache. Native backend restarted with cache and current settings validation. Readiness result recorded below; remaining model/prompt/isolation/cache-integrity and concurrency checks remain open.



7 October — B23 expanded invalidation: the cross-session cache regression now changes provider model and prompt version and confirms fresh extraction for each. Removing the cached concept and its links triggers repair with a new concept ID; the repaired result is subsequently reused. All six concept prompt/cache tests passed on SQLite, Ruff passed. PostgreSQL result follows separately. Source-change concurrency and final full-suite verification remain open.

Expanded concept cache PostgreSQL verification: six passed, one existing warning, 4.71 seconds. Deleted-concept repair uses real PostgreSQL foreign-key constraints.



7 October — B23 external source changes: chunk reads use populate_existing so a reused ORM session cannot hash/extract stale cached objects after another session commits new content. Regression retains the original chunk in the reading session, updates it through a separate writer, and verifies fresh extraction and the new concept. Seven concept/cache tests passed on SQLite, Ruff passed; PostgreSQL result separately recorded. This addresses committed changes before the next synchronization, not source replacement during an in-flight provider call. Native reload remains pending for this read-refresh refinement.

External material-change PostgreSQL verification: seven passed, one existing warning, 6.89 seconds, including an independent writer and reused reader session.



7 October — B23 in-flight material check: synchronization snapshots ordered chunk IDs/content before provider work, refreshes afterward, and rejects changed material before publishing concept/link/cache writes. Regression uses a separately committed writer during the provider call; stale names and cache marker are absent. SQLite concept/assessment batch: 26 passed; PostgreSQL concept/cache batch: eight passed (8.30 seconds); Ruff passed. This is an optimistic post-provider check, not an atomic lock against changes between validation and commit. Final concurrency audit remains open. Full backend suite launched against current tree (session 29646); no completion claimed. Native reload pending for this source-check refinement.



7 October — B17 uncertain failure accounting: owner-budget settlement now retains the provisional reservation when no trustworthy final usage exists, rather than refunding a possibly billable transport failure. Cancellation already leaves the reservation intact; new text/structured timeout and cancellation regressions verify that behavior. This is intentionally conservative estimated usage and can overcount failed/unbilled calls. Global admission/failure accounting, hard input bounds, speech/embedding accounting and reliable billing reconciliation remain open. The running native backend has not yet loaded this settlement change. Full backend session 29646 collected before this change/new tests and remains in progress.

B17 targeted verification: 27 AI governance tests passed, one existing warning, 15.56 seconds; Ruff passed. Tests cover text/structured unknown transport and cancellation reservations.



7 October — consolidated backend verification: 496 passed, four PostgreSQL-only skips, three existing warnings, 222.23 seconds. Collection preceded the uncertain-failure and atomic admission budget edits; those require separate/final verification.



B17 learner admission: persistent monthly learner reservations now use insert-if-missing plus a conditional SQL increment requiring the entire estimate to fit the remaining limit. Refused admission leaves spend unchanged; production accounting failure blocks before provider execution, and development fallback checks/charges under the process lock. Nonnegative integer token reservations required. Settlement docs no longer promise refunds for unknown billing. AI governance batch 28 passed, one PostgreSQL-only skip, Ruff passed. Global budget reservation/admission, heuristic input/final-usage overshoot, development fallback limitations and speech/embedding accounting remain open. Native backend reload pending for these budget changes.

B17 PostgreSQL admission verification: two passed, one existing warning, 4.40 seconds. Two simultaneous connections sharing a balance sufficient for 1.5 reservations produce one admission and one BudgetExceeded, with exactly one reservation persisted.



7 October — B17 admission boundary audit: production reservation-accounting failure now has a regression proving no process-fallback charge/admission occurs. Negative, boolean, fractional and string reservation token counts are rejected before SQL admission. Two historical quality tests were updated for the new intended policy: a full estimate must fit before admission, and unknown provider failures retain provisional usage rather than refunding it. Combined governance/quality verification remains in progress; no full result claimed yet.

Final B17 governance/quality batch: 47 passed, one PostgreSQL-only skip, one existing warning, 17.63 seconds; Ruff passed. Global reservation/admission remains open.



7 October — B17 global admission implemented: text/structured generation reserves global estimated usage with conditional monthly SQL admission when the deployment cap is active. The output reservation supplies max_tokens even without a learner cap. Usage logs skip the full global post-charge in this case; settlement applies only actual/estimated minus reserved tokens. Unknown failures keep global reservations. Learner admission failure refunds the global reservation before any provider dispatch. Existing governance/quality batch 47 passed, one PG-only skip; three new reconciliation/refund tests passed; Ruff passed. PostgreSQL simultaneous global admission test passed: one admission, one rejection, exactly one charge. Full-suite verification, reservation month-boundary alignment, unknown-billing reconciliation, token estimate/final-usage limits and audio/embedding accounting remain open. Native backend reload pending.



7 October — B17 month-boundary settlement: global and learner reservations now return their admission month; provider settlement and pre-dispatch refunds use that original month. Global development fallback accounting is keyed by month as well. Text and structured response regressions cross from October into November with unrelated new-month spend and verify both real accounting tables retain the correct values. Fallback refund regression verifies the new month is untouched. Governance/quality batch: 53 passed, two PostgreSQL-only skips, one existing warning, 16.32 seconds. Ruff passed. PostgreSQL results recorded separately; full suite and native reload remain pending.

B17 PostgreSQL month-boundary/concurrency verification: five passed, 36 deselected, one existing warning, 20.21 seconds. Real global and learner rows preserve the original-month settlement; simultaneous admission tests remain green.


11 October — B17 global unknown-billing verification: four text/structured timeout/cancellation regressions now assert both global and learner reservations remain charged when usage is unknown. All four passed; Ruff passed. Separate governance run before the strengthened assertions: 39 passed, two PostgreSQL-only skips. Sandboxed verification stalled in Windows asyncio socketpair creation; full suite rerun outside sandbox with saved diagnostics. No full-suite or review completion claimed.


13 October — full backend audit: 510 passed, six PostgreSQL-only skips, two failures, three warnings (265.89 seconds). The failures were raw exception text in the shared LogRecord factory and mixed encoding in this report. Both corrected; privacy/audio/encoding batch 44 passed, one skip; Ruff passed. This full run preceded the new workflow checkpoint changes, so final whole-suite verification remains required.

13 October — B18/B19 durable workflow crash checkpoint: migration 0025 adds a nullable internal workflow_id to request keys. Workflow creation and claim binding commit together before domain work. Expired unresolved checkpoints cannot be reclaimed or swept; retries return 409 with the original workflow ID, and interrupted RUNNING history is marked RECOVERY_REQUIRED. The same key cannot silently repeat potentially committed actions. An actual subprocess exits with code 23 after committing a note; reopening the database preserves the note/workflow/checkpoint and blocks reexecution. Recovery requires reviewing existing results rather than automatic replay of an unknown outcome. Workflow/idempotency/migration/process-exit batch: 34 passed, three PG-only skips (23.17 seconds). PostgreSQL targeted migration/checkpoint/concurrency batch: five passed (20.54 seconds), before the history-status assertion was expanded. Native schema upgrade/reload and final verification remain pending.

13 October — B08 real recovery drill: scripts/verify_recovery_drill.py runs only in explicitly named empty disposable source/restore databases. Real PostgreSQL 16 pg_dump creates an encrypted archive, the restore CLI runs real pg_restore, and assertions verify subject/note/audio IDs, relationships, Unicode text, and separately copied audio bytes after the original audio directory is removed. Wrong-key restore is rejected. Drill passed using the existing development tooling image with current source mounted read-only, inside an isolated PostgreSQL container. Audio is a separate directory backup, not included in pg_dump; this verifies the recovery procedure, not offsite replication or host-loss guarantees. Ruff passed.
Final PostgreSQL checkpoint verification: two passed, 26 deselected, one existing warning (8.66 seconds), including RECOVERY_REQUIRED history and migration preservation. Full backend suite is active against the current changes; no completion claimed.

13 October — B09 PostgreSQL snapshot verification: five export tests passed (23.45 seconds). Streaming begins a REPEATABLE READ snapshot, an independent writer then changes the subject and replaces its note, and export retains the original subject/note with consistent record counts. The committed later state is separately verified. Closing an unfinished stream returns the snapshot connection to the pool.

13 October — process-crash fixture alignment: the actual-exit test uses the shared engine on PostgreSQL and a disposable file database on SQLite because an exited process cannot reopen in-memory state. This documented exception is registered in the fixture guard. Dependency/process batch six passed; actual PostgreSQL process-exit regression one passed. Ruff passed.

13 October — full backend verification after fixes: 515 passed, eight PostgreSQL-only skips, three existing warnings, 242.46 seconds. This supersedes the previous failed full run. No backend failures remain in this batch.

13 October — B22/R13 Compose runtime: isolated project aria-review-20261013 uses separate ports 55434/8020/3120 and dedicated review volumes. Database health precedes migration; migration reaches 0025_workflow_checkpoint before backend startup. /ready reports database/schema OK and disabled providers accurately. Frontend initially exceeded 45 seconds compiling because automatic CSS source discovery reached generated files; explicit app/components/lib source registration resolves this and the first request returns HTTP 200 (15.0 seconds). Playwright's UI base URL can now be configured for external stacks. Full review regressions and an actual PostgreSQL-backed API/browser batch are running; results pending. The stack uses cached dependency images with current source/migrations mounted, so a newly built production image remains a separate check.

13 October — real integration follow-up: initial 32-test batch had 13 passes and 19 failures. Most UI failures entered sign-in before client handlers were ready; the PostgreSQL audio delete also failed on an existing progress FK, and personal-key storage was intentionally disabled in the initial review configuration. These were not treated as green results. AuthShell now disables server-rendered fields until hydration, sign-in reads named native FormData, header controls wait for hydration/auth/context readiness, and the expired-session notice uses a matching server/client initial render. Four real auth tests (including delayed application JavaScript) and three sign-out policy cases passed before the final full rerun. A public test-only encryption key enables BYO storage solely in the isolated review stack.

13 October — PostgreSQL audio delete fix: explicit SQL deletes progress children before the parent artifact, since the models lack an ORM relationship that would order unit-of-work deletes. Real PostgreSQL saved-progress deletion regression passed; file cleanup still occurs after commit. Current full backend and broader browser verification are running after this correction.

13 October — development reload and production parity: bounded Tailwind source scanning is active. Windows bind-mount notifications left old auth markup running, verified by comparing server output before/after restart. The final development setup uses Turbopack plus Compose native source synchronization and a dedicated `.next-compose` cache. A temporary route was created, edited, rendered with each value without restarting, and removed afterward; synchronization passed. Fresh frontend and production backend images built successfully. The fresh production backend reports /ready database/schema OK and generates a real WAV offline (107186 bytes, three measured seconds). Its eSpeak compatibility link no longer assumes x86 directory layout. Native Docker filesystem polling remains enabled for backend reload. Updated sample settings document LLM-only estimated budgets and no longer claim reset-on-restart or separate speech accounting. Final batches are pending.

14 October — current-change verification: working-tree diff contains 135 tracked files with 8119 additions/2211 removals ignoring end-of-line whitespace, plus additional staged/new paths. These counts include tests/configuration/docs, not 135 new product features. The previous review container had stale Learn source after newer edits. A fresh frontend image was built; SHA-256 comparison verified all 55 application/component/library/font source files match the checkout, with zero missing or mismatched files.

14 October — actual journey failure resolved: generated study notes start with a Markdown dash, which eSpeak parsed as an option when supplied as an argv value. Local speech now uses fixed --stdin arguments and explicit UTF-8 input. Normal, dash-prefixed and option-like regression cases plus lossless speech tests: 21 passed; Ruff passed. Real installed eSpeak generated WAV for dash-prefixed, option-like and Unicode input. The current results UI replaced the old Assessment Complete heading; journey now verifies Answer Review and the scored-answer summary. Current full learner journey passed (37.9 seconds; total 40.9 seconds), including note-to-audio playback and the post-audio screens. Previous full backend 516 passes and 41 review regressions remain historical results; a backend rerun is required after the speech change. No blanket all-features/completion claim is made.

14 October — connected daily learning flow: the learner's Done for today action saves a local-day, subject-scoped review with durable database uniqueness (migration 0026). It supports conversation-based LLM questions without notes and labelled deterministic recall fallback; conversation-only practice does not invent material-backed mastery. Daily results run the learner loop, create up to three next-day weak-concept tasks, close tracked automatic tasks on later supported evidence, and refresh roadmap ticks. Heatmap cells remain 13 by 13 pixels, including hover. Assessment history is newest-first with API pagination, preventing old 100-row history from hiding a new review.

Verification: full backend 525 passed/8 skipped; final focused SQLite batch 24 passed/1 PostgreSQL-only skip; PostgreSQL daily review/ownership/loop/provider/migration/concurrency batch six passed, followed by one passing large-history test. Full browser run 130 passed/six failed across 136 checks. All six failed checks passed subsequent targeted retests after the hydration fix and configurable landing URL correction; intermittent loading/animation timing failures remain a stress-test limitation. Final mobile run completed 20 navigation round trips, with 16.8 ms p95 frame gaps under 4x throttling and stable DOM/listener counts; heap growth and development runtime limit interpretation. TypeScript and changed-file lint passed. All 56 frontend application/component/library/font files match the review container. Details and separate enhancement priorities: docs/aria-connected-flow-verification-2026-10-14.md.

Live Groq verification remains unexecuted: automatic approval review rejected launching a key-enabled backend because it could transmit stored tutoring conversations to Groq. Main database deployment has not been upgraded by this isolated verification. No claim of a clean full browser run, live cloud-provider certification, or completed main-database deployment is made.
