# ARIA — combined backend, frontend, and product review

**Review date:** 5 October 2026  
**Target:** the current working tree, including the new `frontend-v2` and its FastAPI backend.  
**Purpose:** identify inconsistencies and defects first; give product opinions and enhancements separately afterward.

**Later verification:** see the [14 October connected learning report](aria-connected-flow-verification-2026-10-14.md) and [repair history](aria-review-fixes-2026-10-05.md) for implemented changes and current test evidence. The original findings below preserve the state reviewed on 5 October.

## Executive assessment

ARIA has a strong visual identity and a useful backend foundation: durable conversations, owner-scoped services, document retrieval, structured assessments, evidence tracking, revision scheduling, encrypted personal keys, and deployment tooling. The concept map can become its defining feature.

The main release risk is correctness across boundaries. A polished screen can currently show the wrong subject's work, report failed audio as ready, retain obsolete roadmap completion, or conceal unavailable AI configuration. The backend review also reproduced failures that the existing test suite misses. I would fix the P1 findings before broader learner use and improve the connections between existing features before adding a large new feature set.

**This is a review document, not a record of completed repairs.** The findings below remain open unless explicitly marked otherwise. No application code or tests were changed during this review. The earlier no-notes chat fix is included as completed historical work, with its remaining configuration requirement and missed test assertion disclosed.

## Review method, evidence, and limits

Backend review covered authentication/session/CSRF behavior; configuration and provider selection; study and conversation persistence; document ingestion, retrieval, and concepts; assessments and evidence; learner state/adaptation; notes and revision; roadmaps; planner/progress; audio/STT/storage; notification/email/push paths; orchestration/idempotency; export/deletion; scheduler/backups; migrations, deployment, and CI configuration. This is a broad source review with targeted runtime probes, not a claim that every branch was exercised.

The backend suite was run with the existing Python 3.12 integration environment and isolated SQLite test fixtures. Additional probes used a separate in-memory SQLite database with foreign keys enabled, synthetic accounts, and a fake TTS provider. They did not use or change the learner database. The source review did not print credentials or call live cloud models.

| Check | Result | What the result establishes |
|---|---|---|
| Full backend `pytest -q` | **316 passed, 1 failed**, 317 total; 193.82 seconds | Broad deterministic behavior passes; one stale assertion remains |
| Backend Ruff | **10 findings:** nine E501, one I001 | Backend lint is currently failing on formatting; these are not ten runtime failures |
| Foreign-key-enabled review probes | Confirmed chat deletion failure, wrong-parent assessment mutation, foreign associations, roadmap evidence problems, export identity loss, and retained audio file | Concrete failures beyond the ordinary suite |
| Earlier frontend typecheck and full-source ESLint | Passed | Static frontend checks at the preceding review |
| Earlier real-backend frontend integration run | **19 passed, 2 failed**, 21 total | One obsolete onboarding selector; one local TTS failure |
| Earlier visual enhancement verification | **20 browser checks passed** against an optimized build | Visual/interaction checks passed; does not negate the defects below |

The backend failure is [tests/test_rag_grounding.py:147](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/tests/test_rag_grounding.py:147>): it still expects “could not find enough relevant information” after the previous chat fix deliberately changed that response to explain missing LLM configuration. I missed that assertion in the earlier targeted verification. It needs updating; it is not evidence that the supported no-notes generation branch is broken.

PostgreSQL migration roundtrips, container startup, production traffic, real SMTP/push delivery, real microphone hardware, cloud STT/TTS, and live LLM quality were **not revalidated in this review**. CI contains PostgreSQL and restore checks, but their existence is not proof of a passing current CI run. No vulnerability-feed audit or penetration test was performed. Source-confirmed security findings identify concrete risky paths, not demonstrated compromise.

### Priority and evidence labels

- **P1:** fix before relying on or exposing the affected workflow.
- **P2:** important correctness, integration, operational, or usability repair.
- **P3:** polish/documentation alignment.
- **Probe confirmed:** reproduced in the isolated review environment.
- **Source confirmed:** a specific inspected code path establishes the issue; its full production consequence was not exercised.
- **Earlier browser/integration confirmed:** evidence carried forward from the frontend review, not a newly repeated browser check.

## Part I — backend inconsistencies and problems

### B01 — P1: Deleting a chat message can break subsequent sends

**Evidence: probe confirmed.** [backend/app/services/study.py:132](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/study.py:132>), [backend/app/services/memory.py:122](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/memory.py:122>), and the unique session-position constraint in [backend/app/db/models.py:384](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/db/models.py:384>).

`_next_position()` uses the number of remaining messages plus one. After two conversation turns occupy positions 1–4, deleting position 1 leaves three rows, so the next send tries to insert position 4 again. The retry repeats the same count and conflict. The probe received **HTTP 500** when sending after deleting the first message.

**Impact:** a normal privacy/editing action can make a conversation unusable; an LLM answer may already have been generated and charged before persistence fails.

**Repair:** allocate positions from `MAX(position)` rather than row count, retaining concurrency protection or a per-session sequence/lock. Test deletion at the beginning and middle, followed by another turn and concurrent sends. Define whether deleting one bubble also deletes its paired turn.

### B02 — P1: Related-object ownership and subject checks are missing in several writes

**Evidence: probe confirmed.** [backend/app/api/routes/roadmaps.py:29](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/api/routes/roadmaps.py:29>), [backend/app/services/roadmap.py:250](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/roadmap.py:250>), [backend/app/api/routes/notes.py:85](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/api/routes/notes.py:85>), and `backend/app/services/notes.py:75,136`.

The review reproduced all three cases:

1. A learner created a roadmap using **another learner's context ID**, receiving HTTP 201.
2. A learner created a note linked to **another learner's concept ID**, receiving HTTP 201.
3. A learner generated a note in subject B from their conversation in subject A, receiving HTTP 201.

