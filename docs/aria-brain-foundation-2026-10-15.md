# ARIA Brain foundation — 2026-10-15

Branch: `codex/aria-brain`, based on the committed UI/audio work on `codex/ui-polish`.

## Completed: S1 — learner snapshot

`services/brain/snapshot.py` builds immutable, validated projections for one owned learning context:

- Up to 50 recent concept states and 30 valid evidence references.
- Up to 10 active roadmaps, with persisted milestone counts.
- Up to 20 deadlines in the next 14 days and 20 overdue pending tasks.
- Full subject totals for concepts, supported/weak states, evidence and messages.
- Validated account-level assessment preferences, when present. Missing preferences remain unset.

Queries apply limits before loading rows. Snapshot building does not flush, commit, recompute mastery or synchronize milestones. It deliberately avoids `list_roadmaps`, which synchronizes milestones and commits. Counts are subject-scoped; arbitrary preferences, conversation text, evidence provenance and task descriptions are excluded. This is a new shared projection, not yet a replacement for existing tutor/dashboard consumers.

## Completed: S2 — typed capabilities and reusable audio

`services/brain/capabilities.py` adapts the eight existing orchestration agents and adds `audio.from_session`. Each capability declares its input model, required parameters, required/optional classification, confirmation policy, cost class and handler. Unknown names and extra/invalid parameters are rejected before execution. Existing workflow handlers and approval rules remain in place.

Conversation/text audio generation now lives in `services/audio.py`; API adapters preserve the existing URLs, response shape and 404/422 behavior. The typed audio capability requires a session ID, matching owned context, and an existing message-position cutoff. Later messages are excluded on replay. An unchanged, ready source reuses the saved episode without calling speech generation again. Audio capability outputs contain IDs/status, not transcript text.

The existing engine can execute the `audio_from_session` workflow through its normal workflow endpoint. It validates the typed audio parameters before creating a workflow. Speech-generation failures remain failed workflows, rather than being reported as completed. This does not add an exactly-once guarantee for external provider calls.

## Verification

- Full backend: **550 passed, 10 PostgreSQL-only skips** on local SQLite.
- Foundation unit tests: **6 passed**, covering ownership, subject isolation, bounds, no flush/commit, parameter validation, confirmation gating, existing-agent adapters, frozen audio cutoff, reuse and workflow execution.
- Focused audio/workflow/crash recovery suite: **34 passed, 1 PostgreSQL-only skip**.
- Browser audio regression suite: **6 passed**, using isolated servers and blank cloud keys. Covers existing saved-note playback/progress, pasted text/reload/source view, image OCR upload, chat conversion, inline retry, and mobile overflow.
- TypeScript, ESLint (`app components lib`), Python lint (`backend tests scripts`) and diff whitespace checks passed.
- No database migrations or new frontend behavior in this foundation stage. No new live-provider call was made.

## Next: S3 — chat routing and action cards

Not implemented in this checkpoint:

- Routing enable/disable flags and optional LLM classification.
- Durable message action metadata and run/status/cancel endpoints.
- Persisted immutable action inputs, workflow identity and safe retry state.
- Action cards, clarification choices and bounded status polling in Learn.
- Redacted decision audit helper.

The first complete routed flow remains “make audio from this chat.” Keep an actual source snapshot or immutable source reference as well as its message cutoff, scope status and cancellation to the owner, and distinguish cancelling before execution from stopping provider work already in progress. Server policy determines confirmation; LLM-supplied fields cannot relax it.

S4 transactional outbox and S5 proactive suggestions follow S3. Required scoring/evidence/learner-state/daily-review/roadmap chains remain deterministic and inline. Roadmap setup and configurable, one-question-at-a-time assessments remain separate feature work.
