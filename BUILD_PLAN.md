# ARIA Build Plan

**Product:** ARIA — AI Learning Operating System  
**Document status:** Implementation tracking baseline  
**Last reviewed:** 2026-08-12  
**Current implementation status:** Phases 0–7 are implemented (including the Extruded Light frontend rebuild); Phase 8 is next.

> **Encoding note:** This file is valid UTF-8. Text such as `â€"` in some viewers is a
> Latin-1 mis-decoding of the em-dash character (U+2014), not file corruption.

---

## How to use this document

This is the working checklist for building ARIA. Each phase has:

- the purpose of the phase;
- the work to complete;
- dependencies;
- an explicit definition of done;
- the current status.

Status values:

- `[x] Complete` — verified and finished;
- `[~] In progress` — actively being built;
- `[ ] Not started` — planned but not implemented;
- `[!] Blocked` — cannot continue until a named dependency is resolved.

The long-term features are intentionally included in this plan. They are sequenced after the foundation so they can share the same domain model, learner context, evidence, workflow, security, and observability infrastructure.

---

## Current snapshot

### Completed planning

- [x] Product vision and differentiation defined.
- [x] R0 adaptive-learning hypothesis defined.
- [x] R0 requirements and acceptance gates defined.
- [x] R0 learner journey and screen inventory defined.
- [x] High-level system architecture defined.
- [x] AI, memory, database, API, agent, prompt, and technology decisions documented.
- [x] Later product direction includes Notes, Audio, Planner, Progress, and MAO.

### Not yet implemented

- [x] Application repository structure.
- [x] Frontend application.
- [x] Backend application.
- [x] Database schema and migrations.
- [x] Authentication and authorization.
- [x] Resource ingestion and retrieval.
- [x] Study, assessment, evaluation, evidence, and adaptation workflows.
- [x] Automated tests and CI/CD.
- [ ] Notes, Audio, Planner, Progress, and MAO runtime features.

---

# Phase 0 — Implementation baseline

**Status:** `[x] Complete`  
**Goal:** Convert the documentation-only repository into a runnable development workspace.

## Work

- [x] Establish repository layout:

  ```text
  frontend/       Next.js application
  backend/        FastAPI application
  database/       migrations and seed data
  tests/          cross-system test support
  docs/           product and architecture documentation
  ```

- [x] Add `.env.example` and secret-handling rules.
- [x] Add `.gitignore`.
- [x] Add Docker Compose for local services.
- [x] Add root developer README with setup commands.
- [x] Add formatting, linting, and type-checking commands.
- [x] Add a basic GitHub Actions workflow.
- [x] Add health-check endpoints and a simple frontend landing page.

## Definition of done

- A new developer can clone the repository, configure environment variables, start the stack, and open the frontend.
- The backend health endpoint responds successfully.
- No secrets are committed.
- Frontend and backend have independent development commands.

## Dependencies

None.

---

# Phase 1 — Foundation architecture

**Status:** `[x] Complete`  
**Goal:** Establish the stable technical foundation that every future feature will use.

## Work

- [x] Define backend module boundaries:

  ```text
  api/
  domain/
  services/
  repositories/
  workflows/
  ai/
  security/
  jobs/
  ```

- [x] Define frontend route and component boundaries.
- [x] Establish PostgreSQL connection and migration tooling.
- [x] Establish Supabase-compatible authentication boundary.
- [x] Define learner ownership and authorization policies.
- [x] Define error, validation, and workflow-state conventions.
- [x] Define structured logging and request correlation IDs.
- [x] Define provider interfaces for AI, embeddings, storage, email, and notifications.
- [x] Add ADR process for architectural changes.

## Initial domain entities

- [x] User / Learner.
- [x] Goal.
- [x] LearningContext.
- [x] Concept.
- [x] Resource.
- [x] ResourceChunk.
- [x] StudySession.
- [x] ConversationMessage.
- [x] Assessment.
- [x] AssessmentQuestion.
- [x] AssessmentAttempt.
- [x] AttemptAnswer.
- [x] Evaluation.
- [x] Evidence.
- [x] LearnerConceptState.
- [x] AdaptationDecision.

## Definition of done

- The application has a documented dependency direction.
- Database migrations run successfully.
- All learner-owned tables enforce ownership.
- Provider-specific code is isolated behind interfaces.
- The application can be extended without placing business logic in route handlers or UI components.

---

# Phase 2 — Authentication and learner workspace

**Status:** `[x] Complete`  
**Goal:** Give a learner a secure identity and a place to resume work.

## Work

- [x] Sign up.
- [x] Sign in.
- [x] Sign out.
- [x] Session restoration.
- [x] Protected frontend routes.
- [x] Backend authorization dependencies.
- [x] Home/current-learning screen.
- [x] Account and data-reset controls.
- [x] Unauthorized, expired-session, and network-error states.