Checking ownership of the destination context alone does not validate every referenced concept/session. Foreign keys prove that an ID exists, not that it belongs to this learner or subject. These probes did not demonstrate access to another learner's content. They do establish invalid associations, and cross-owner references can interfere with foreign-key-safe deletion of the referenced data.

**Repair:** resolve every referenced context, concept, session, deadline, and source through a shared owner-and-context validation helper before creating data or calling providers. Explicitly define whether cross-subject linking is supported; reject it wherever isolation is promised. Add cross-owner and same-owner/wrong-subject cases for each relationship, including deletion afterward.

### B03 — P1: An assessment request can return 404 after committing the mutation

**Evidence: probe confirmed for submission; source confirmed for answer saving.** `backend/app/api/routes/assessments.py:186,206`, particularly the relationship checks at lines 200 and 231; [backend/app/services/assessment.py:275](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/assessment.py:275>).

The route calls `save_answers()` or `submit_attempt()` before checking that the attempt belongs to the assessment in the URL. Those services commit changes. The probe submitted an attempt from assessment B through assessment A's URL: the response was **404**, but B's attempt was already **SUBMITTED**.

**Impact:** a rejected request can consume an attempt and record evaluation/evidence. The caller reasonably interprets 404 as no action taken. Same-owner checks do not prevent this inconsistency.

**Repair:** validate the attempt's assessment relationship before any writes. Bind idempotency replay to the requested attempt and request payload. Test that mismatched parent/child IDs leave answers, attempt status, evaluations, and evidence unchanged.

### B04 — P1: Roadmap completion is not reliably scoped or reversible

**Evidence: probe confirmed.** [backend/app/services/roadmap.py:170](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/roadmap.py:170>), especially lines 189–244.

The supported-concept query is owner-scoped but ignores `roadmap.context_id`. Matching accepts a shared stem/token in milestone text. A supported “Functions” concept from a different subject completed **two** milestones in a Python roadmap. The concept's confidence was 50, but the roadmap displayed **85** because it applies `max(85, best_confidence)`.

After the same learner state changed to NEEDS_REVIEW with confidence 0, the roadmap still reported **two completed milestones**. The unmatched branch only changes the reason of NOT_STARTED milestones; it never withdraws a previously supported completion. A single overlapping skill can also complete a multi-skill milestone, and stored prerequisites are not enforced by this completion logic.

**Impact:** the signature progress visualization can overstate what the learner understands, contradicting the evidence model and subject-isolation promise.

**Repair:** explicitly link milestone requirements to scoped concept IDs/evidence, define a completion rule for all required skills, derive confidence without an artificial floor, and recompute regressions/invalidation. Decide how context-free roadmaps are allowed to share evidence. Test matching names across subjects, partial coverage, prerequisite ordering, and evidence reversal.

### B05 — P1: Web-push destinations are unconstrained outbound targets

**Evidence: source confirmed; exploitation not attempted.** [backend/app/schemas/push.py:4](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/schemas/push.py:4>), `backend/app/services/push.py:22,69`, and [backend/app/api/routes/push.py:31](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/api/routes/push.py:31>).

Push registration accepts an arbitrary nonempty endpoint string. With VAPID configured, the sender passes that endpoint to `webpush()` without application-level scheme/host/private-address checks. This creates an SSRF risk: authenticated input can influence a server-side outbound destination. The precise reachability and exploitability depend on library behavior, valid push keys, and deployment egress controls.

**Repair:** validate HTTPS push-service destinations, reject credentials/private/loopback/link-local targets, control redirects and DNS resolution, and enforce outbound network restrictions. Add tests that reject local/private targets without contacting them. Keep real delivery validation separate from these rejection tests.

### B06 — P2: Cloud audio can silently omit most of an accepted source

**Evidence: source confirmed.** `backend/app/services/audio.py:33,80`; cloud providers in `backend/app/ai/providers.py:151,255`.

Audio conversion accepts sources up to 20,000 characters, but both cloud TTS implementations send only `text[:4000]`. The artifact retains the full text and can become READY even though its speech contains only the beginning. The returned duration is estimated from text length, not measured from the resulting audio.

**Impact:** a learner can believe an entire note or resource was converted and reviewed while most of it was never spoken. Joining overlapping resource chunks can additionally repeat text at chunk boundaries.

**Repair:** segment the complete source within provider limits and assemble the result, or enforce and clearly communicate a truthful conversion limit. Measure playback duration and preserve source offsets. Test a source whose distinctive ending occurs after character 4,000.

### B07 — P2: The audio queue can process an artifact that is already being generated

**Evidence: source confirmed.** `backend/app/services/audio.py:175,257`; [backend/app/jobs/scheduler.py:91](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/jobs/scheduler.py:91>).

In-request generation commits PROCESSING before calling TTS. The scheduler selects every PENDING/PROCESSING artifact with no lease, heartbeat, or stale-age condition. Its advisory lock excludes another scheduler job, but does not exclude a foreground generation request. A slow request can therefore be picked up again, paying for duplicate synthesis and racing to overwrite status/storage. Simultaneous foreground creation also has no atomic source-level claim.

**Repair:** use one durable job path with atomic claiming, an execution lease, retry limits, and stale-job recovery. Until then, restrict recovery to genuinely stale artifacts and coordinate it with foreground work. Test overlapping foreground/worker calls with a delayed provider.

### B08 — P2: Subject/account deletion and backups do not cover audio files consistently

**Evidence: probe confirmed for subject deletion; source confirmed for reset/backup.** [backend/app/services/data_management.py:309](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/data_management.py:309>), [backend/app/services/account.py:104](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/account.py:104>), [backend/app/services/audio.py:308](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/audio.py:308>), [backend/app/services/backup.py:36](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/backup.py:36>), and the separate `audiofiles` volume in [docker-compose.prod.yml](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/docker-compose.prod.yml>).

