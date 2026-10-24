# ARIA scaling plan: from 1k to 1M users

Starting point: paid AI keys, Vercel Pro, Supabase Pro (see [BACKLOG.md](BACKLOG.md)).
Each phase lists **when to start it** (the measured trigger, not a guess), **what changes in the
code**, **how we prove it works** and **effort** (one developer with Claude Code).

## Phase 0: Measure first (do now, before 10k) · ~3 days

You can't scale what you can't see. Everything later is decided by these numbers.

| Step | What | Where in ARIA |
|---|---|---|
| Load-test script | k6 scripts: sign-up, chat (Quick/Deep), web search, upload, quiz, audio; ramp 50 → 500 → 2,000 virtual users | new `loadtest/` folder, run against **staging**, never production |
| Staging environment | A second Vercel project + Supabase branch with the same settings | Vercel "Preview" + Supabase branching |
| Dashboards | p95 latency per route, error rate, DB connections, job queue length, AI cost/day | Vercel Observability, Supabase reports, Sentry, Langfuse |
| Baseline | Record the numbers at today's scale | `docs/SCALING-PLAN.md` results table (below) |

**Done when:** we know the user count at which latency or errors start to climb, and which route breaks first.

---

## Phase 1: 10k users · ~1–2 weeks

**Start when:** DB connections > 60% of the pool at peak, or p95 page load > 1.5 s, or job wait > 1 min.

### 1.1 Database: transaction pooler
- **Why:** each serverless request opens its own connection; the session pooler (port 5432) holds one
  per client and runs out. The transaction pooler (port 6543) shares a few real connections among
  thousands of requests.
- **Change:** `DATABASE_URL` → port 6543; in `backend/app/db/session.py` keep `NullPool` and set
  psycopg `prepare_threshold=None` (prepared statements don't survive transaction pooling).
- **Watch out:** session-level advisory locks (`pg_advisory_lock` in `services/brain/checkpoints.py`,
  `pg_try_advisory_lock` in `jobs/scheduler.py`) must become transaction-level
  (`pg_advisory_xact_lock`) or move to Redis locks.
- **Prove:** load test at 2× expected peak; no `OperationalError`; connections flat.

### 1.2 Indexes and slow queries
- **Change:** run Supabase's slow-query report; add indexes for the top 5 (likely
  `conversation_messages(study_session_id, position)`, `evidence(owner_id, concept_id)`,
  `resources(owner_id, context_id)`, `jobs(status, lease_until)`); new Alembic migration.
- **Prove:** each slow query < 50 ms at production data size.

### 1.3 Redis (Upstash) for rate limits and short caches
- **Why:** rate limits today are per-process (`ARIA_RATE_LIMIT_BACKEND=memory`) or one DB upsert per
  request (`db`); both break down with many instances.
- **Change:** add a `redis` backend in `backend/app/security/rate_limit.py`; cache for 1–5 minutes:
  `/auth/me`, the adaptation/topic states, roadmap lists, web-search results for the same question.
- **Prove:** rate limits hold across instances; DB reads per page drop by half.

### 1.4 Per-user AI budgets and abuse protection
- **Change:** turn on `ARIA_LLM_PER_USER_BUDGET_USD` (exists); daily caps for web searches and audio
  minutes per user; Cloudflare Turnstile on sign-up; Vercel Firewall rules for bursts.
- **Prove:** a scripted abusive user hits limits; normal users never do.

---

## Phase 2: 50k–100k users · ~2–4 weeks

**Start when:** job queue backlog grows at peak, the 5-minute timer is the bottleneck, or DB CPU > 60%.

### 2.1 Managed job queue
- **Why:** jobs today live in a Postgres table, started by an HTTP "kick" and a 5-minute timer.
  At high volume that means polling load on the database and slow starts.
- **Change:** keep the `jobs` table as the record (status, progress, resume), but deliver work through
  **Vercel Queues** (or Upstash QStash / Inngest): `jobs.enqueue` publishes a message; a queue consumer
  calls `run_one`. The existing `Continue` hand-over and leases stay as they are.
- **Where:** `backend/app/services/jobs.py` (`enqueue`, `kick`), `api/routes/internal.py`.
- **Prove:** 1,000 audio episodes queued at once all finish; no job runs twice; failures retry.

### 2.2 Read replica
- **Change:** a Supabase read replica; route read-heavy pages (Progress, history, lists) to it via a
  second engine in `db/session.py`; writes stay on the primary.
- **Prove:** primary CPU drops; replica lag < 1 s.

### 2.3 Cache repeated AI work
- **Change:** reuse file digests and quiz questions for identical material (hash of the text); cache
  web-search findings per normalised question for a few minutes (current affairs stay fresh).
- **Prove:** AI cost per active user drops; answers unchanged.

### 2.4 Multi-region readiness
- **Change:** keep functions in the same region as the database (iad1 / us-east-1); add a CDN for
  audio files (Blob already serves through a CDN).
- **Prove:** p95 latency from India and Europe acceptable (test with remote load generators).

---

## Phase 3: 1M users · ongoing

**Start when:** a single Postgres primary is near its largest size, or the team needs 24/7 reliability.

| Area | Change |
|---|---|
| Database | Larger compute; partition the biggest tables (messages, evidence) by owner; archive old chats |
| Workers | Separate worker fleet (Vercel Daemons or containers) for audio and digests |
| AI | Negotiated rate limits with OpenAI and Google; three-provider fallback; batch APIs for non-urgent work |
| Reliability | SLOs (99.9%), on-call rotation, incident runbooks ([PRODUCTION-RUNBOOK.md](PRODUCTION-RUNBOOK.md)), chaos tests |
| Data | Data retention policy; GDPR/DPDP processes; regional data residency if required |
| Cost | Monthly cost review per feature; move heavy users to paid plans |

---

## Cost model (to revisit with real numbers)

`monthly cost ≈ hosting + database + storage + (active users × questions/day × 30 × AI cost per answer)
+ web searches + audio minutes`

AI is the largest line at every phase. The levers: model choice per depth (mini models for
Quick/Balanced), caching, per-user caps, and paid plans for heavy use.

## Order of work

1. Phase 0 now: load tests, staging, dashboards, baseline.
2. Phase 1 when the first trigger fires (likely the pooler first).
3. Phase 2 and 3 only when their triggers fire. Don't build for 1M users before there are 10k.

## Results log

| Date | Users / load tested | p95 chat | p95 pages | Errors | Change made |
|---|---|---|---|---|---|
| — | baseline to be recorded in Phase 0 | | | | |