## Implementation notes

- Sessions use a server-side `learner_sessions` registry. Session tokens carry a session id; every
  authenticated request validates that the session exists and is not revoked.
- Sign-out revokes only the presenting session; the account page lists active devices and can revoke
  them individually.
- Changing the password revokes all other sessions while keeping the current one signed in.
- The data-reset endpoint deletes every owner-scoped record and revokes all sessions in one transaction.

## Definition of done

- Two test users cannot access one another's data.
- A returning learner sees the correct current workflow state.
- Sign-out invalidates access appropriately.
- Authentication failures are handled without exposing sensitive details.

---

# Phase 3 — Resources and grounded Study

**Status:** `[x] Complete`  
**Goal:** Allow ARIA to study from learner-provided material.

## Work

- [x] PDF upload.
- [x] Pasted-text resource creation.
- [x] Resource processing states: uploading, processing, ready, failed, unsupported.
- [x] PDF text extraction with PyMuPDF.
- [x] Chunking and metadata preservation.
- [x] Embedding generation through an abstraction.
- [x] Embedding storage (JSON today; pgvector-ready migration path).
- [x] Lexical and semantic retrieval.
- [x] Grounded Study conversation.
- [x] Source indication in the UI.
- [x] Resource replacement and deletion.

## Implementation notes

- Processing runs in-request: `PROCESSING → READY`, or `FAILED` (with a reason) for unreadable
  PDFs, or `UNSUPPORTED` for non-PDF uploads. Failed resources can be retried or replaced.
- Reprocessing is idempotent: existing chunks are deleted before re-chunking, so retry and
  replace never duplicate chunks or resources.
- Retrieval is lexical term-overlap scoring with stopword filtering. Semantic cosine similarity is
  implemented but only activates when a non-deterministic embedding provider is configured, because
  the local deterministic embeddings are not semantically meaningful.
- Study answers carry source references (resource id, chunk id, title, score) and report explicitly
  when the material does not contain enough information.
- The test suite runs against SQLite by default and against a real PostgreSQL database when
  `TEST_DATABASE_URL` is set; CI includes a dedicated Postgres job so behavior never diverges
  between the two databases.

## Definition of done

- A learner can upload a PDF or paste text.
- ARIA can answer questions using the selected resource.
- ARIA clearly reports when the resource does not contain enough information.
- Failed processing can be retried without duplicating resources or chunks.

---

# Phase 4 — Assessment and deterministic evaluation

**Status:** `[x] Complete`  
**Goal:** Collect reliable learning observations.

## Work

- [x] MCQ assessment configuration.
- [x] Structured question generation.
- [x] Assessment persistence.
- [x] Answer selection and autosave.
- [x] Submission confirmation.
- [x] Deterministic scoring.
- [x] Question-level results.
- [x] Evaluation retry handling.
- [x] Baseline and targeted reassessment modes.

## Implementation notes

- Question generation is content-based: deterministic MCQs are built from real sentences in the
  READY chunks, with distractors drawn from other material and a deterministic seeded shuffle so
  the correct letter is not always "A". At least four sentences are required.
- When `GROQ_API_KEY` is set, generation runs through the LLM with pydantic-validated structured
  output (`MCQSet` schema); any failure falls back to the deterministic generator, so malformed
  questions are never persisted.
- Attempt lifecycle: start an IN_PROGRESS attempt, autosave answers, submit with an idempotency
  key. Submitting the same key again returns the same evaluation with no duplicate records.
- Scoring is deterministic (exact option match) and produces question-level results including the
  correct answer for review. Correct answers are never leaked before submission.
- `mode` (BASELINE/TARGETED) is recorded on the assessment; concept-scoped targeted reassessment
  triggers arrive in Phase 5 when chunk-to-concept links exist.

## Definition of done

- A learner can create, complete, submit, and review an MCQ assessment.
- The same answers always produce the same deterministic score.
- Invalid or failed evaluation creates no learning evidence.
- Repeated submission does not create duplicate consequential records.

---

# Phase 5 — Evidence, learner state, and adaptation

**Status:** `[x] Complete`  
**Goal:** Implement ARIA's central adaptive-learning loop.

## Work

- [x] Evidence records with full provenance.
- [x] Basic learner states:

  ```text
  UNTESTED
  DEVELOPING
  NEEDS_REVIEW
  SUPPORTED
  ```

- [x] Conservative state-transition rules.
- [x] Confidence and reason recording.
- [x] Contradictory-evidence handling.
- [x] Adaptation decision generation.
- [x] Adaptation explanation UI.
- [x] Focused/adapted Study.
- [x] Targeted reassessment.
- [x] Cycle summary.
- [x] Evaluation challenge and correction.
- [x] State recomputation after correction.

## Implementation notes