Deleting one audio item uses storage cleanup, but context deletion and learner reset directly delete database rows. The probe generated a file in a temporary audio directory, deleted its subject, and confirmed that the file **still existed** after its row was removed.

The scheduled backup captures PostgreSQL, while current audio bytes normally live in a separate filesystem volume. Restoring only that database does not restore those bytes. This does not mean the database backup itself is corrupt.

**Repair:** collect storage keys during deletion and perform reliable cleanup after commit, with an outbox/sweeper for failures. Include audio storage and the required encryption-key recovery procedure in disaster recovery, or document/test deliberate regeneration. Verify both row and byte lifecycle.

### B09 — P2: The “full export” loses identities and relationships and silently truncates

**Evidence: probe confirmed for note identity/context loss; source confirmed for other omissions/caps.** `backend/app/services/data_management.py:52,74,129,182`.

Notes, tasks, deadlines, conversations, resources, and concept summaries are flattened into collections with selected fields. Many omit their original ID and context ID. Meanwhile, other exported collections contain foreign IDs, so the export cannot reliably reconstruct those relationships. The probe confirmed that exported notes lacked both IDs and context associations.

The export also excludes original resource bytes and generally does not provide the full original resource record; chunk exports are not a replacement for the original document. Collections are capped at 5,000 rows and messages at 500 per session without explicit truncation metadata or continuation support.

**Repair:** define whether this is a readable summary or a complete portable export. For the latter, include stable IDs, context relationships, schema version, explicit omissions/truncation metadata, and streaming/paginated export for large accounts. Keep credential ciphertext excluded. Validate relational completeness and an import/reconstruction roundtrip.

### B10 — P2: Chat citations can include material the model did not receive

**Evidence: source confirmed.** `backend/app/services/study.py:238,353`, [backend/app/services/context_assembly.py:64](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/context_assembly.py:64>), and [backend/app/api/routes/study.py:139](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/api/routes/study.py:139>).

Retrieval returns the highest-ranked chunks even when their scores are zero or negative. Prompt construction drops nonpositive chunks and can also deduplicate/truncate them to fit its context budget. The response and persisted references still serialize the original retrieval list.

**Impact:** an unrelated question may be answered from general knowledge while the interface shows document citations. It can also cite a chunk that was excluded from the final prompt. That weakens the document/general-knowledge distinction central to ARIA's tutor.

**Repair:** build an explicit final evidence package and return references only to excerpts actually included. Mark the answer mode as general, document-grounded, or mixed, and avoid implying that a reference proves every statement. Test unrelated queries, zero scores, duplicate chunks, and context-budget truncation.

### B11 — P2: Conversation history loses fallback status and can hide newer messages

**Evidence: source confirmed.** [backend/app/schemas/study.py:49](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/schemas/study.py:49>), [backend/app/api/routes/study.py:61](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/api/routes/study.py:61>), `backend/app/services/study.py:82,116`.

The immediate send response includes `fallback_used`; stored conversation messages and their GET response do not. The frontend accepts this optional field when loading history, but the backend cannot supply it. Reopening the conversation therefore loses the structured distinction between a generated answer and a deterministic/provider-failure fallback.

Sessions are listed oldest-first with a 100-row cap, and messages oldest-first with a 200-row cap. Without pagination, the newest sessions or later conversation turns become inaccessible through these list endpoints.

**Repair:** persist answer mode/fallback reason and provider metadata without secrets. Add cursor pagination, load the most recent page by default, and allow older history to be fetched. Test reload parity and conversations exceeding the current limits.

### B12 — P2: “Key configured” and “feature available” mean different things across the app

**Evidence: source confirmed; local missing-key state confirmed in the preceding fix.** `backend/app/services/llm_keys.py:168,189`, [backend/app/ai/registry.py:24](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/ai/registry.py:24>), `backend/app/services/audio.py:36,65`, and [backend/app/api/routes/health.py:50](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/api/routes/health.py:50>).

Personal-key status reports configured when a row exists, even if it cannot be decrypted. Credential resolution silently falls back to the global key or no provider. The readiness endpoint reports only whether a global key is present, so a personal-key-only setup still appears “not configured.” Chat/assessment/notes/roadmaps resolve learner credentials, while TTS/STT use only deployment credentials.

**Impact:** saving a personal Groq key can enable chat but leave voice unavailable; a configured-looking saved key may be unusable after encryption-key loss/rotation. The UI lacks a reliable capability contract to explain these differences.

**Repair:** expose authenticated capability/status information: usable personal/global LLM, permitted models, transcription, TTS, embeddings, and actionable setup reasons. Distinguish presence from decryptability and successful provider validation. Decide explicitly whether personal keys should fund audio; do not assume the same key automatically enables every feature.

**Earlier fix status:** no-notes tutoring is supported; empty subjects now skip embeddings and the fallback explains missing configuration. Local personal-key encryption was enabled. At that check there was no global Groq key and no saved personal key; live answers require a valid key. This review did not reconfigure providers.

### B13 — P2: With notes present, an embedding failure still prevents general tutoring

**Evidence: source confirmed.** [backend/app/services/study.py:392–416](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/study.py:392>).

The earlier fix avoids embeddings for an empty subject. If ready notes exist and retrieval/embedding fails, `answer_question()` returns immediately, before calling a separately available LLM. Its fallback tells the learner to review cited excerpts while returning an empty source list.

**Repair:** classify retrieval failure separately from LLM failure. Use lexical retrieval when semantic retrieval fails; where appropriate, offer a clearly labeled general-knowledge answer with no invented document claims. Preserve a strict document-only mode for questions that require the source. Test a failing embedding endpoint with a healthy LLM.

### B14 — P2: Public readiness leaks failure detail and overstates capability readiness