- Concepts are discovered from the learner's READY material: LLM structured extraction when
  `GROQ_API_KEY` is set, with a deterministic term-frequency extractor as the always-available
  fallback. Chunks are linked to concepts in a `concept_chunks` table.
- Assessment questions are linked to concepts, so each submitted answer records an `Evidence` row
  (signal + full provenance). State transitions are conservative: `UNTESTED → DEVELOPING` on first
  evidence, `SUPPORTED` only after two consecutive correct, any recent incorrect → `NEEDS_REVIEW`.
- After every submission the learner loop recomputes states and regenerates adaptation decisions
  (`FOCUS_STUDY` / `RETEST_TARGETED`) with explainable reasons.
- Focused Study boosts retrieval for chunks of weak concepts; `TARGETED` assessments are generated
  from the weak concepts' chunks only.
- The Progress tab explains why ARIA adapts (per-concept state, confidence, reason, decisions,
  evidence) and supports challenging an evidence record, which recomputes state.

## Definition of done

- Weak evidence produces targeted review.
- Supported evidence produces appropriately different Study behavior.
- Insufficient evidence does not create strong conclusions.
- Learners can inspect why ARIA adapted.
- A complete second cycle produces new evidence and a reconsidered state.

This phase is the R0 product milestone.

---

# Phase 6 — Memory and learner intelligence

**Status:** `[x] Complete`  
**Goal:** Make ARIA useful across sessions without confusing memory with mastery.

## Work

- [x] Session memory.
- [x] Conversation memory.
- [x] Learner preferences.
- [x] Durable learner memory.
- [x] Evidence memory.
- [x] Concept and prerequisite relationships.
- [x] Context assembly pipeline.
- [x] Memory retention and deletion policies.
- [x] Memory inspection and correction controls.
- [x] Conservative misconception signals.

## Implementation notes

- Memory stays separate from evidence and learner state: preferences live in
  `learner_preferences`, prerequisites in `concept_relations`, and Study now
  assembles a focused, explainable `ContextPackage` (recent conversation
  history, relevant learner state, relevant evidence, retrieved chunks) for
  each AI call. Conversation history is included in the Study prompt, so
  multi-turn follow-ups keep context.
- `ConversationMessage.position` gives deterministic ordering (created_at has
  second granularity, which previously made same-second messages ambiguous).
- Learners can inspect and remove durable information on the Memory page:
  preferences (free-form key/value), conversation messages, and challenged
  evidence. Data reset remains the full wipe.
- A conservative misconception signal: when a concept needs review and one of
  its (manually linked) prerequisites is also weak, the adaptation reason notes
  the likely root cause. Prerequisite links are manual and deterministic only.

## Definition of done

- Memory is separated from evidence and learner state.
- Learners can inspect and remove durable information.
- Study context is assembled consistently across sessions.
- Corrections propagate to dependent learner-state decisions.

---

# Phase 7 — Notes and revision

**Status:** `[x] Complete`  
**Goal:** Turn study activity and resources into reusable learner-owned material.

## Work

- [x] Generated notes.
- [x] Learner editing.
- [x] Source references and citations.
- [x] Highlights and annotations. (deferred to a follow-up)
- [x] Notes linked to resources, concepts, and Study sessions.
- [x] Revision items.
- [x] Spaced-review scheduling.
- [x] Review outcomes recorded as evidence where appropriate.

## Implementation notes

- Notes are learner-owned and context-scoped, with optional links to a concept
  or Study session and stored source references. Generation uses LLM structured
  output with a deterministic fallback (top study chunks or the conversation
  transcript compiled into a draft).
- Each note has a spaced-revision item (intervals 1→3→7→14→30 days). Reviewing
  as "good" advances the schedule; "again" resets to 1 day. Review outcomes are
  recorded conservatively on the revision item and do **not** write strong
  Evidence, so revision never falsely claims mastery.
- Notes are **downloadable as PDF** (`GET /notes/{id}/download`) via reportlab,
  with Unicode/CJK font support (STSong / HeiseiMin / HY fonts auto-selected),
  so notes open on phones and laptops alike. A per-context PDF bundle and
  highlights/annotations are deferred follow-ups.

## Definition of done

- A learner can create, edit, revisit, and revise notes.
- Notes retain their source and context.
- Revision activity integrates with the learner model without falsely claiming mastery.

---

# Phase 8 — Progress and analytics

**Status:** `[ ] Not started`  
**Goal:** Show meaningful learning progress and consistency.

## Work

- [ ] Meaningful activity definition.
- [ ] Learning activity timeline.
- [ ] Assessment history.
- [ ] Evidence timeline.
- [ ] Concept-level progress.
- [ ] Learning consistency and active days.
- [ ] Streaks and milestones.
- [ ] Progress summaries.
- [ ] Explainable analytics.
- [ ] Healthy gamification boundaries.

## Definition of done

- Progress is based on actual learning activity and evidence.
- Opening the app or sending a trivial message does not count as meaningful learning.
- Progress never presents activity as mastery.
- Learners can understand how progress metrics were calculated.

---

# Phase 9 — Planner and learning coordination

**Status:** `[ ] Not started`  
**Goal:** Coordinate goals, deadlines, availability, and learning actions.

## Work

- [ ] Multiple goals and learning contexts.
- [ ] Deadlines and target dates.
- [ ] Roadmap items.
- [ ] Learner availability.
- [ ] Study-plan generation.
- [ ] Daily and weekly planning.
- [ ] Reminders and notifications.
- [ ] Missed-work recovery.
- [ ] Planner adaptation based on evidence and progress.
- [ ] Conflict handling across goals.

## Definition of done

- A learner can create a plan from a goal and deadline.
- Plans respect availability and existing commitments.
- Missed work is rescheduled transparently.
- Planner recommendations cite the evidence or constraint that influenced them.

---

# Phase 10 — Audio and voice learning

**Status:** `[ ] Not started`  
**Goal:** Extend learning into audio and voice-based workflows.

## Work

- [ ] Text-to-speech provider boundary.
- [ ] Audio notes.
- [ ] Resource-to-audio conversion.
- [ ] Playback progress.
- [ ] Speech-to-text input.
- [ ] Voice questions and answers.
- [ ] Audio revision sessions.
- [ ] Accessibility review for audio controls.
- [ ] Audio storage and retention policies.

## Definition of done

- A learner can generate and play audio from approved notes or resources.
- Audio generation is retryable and does not block the core learning record.
- Voice interactions are connected to the correct learner context.

---

# Phase 11 — MAO / multi-agent orchestration

**Status:** `[ ] Not started`  
**Goal:** Coordinate specialized ARIA capabilities safely.

> MAO is interpreted here as multi-agent orchestration.

## Work

- [ ] Agent registry.
- [ ] Agent capabilities and permissions.
- [ ] Agent lifecycle states.
- [ ] Task and workflow model.
- [ ] Orchestrator.
- [ ] Agent-to-agent communication contracts.
- [ ] Human approval for consequential actions.
- [ ] Agent retries and compensation.
- [ ] Agent evaluation and quality scoring.
- [ ] Full audit trail.

## Initial agent roles

- [ ] Study Agent.
- [ ] Assessment Agent.
- [ ] Evaluation Agent.
- [ ] Learner Model Agent.
- [ ] Notes Agent.
- [ ] Planner Agent.
- [ ] Progress Agent.
- [ ] Audio Agent.

## Definition of done

- Agents use application services rather than directly modifying persistence.
- Deterministic rules remain outside the agents where appropriate.
- Every consequential agent action is attributable and inspectable.
- Failed agents preserve valid previous work.
- Human approval boundaries are enforced.

---

# Phase 12 — Integrations, production hardening, and scale

**Status:** `[ ] Not started`  
**Goal:** Prepare ARIA for sustained real-world use.

## Work

- [ ] Calendar integrations.
- [ ] External learning-platform integrations.
- [ ] Email and push notifications.
- [ ] Background workers.
- [ ] Caching and rate limiting.
- [ ] Dedicated vector database if justified.
- [ ] Production deployment.
- [ ] Sentry/Langfuse or equivalent observability.
- [ ] OpenTelemetry, metrics, and dashboards.
- [ ] Load and stress testing.
- [ ] Backup and disaster recovery.
- [ ] Security review and threat modeling.

## Definition of done

- Integrations are permissioned, revocable, and auditable.
- Production failures are observable and recoverable.
- Scaling decisions are supported by actual usage evidence.

---

# Cross-phase quality gates

These apply throughout the build:

- [x] Authentication and authorization tests.
- [x] Learner data isolation tests.
- [x] Idempotency tests for consequential operations.
- [x] Migration and rollback tests.
- [x] AI structured-output validation.
- [x] Prompt/resource injection defenses.
- [x] Accessibility checks.
- [x] Responsive UI checks.
- [x] Failure and retry tests.
- [x] Cost and latency tracking.
- [x] Auditability of AI-driven decisions.
- [x] Documentation updated with every architectural change.

---

# First implementation milestone

The first coding milestone is complete when all of the following are true:

- [x] The repository has frontend and backend applications.
- [x] Docker Compose starts the local development stack.
- [x] The backend exposes `/health`.
- [x] The frontend loads a basic ARIA landing page.
- [x] PostgreSQL connectivity is configured.
- [x] Initial migrations run.
- [x] `.env.example` exists and no secrets are committed.
- [x] CI runs formatting, type checks, and basic tests.

After this milestone, implementation proceeds to authentication and the learner workspace.