**Evidence: source confirmed.** [backend/app/api/routes/health.py:38](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/api/routes/health.py:38>), `deploy/caddy/Caddyfile:29`, and [backend/app/security/secrets.py:11](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/security/secrets.py:11>).

`/ready` is intentionally publicly proxied. On database failure it returns the raw exception string, which can expose infrastructure details. On success it checks `SELECT 1`, not schema/migration readiness, accounting tables, or storage. A nonempty key is labeled configured without validating provider access. Session-secret validation occurs when requested, rather than being part of this readiness check, so bypassing the external preflight can yield a ready-looking deployment with unusable authentication.

**Repair:** return a sanitized public status; retain restricted operator diagnostics with a request ID. Separate process liveness, core database/schema readiness, and optional capability readiness. Validate required production configuration at startup and keep the existing preflight as an additional check. Avoid live paid provider calls on every health poll.

### B15 — P2: Error sanitization is inconsistent across API responses, logs, and audit data

**Evidence: source confirmed.** [backend/app/services/resource_ingestion.py:86](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/resource_ingestion.py:86>), [backend/app/services/audio.py:222](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/audio.py:222>), `backend/app/ai/providers.py:296,469,508`, and [backend/app/services/orchestration.py:155](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/orchestration.py:155>).

Chat responses deliberately use generic errors, but ingestion/audio persist raw `str(exc)` in learner-visible `error_detail`. TTS chains concatenate provider exception text; LLM failures log full exceptions; workflow task/audit records also store exception text. The logging setup does not implement a shared redaction filter. Depending on the provider exception, this may expose request text, credentials, account identifiers, or infrastructure details. No real credential leak was reproduced in this review.

**Repair:** classify provider errors into safe codes/messages, redact sensitive fields before logging/storage, and keep protected diagnostics separate from learner-visible state. Test with synthetic secret markers and provider responses containing prompt text; assert absence across HTTP payloads, persisted error fields, and logs.

### B16 — P2: Roadmap input validation and fallback content do not match the product contract

**Evidence: source confirmed.** [backend/app/schemas/roadmap.py:39](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/schemas/roadmap.py:39>), [backend/app/db/models.py:482](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/db/models.py:482>), [backend/app/api/routes/roadmaps.py:29](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/api/routes/roadmaps.py:29>), and [backend/app/services/roadmap.py:30](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/roadmap.py:30>).

Goal, level, and target date are unrestricted strings in the request, despite database limits of 255/64/64 characters. Target date is not parsed as a date. The AI-generating route has no rate-limit dependency equivalent to chat/assessment/notes. SQLite does not enforce VARCHAR lengths like PostgreSQL, so local tests can miss production failures.

The fallback curriculum is programming-specific for every goal: syntax, variables, concurrency, production security, and deployment. It can therefore generate an inappropriate curriculum for history, biology, or language learning, without a structured fallback indicator.

**Repair:** bound and validate inputs before provider calls, apply the shared generation limits, and constrain generated milestone fields too. Use subject-appropriate templates or an honest starter outline, and expose generation mode/failure reason. Test a nonprogramming goal and overlength inputs against PostgreSQL.

### B17 — P2: AI budgets are safeguards rather than guaranteed spending caps

**Evidence: source confirmed.** [backend/app/ai/budget.py:188](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/ai/budget.py:188>), `backend/app/ai/providers.py:305,432,475`, and the TTS/STT/embedding provider paths.

Global accounting is recorded after generation. Multiple requests can pass the pre-call check before spend crosses the cap. Learner accounting reserves estimated input plus a completion floor, but generation does not pass an explicit output-token limit tied to that reservation. Actual output can exceed it; character-based token estimates are also not guaranteed bounds. Audio and embeddings use separate direct HTTP providers and are not covered by the LLM token accounting path.

**Repair:** describe the current limits truthfully. If a hard cap is required, atomically reserve conservative request cost, impose output limits, settle actual usage, and account for relevant audio/embedding charges separately. Include global and per-learner concurrency, failed calls, missing usage metadata, and refunds in verification. Do not infer a pricing guarantee from this review.

### B18 — P2: Idempotency reservations have race and payload-reuse gaps

**Evidence: source confirmed; no concurrent production reproduction.** `backend/app/services/idempotency.py:36,173`, [backend/app/api/routes/orchestration.py:108](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/api/routes/orchestration.py:108>), and [backend/app/services/assessment.py:275](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/assessment.py:275>).

Initial reservation insertion uses a unique constraint, but reclaiming an expired reservation and converting a completed row into a new reservation use read-then-update without a lock or conditional ownership claim. Two callers can both be told to proceed. A completed result can also appear after the route's replay check but before `reserve()`, which currently clears completed responses. Keys are not bound to a payload fingerprint, and assessment replay is looked up by owner/key before validating the requested attempt.

**Repair:** use atomic compare-and-set/row locking for claims, return completed replay results instead of clearing them, and bind owner/scope/key to a request fingerprint. Reject conflicting reuse explicitly. Verify concurrent reclaim, completion between lookup/reserve, same key with different payloads, and different attempts using one key.

### B19 — P2: Workflow retries do not reliably recover database failures

**Evidence: source confirmed.** `backend/app/services/orchestration.py:155,274`, [backend/app/api/routes/orchestration.py:49](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/api/routes/orchestration.py:49>).

The retry handler catches all exceptions but then commits error status on the same session without rolling back first. A flush/commit failure can leave that session unusable, making error recording and the next retry fail. Domain services can commit their work before task/audit persistence, so retrying the entire handler after a later failure can duplicate effects. The payload is an unstructured dict; malformed context UUIDs can fail while advancing a workflow outside the step-level error handling.

**Repair:** validate each workflow's payload up front, roll back failed transactions before recording status, and make each consequential step idempotent. Define workflow recovery checkpoints and distinguish domain work from status/audit persistence. Test injected database failure after a committed domain action and malformed payloads; verify the workflow has a truthful terminal/recoverable state.

### B20 — P2: Failed resource reprocessing can discard previously usable retrieval data

**Evidence: source confirmed.** `backend/app/services/resource_ingestion.py:221,267`.

Reprocessing deletes existing chunks and concept links, commits PROCESSING, and only then extracts/embeds the replacement. A temporary extraction/embedding failure leaves the resource FAILED with its old searchable representation already removed. Replacement commits new raw/text content before successful processing as well. There is no generation/version claim to prevent overlapping reprocess requests from publishing competing chunk sets.

**Repair:** build a new version separately and atomically switch the active version after successful validation. Preserve the last usable version and distinguish “replacement failed” from “no usable material.” Coordinate concurrent replacement/retry and make concept associations version-aware. Test a healthy resource followed by provider failure and overlapping replacements.

### B21 — P2: Deterministic quizzes can have several factually correct options

**Evidence: source confirmed.** `backend/app/assessment/mcq.py:78,128`.

The fallback takes one sentence as the correct option and three other sentences from the same material as distractors, then asks “which of the following statements is correct?” Those other sentences can all be true. Deterministic scoring can be mechanically consistent while the question itself is ambiguous.

**Repair:** generate a question with one demonstrably correct answer and relevant, false alternatives, or label a different exercise that actually tests source identification. Validate pedagogical quality as well as JSON/schema and scoring. Include a four-true-facts fixture and human-reviewed questions; do not treat synthetic generation as equivalent to a reliable assessment of understanding.

### B22 — P2: Development and production configuration do not expose the same capabilities

**Evidence: source confirmed.** [docker-compose.yml:23](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/docker-compose.yml:23>), [docker-compose.prod.yml:85](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/docker-compose.prod.yml:85>), [backend/app/core/config.py:27](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/core/config.py:27>), and [frontend-v2/app/app/account/page.tsx:19](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/frontend-v2/app/app/account/page.tsx:19>).

The development backend forwards the global Groq key/model but not personal-key encryption, TTS/STT, embedding, SMTP, or push configuration. The container does not receive the host `.env` merely because Compose reads it for substitutions. A host-native setup can therefore work differently from the documented development stack. Development audio storage also lacks the dedicated mounted volume used in production.

The backend default model allowlist, production Compose default, and frontend hard-coded options differ. Frontend preview port 3101 also depends on CORS overrides rather than the default port-3000 configuration.

**Repair:** publish one explicit local capability configuration and startup/readiness command; forward the intended settings and persist development audio deliberately. Retrieve permitted models/capabilities from the API. Preserve the production same-origin proxy contract and test the supported development modes separately.

### B23 — P2: Concept synchronization and learner-state reads will grow expensive

**Evidence: source confirmed; no new load benchmark.** `backend/app/services/concepts.py:16,58,86`, [backend/app/services/learner_state.py:68](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/learner_state.py:68>), and [backend/app/services/roadmap.py:302](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/roadmap.py:302>).

Concept synchronization loads all ready chunks and can regenerate concepts on every assessment creation. Its structured extraction prompt includes every chunk's excerpt without an overall prompt budget, while synchronization deletes and rebuilds links. Learner-state recomputation queries evidence separately for each concept; roadmap lists rescan supported concepts and commit separately per roadmap. These paths can add latency/cost as material and history grow. The review does not establish a measured production threshold.

**Repair:** trigger extraction from resource-version changes, cache/version the extraction result, bound prompts, and batch evidence/milestone calculations. Normalize/deduplicate concept identities before insertion and enforce intended uniqueness. Measure representative large subjects and concurrent usage before adding infrastructure solely for scaling.

### B24 — P2: The current backend quality gates are not clean

**Evidence: fresh tool results.** [tests/test_rag_grounding.py:147](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/tests/test_rag_grounding.py:147>), [backend/app/schemas/roadmap.py:1](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/schemas/roadmap.py:1>), and the Ruff locations listed below.

The full suite has one stale assertion introduced by the previous response-wording change. Backend-only Ruff has nine long-line errors and one import-order error. CI explicitly runs Ruff and pytest, so these current changes should not be described as ready to pass its backend job.

Ruff locations: `ai/prompts.py:36,40,88,93`; `core/config.py:27`; `schemas/roadmap.py:1`; `services/context_assembly.py:49,50,51,54` (all under `backend/app`).

**Repair:** update the obsolete assertion to the intended missing-key contract, resolve formatting, and run the complete required checks. Add regression coverage for the reproduced findings; ordinary happy-path and owner checks currently miss these related-object, deletion, and failure-order cases. Avoid replacing meaningful assertions with permissive ones just to obtain a green result.

## Part II — frontend inconsistencies and problems

The complete frontend findings from the preceding review are included below. Their R1–R14 identifiers are retained so they can be tracked alongside B01–B24. Evidence dates and limitations remain explicit.

Priority: P1 = fix before relying on the affected workflow; P2 = important correctness/usability improvement; P3 = polish or documentation drift. “Browser confirmed” and “integration confirmed” describe observations; “source confirmed” identifies a concrete code path that was inspected but not exercised end to end.

### R1 — P1: The microphone feature is blocked by the frontend's own policy

**Evidence:** [frontend-v2/next.config.ts:26](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/frontend-v2/next.config.ts:26>); voice capture in [frontend-v2/app/app/learn/page.tsx:217](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/frontend-v2/app/app/learn/page.tsx:217>). Browser confirmed: `document.featurePolicy.allowsFeature('microphone')` returned false on the served page.

The application offers Speak question and calls `getUserMedia`, while the response header sets `microphone=()`. This prevents voice capture even when the browser and hardware support it. Mocking getUserMedia in a test bypasses this real policy restriction.

**Recommendation:** allow the microphone for the application origin, retain the other permission restrictions, and test the actual served policy. Then validate permission denial, recording, transcription failure, and stream cleanup with real hardware separately.

### R2 — P1: Subject switches can show and operate on the previous subject's data

**Evidence:** [frontend-v2/app/app/planner/page.tsx:75](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/frontend-v2/app/app/planner/page.tsx:75>), particularly `setTasks(t)` at line 83. Browser confirmed with delayed responses: switch from subject A to B, observe B's task, then release A's response; A's task replaces it while the active-context selector still says B.

The effect's cancelled flag guards errors/finalization, but the load function itself updates state without a request/context guard. An old response can therefore overwrite current data. A learner could complete or delete the wrong subject's task while trusting the current header.

Related source risks exist in Audio, Assessments, and Roadmaps. The assessment screen also retains its active attempt and review state when the context changes; follow-up adaptation/retest calls use the current context rather than a captured attempt context. Dashboard, Materials, and Map have stronger context isolation. Learn guards message responses, but its session-list loader still updates state without a request version; that remaining source risk should use the same isolation pattern.

**Recommendation:** apply one subject-isolation pattern everywhere: context-keyed workspaces or request versions plus cancellation inside data loaders. Define what happens when a learner switches subjects during an assessment; retain a correctly scoped draft or ask them to leave the attempt explicitly. Add delayed-response and mid-attempt context-switch coverage.

### R3 — P1: Failed audio generation is announced as success

**Evidence:** [frontend-v2/app/app/audio/page.tsx:119–140](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/frontend-v2/app/app/audio/page.tsx:119>); backend generation returns a FAILED artifact in [backend/app/services/audio.py:222](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/audio.py:222>). Integration confirmed: the artifact displayed `FAILED · 0:07`, while the frontend success path unconditionally calls `toast('Audio ready.')`.

HTTP success means the artifact record was returned, not that synthesis succeeded. The client also invents a duration from text length when duration is absent, including for failed generation, and offers playback without checking READY.

The observed local cause was `LocalTTSProvider` COM access denied. The UI bug remains applicable to any provider/storage failure that produces a FAILED artifact.

**Recommendation:** branch on artifact status. Show ready/play controls only for READY, processing feedback only for actual processing, and a readable failure/retry state for FAILED. Keep unknown duration unknown, or explicitly label an estimate. Check provider readiness independently of HTTP/database health.

### R4 — P1: Failed sign-out can appear successful while the session remains valid

**Evidence:** [frontend-v2/components/auth-provider.tsx:46–52](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/frontend-v2/components/auth-provider.tsx:46>), [frontend-v2/components/app-shell.tsx:340](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/frontend-v2/components/app-shell.tsx:340>), and the cookie-revoking backend sign-out route.

Source confirmed: signout catches every request failure, clears the in-memory user, and resolves successfully. The shell then navigates home. If the backend did not receive/revoke the session, the HttpOnly session cookie remains valid and refreshing can restore authentication. The ordinary successful sign-out integration case passes; the failure path is not covered.

**Recommendation:** distinguish successful server logout from an interrupted request. Do not claim the session was revoked when it was not. Offer retry or an explicit offline/local-only outcome, and cover network failure plus subsequent refresh.

### R5 — P2: Anonymous visitors can enter workspace routes and get stuck loading

**Evidence:** `frontend-v2/components/context-guard.tsx:21,38`; Audio's effect returns immediately without a context. Browser confirmed: an anonymous visit to `/app/audio` remained on that URL with the workspace shell and “your audio studio…” loading content.

This is a route-state problem, not a demonstrated bypass of backend authorization. The guard handles authenticated users without a subject but deliberately does nothing for unauthenticated visitors. Several screens require a context to finish loading.

**Recommendation:** once authentication resolves, send unauthenticated workspace visitors to sign-in with a return destination. Preserve a real authentication/network-error state instead of treating every failure to load the current user as ordinary anonymous access.

### R6 — P2: Overlapping toasts leak notifications and repeating timers

**Evidence:** [frontend-v2/lib/toast.ts:31–35](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/frontend-v2/lib/toast.ts:31>). Browser confirmed: emit two toasts, wait three seconds; the first toast remains after the second disappears.

The interval returns whenever its captured id is not the latest global counter. Older intervals then neither remove their toast nor clear themselves. They keep waking for the lifetime of the page. Every toast also uses a success icon, including failure messages, and the container lacks a live-region announcement.

**Recommendation:** give each toast its own finite timeout and lifecycle, independent of newer toasts. Support success/error/info semantics and accessible announcements. Test overlapping messages, not just one toast at a time.

### R7 — P2: Dialog and popover keyboard behavior is inconsistent

**Evidence:** [frontend-v2/components/confirm.tsx:22–30](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/frontend-v2/components/confirm.tsx:22>); modal markup in Materials, Planner, Audio, and Assessments. Browser confirmed: Tab escapes an open confirmation dialog.

The confirmation component focuses Cancel and handles Escape, but has no focus trap, background inertness, or explicit focus restoration. Several create dialogs are plain divs without dialog semantics. Palette settings also has less complete dismissal/focus handling than the upgraded notification/profile popovers.

**Recommendation:** reuse an accessible dialog primitive across all modals. Trap focus while open, restore the trigger, label the dialog, and handle Escape/backdrop consistently. Use the same popover interaction rules for palette settings.

### R8 — P2: Loaded fonts are not being applied through the shared tokens

**Evidence:** [frontend-v2/app/globals.css:252–253](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/frontend-v2/app/globals.css:252>), [frontend-v2/app/layout.tsx:34](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/frontend-v2/app/layout.tsx:34>). Browser confirmed: the body's local-font variable contains Jakarta, but root `--font-sans` resolves empty; body and concept nodes use the system font stack.

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

- Account offers two hard-coded model options (`account/page.tsx:19`), while backend configuration allows more ([backend/app/core/config.py:27](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/core/config.py:27>)). A saved model outside those options cannot be represented faithfully by the select.
- `tests/auth.spec.ts:28` expects an “onboarding” heading that was renamed; the current flow reaches the correct onboarding URL. Update the assertion to the user-visible heading.
- `tests/learning-agent-features.spec.ts:4` writes screenshots to a developer-specific absolute directory outside this workspace. Use Playwright's output paths.
- Microphone tests replace getUserMedia/MediaRecorder, so they can pass despite the real permissions policy blocking capture. Add a policy/capability check rather than interpreting a mocked transcription path as proof of working voice.
- Frontend defaults to API port 8000; default backend CORS only permits frontend port 3000. The current port-3101 preview works because the backend was started with explicit overrides. The earlier network error was a missing backend, not an invalid account. A repeatable local startup/readiness check is still needed.

**Recommendation:** centralize capability/model configuration, make test artifacts portable, and document one reliable startup command. Treat API reachability, database readiness, and provider readiness as different checks.

### R14 — P3: Theme and product copy do not always match the implemented behavior

- Theme documentation calls dark mode the default, while layout/provider default to light Aurora. Decide which rule is current and align both.
- Palette accessibility text says “Midnight Aurora” although Aurora declares `color-scheme: light`.
- Landing promises a 52-week heatmap (`app/page.tsx:16`); backend uses 182 days ([backend/app/services/progress.py:36](<C:/Users/Divya Tejaswi/OneDrive/Pictures/ドキュメント/Aria_v3/backend/app/services/progress.py:36>)), and progress fallback copy says 26 weeks.
- Roadmap empty-state copy uses implementation language such as “isolated curriculum tree.” Learners would benefit from a plain explanation of what they can do next.

**Recommendation:** audit product claims, labels, defaults, and empty-state wording against the actual contracts. These should be corrected rather than solved with extra animation.

## Part III — cross-system integration assessment

| Workflow | Current strength | Main unresolved boundary |
|---|---|---|
| Sign-in/session | Cookie sessions, CSRF, revocation, ordinary integration tests | Local startup/CORS drift; false sign-out success; anonymous workspace handling |
| Tutor with/without notes | Both modes implemented; per-owner LLM selection; durable turns | Actual key/capability setup; deletion numbering; source provenance; fallback metadata/history |
| Documents/concepts | Bounded binary upload, OCR off the event loop, deterministic retrieval fallback | Destructive retry/versioning; repeated extraction; unbounded extraction prompt; excerpt/navigation limits |
| Assessments/adaptation | Server-side scoring, structured output validation, durable evidence | Parent validation after mutation; related IDs; ambiguous fallback quiz; stale frontend attempt context |
| Map/roadmap | Distinctive frontend graph and evidence-backed concept state foundation | Roadmap completion does not reliably reflect scoped, current evidence; generic fallback curriculum |
| Audio/voice | Provider interfaces, failure artifact status, stored playback progress | Microphone policy; private versus global key capability; silent truncation; queue claim; failed-success UI; storage lifecycle |
| Planner/progress | Useful reminders, timezone-aware progress, separation of activity and mastery in code | Subject response races; contract/copy drift; truthful qualifying activity; shared notification behavior |
| Data/privacy | Owner scoping, export endpoint, encrypted keys, deletion services | Cross-owner related links; incomplete export; retained audio bytes; unredacted exception paths |
| Deployment/operations | Migrations, proxy, rate-limit options, backup and CI tooling | Current failed quality gates; sanitized/schema-aware readiness; capability/config parity; storage recovery |

HTTP 200/201 is not enough to establish that AI generation, processing, or delivery succeeded. Frontend state should use the domain result and a shared capability/error contract. Likewise, a 404/422 should not be emitted after a consequential mutation has already committed.

## Part IV — overall opinion and enhancements (separate from defects)

### Overall opinion

ARIA is a promising learning companion with a coherent visual direction and more useful underlying functionality than its current reliability suggests. The separation of UI, routes, domain services, provider interfaces, and ownership logic is worth keeping. Server-side evaluation and evidence tracking give it a foundation for meaningful adaptation rather than only an attractive chat screen.

The backend's “agents” are currently thin workflow handlers over those services. That is a reasonable architecture; it should not be marketed as an independently improving model. The self-loop mainly recomputes evidence/state and adapts prompts to recent history. Stronger persistent learning personalization would need explicit learner preferences, tested adaptation policies, and evaluation of whether explanations actually help.

My priority would be a trustworthy, connected learning loop: **choose a goal → learn from material or general knowledge → practice a specific concept → review evidence → get the next useful action**. Existing screens already cover much of this. The opportunity is to carry intent and verified state between them.

### Theme, onboarding, and animation direction

Keep the current celestial learning direction and refine it. The existing theme is a good foundation; “perfect” would overstate its typography, dense-label readability, and control consistency. Fix font tokens, hierarchy, spacing, modal behavior, and failure states before deciding on a full theme replacement.

Onboarding does not need every showcase animation. Keep its current small number of choices, explain that notes are optional for chat, and surface AI setup only when needed. A short constellation introduction and calm step transitions can add character without delaying entry. Offer optional guidance into the first learning session instead of extending the form into a long wizard.

Use Anime.js for occasional coordinated SVG/path sequences and milestone moments; use Motion for component/layout transitions and CSS for basic feedback. Preserve reduced motion, visibility pauses, cleanup, and quiet reading surfaces. A mastery celebration should follow verified evidence; B04 must be repaired before its visuals communicate certainty.

### Enhancement proposals in value order

| Enhancement | Why it matters | Suggested first implementation |
|---|---|---|
| **Concept-scoped Learn/Practice/Review** | Preserves the learner's intent and connects map, tutor, assessment, and sources | Carry context/concept/source IDs through navigation; show the selected scope and a targeted practice action |
| **Capability/setup center** | Prevents “network error,” missing-key, and unavailable-voice confusion | Show safe status for LLM, allowed models, transcription, synthesis, embeddings, and email; give the next setup/retry action |
| **Actionable session recap** | Turns a chat into a learning outcome | Key ideas, questions still open, source links, and one next action; distinguish generated suggestions from assessed mastery |
| **Evidence-based progress explanation** | Makes the living universe trustworthy | Explain which assessment/evidence changed a concept or milestone; show reassessment and invalidation rather than hiding regression |
| **Optional first-session guided path** | Helps newcomers experience value quickly | Topic → optional material/key setup → explanation → short practice → visible evidence update; allow skipping |
| **Source reader with excerpt navigation** | Makes grounding inspectable | Open the exact cited excerpt, highlight it, preserve reading position, and return to the conversation |
| **Unified search** | Reduces navigation between separate tools | Search subjects, concepts, notes, materials, and saved conversations with typed results and scoped access |
| **Study preferences that affect explanations** | Makes personalization observable | Persist preferred detail, examples, language, and accessibility choices; show and allow editing the preferences used |
| **Reliable long-running job experience** | Makes audio/OCR/generated work understandable | Durable job status, retry/cancel where supported, safe failure reasons, and completion notifications; do not simulate progress |
| **Exam-focused next-action view** | Connects current planner/revision/adaptation features | Combine upcoming deadline, weak concepts, revision due, and realistically available study time |

Spaced revision, assessments, reminders, badges, audio, and roadmaps already exist. Improve their reliability and connections before building duplicate systems. More permanent particles, sound effects, 3D scenes, and many additional dashboards are lower-value investments at this point.

### Backend design improvements supporting those enhancements

- Centralize relationship validation and keep consequential writes within an explicit transaction boundary. Perform parent/owner/context checks before provider calls and mutations.
- Version resources, concept extraction, prompts, and generated artifacts. Preserve provenance and the last usable result during failed regeneration.
- Standardize safe domain errors and capability responses; keep learner-facing messaging separate from protected diagnostics.
- Make asynchronous work durable before expanding audio/OCR features. Use atomic claims, idempotent steps, explicit retry rules, and recoverable workflow states.
- Define complete data portability and deletion behavior across both the database and file storage. Exercise restore with representative relationships and external artifacts.
- Add evidence-quality evaluation for tutor answers, concept extraction, and quiz validity. Correct schemas and passing scoring tests alone do not establish learning quality.
- Measure large-subject performance before choosing caching, an external queue, or additional services. The current service structure can evolve without a wholesale rewrite.

## Part V — combined action plan and acceptance criteria

### Release 1: Correctness and access boundaries

**Address:** B01–B05, frontend R1–R4; include related-object validation everywhere affected.

**Acceptance:** deleting messages does not break chat; wrong parent IDs cause no mutation; foreign relationships are rejected; roadmap completion stays within its intended evidence scope and can regress; push destinations cannot reach disallowed networks; microphone policy permits the intended origin; delayed subject responses cannot overwrite current work; failed synthesis/logout are reported truthfully.

### Release 2: Integration truthfulness and recovery

**Address:** B06–B16, B20–B22; frontend R5, R9–R13.

**Acceptance:** full accepted audio text is spoken or limits are explicit; one generation claim per artifact; deleted data includes stored bytes; exports retain IDs/context relationships and announce omissions; displayed citations match the final evidence package; answer mode survives reload; history is pageable; capability setup is accurate; failed retrieval/processing has a safe, useful recovery path; readiness/errors reveal no secrets; nonprogramming goals receive appropriate roadmap behavior.

### Release 3: Shared quality and operational controls

**Address:** B17–B19, B23–B24; frontend R6–R8 and R14.

**Acceptance:** retry/idempotency concurrency is verified; failed DB sessions recover correctly; spending controls have documented/tested guarantees; extraction prompts and costly reads are bounded; required backend/frontend checks pass; notifications clean up independently; dialogs support keyboard focus; computed typography and product claims match implementation. Repeat PostgreSQL migration/restore and a configured-provider smoke test before production sign-off.

### Release 4: Connected learning and restrained delight

**Build:** concept-scoped navigation/practice, source reader, recap, progress explanation, optional guided first session, and purposeful milestone animation.

**Acceptance:** a learner can follow one coherent learning journey with retained subject/concept/source scope, understand why progress changed, recover from failed capabilities, and complete it with keyboard/reduced-motion settings. Evaluate learning utility as well as visual polish.

### Recommended regression matrix

| Scenario | Required observation |
|---|---|
| Two owners and two subjects with overlapping concept names | No foreign links or unintended progress transfer |
| Wrong assessment ID with a valid owned attempt | Rejection leaves persisted state unchanged |
| Delete first/middle chat bubble, then send | New turn persists with unique ordering |
| LLM absent, personal key unusable, embedding down, model error | Distinct truthful states; no invented sources or exposed secrets |
| Concurrent generation, retry, or idempotency reclaim | One claimed effect or explicit conflict/replay |
| Audio ending after character 4,000 | Complete accepted output, or a clearly stated limit |
| Subject/reset deletion and restore | Database relationships and external byte lifecycle verified |
| More than 100 sessions/200 messages or export cap | New history remains reachable; truncation is explicit |
| Slow subject A response after switching to B | B's data and actions stay scoped to B |
| Real microphone policy and denied permission | Supported recording or readable recovery; stream cleanup |
| Two simultaneous toasts and keyboard modal use | Both toasts expire; focus stays in the dialog and returns correctly |
| Nonprogramming goal and invalid dates/oversized input | Appropriate fallback or safe validation before cost/write |

## Conclusion

Keep ARIA's visual identity and service architecture. The strongest next release is one that makes its existing learning features correct, explainable, and connected. Address the reproduced failures and shared reliability gaps first, then make the concept-centered learning journey the source of its “wow” effect.
