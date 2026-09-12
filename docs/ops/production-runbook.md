# ARIA Production Runbook

Operational procedures for deploying and running ARIA in production. The
application artifacts referenced here already exist in the repository; this
document sequences them and records the drills an operator must execute
before unrestricted production use.

---

## 1. Deployment sequence

```text
1. Secrets from the deployment secret manager (never a committed .env):
   POSTGRES_PASSWORD, DATABASE_URL (same password — preflight verifies the
   coupling), ARIA_SESSION_SECRET, ARIA_LLM_KEYS_ENCRYPTION_KEY,
   GROQ_API_KEY, SMTP_*, ARIA_CORS_ORIGINS, ARIA_TRUSTED_HOSTS,
   ARIA_PUBLIC_URL, NEXT_PUBLIC_API_URL, ARIA_DOMAIN.
2. python scripts/check_prod_secrets.py --strict --ai-tutoring --byo-keys --audio
   (add --semantic-enabled / --push-enabled as scoped;
   --allow-local-tts only for beta: unrestricted prod requires cloud TTS)
3. docker compose -f docker-compose.prod.yml config --quiet
4. docker compose -f docker-compose.prod.yml up -d --build
   (the `migrate` service applies alembic upgrade head before backend start;
   verify single head: 0017_owner_scoped_idempotency)
5. curl https://<ARIA_DOMAIN>/ready        # DB-backed readiness via Caddy (sole public probe)
   # /health is backend-internal liveness (NOT routed by Caddy by design):
   # query it backend-direct, e.g. docker compose exec backend curl localhost:8000/health
   curl https://<ARIA_DOMAIN>/metrics      # must return 403 publicly
6. Smoke: register → verify email → onboard → upload material → ask tutor.
```

Key generation helpers: `scripts/generate_llm_keys_key.py` (BYO encryption),
`scripts/generate_vapid.py` (web push). Rotation for BYO keys:
`scripts/rotate_llm_keys.py` (run until `reencrypted=0, failed=0`, then drop
`ARIA_LLM_KEYS_ENCRYPTION_KEY_OLD`).

## 2. Backup and restore drill (execute before launch; RPO/RTO below)

Backups run automatically in production (Caddy-fronted stack):
`ARIA_BACKUP_ENABLED=true` (default in compose), daily at
`ARIA_BACKUP_INTERVAL_HOURS` into the `backups` volume, pruning to
`ARIA_BACKUP_KEEP`. The scheduler job is advisory-locked (multi-replica safe)
and requires `postgresql-client` (present in `backend/Dockerfile.prod`).

Manual backup: `python scripts/backup_db.py [--out DIR] [--keep N]`
Manual restore: `python scripts/restore_db.py [FILE]` (defaults to newest)

**Drill procedure (perform on staging, record the results below):**

```text
1. Seed staging with representative data (accounts, materials, assessments,
   audio, notes, BYO keys).
2. python scripts/backup_db.py --out /tmp/drill      # record duration
3. Stop backend; drop and recreate the target database.
4. python scripts/restore_db.py /tmp/drill/<latest>.dump.gz   # record duration
5. alembic upgrade head                              # must be a no-op
   (local dev without pip install: PYTHONPATH=backend alembic upgrade head)
6. Start backend; verify /ready, login, material retrieval, audio playback,
   assessment submission, BYO-key usage (learner key still decrypts).
7. Record: backup size, backup duration, restore duration, verification
   checklist result, operator, date.
```

**RPO/RTO template (fill in and keep with incident docs):**

| Parameter | Value |
|---|---|
| RPO target (max acceptable data loss) | ____ (interval-based: equal to `ARIA_BACKUP_INTERVAL_HOURS`) |
| RTO target (max acceptable restore time) | ____ |
| Backup duration (measured) | ____ |
| Restore duration (measured) | ____ |
| Last successful drill date / operator | ____ |

**First drill record (2026-09-05, local Docker `pgvector/pgvector:pg16`, pre-launch dry-run):**

| Check | Result |
|---|---|
| Fresh migrations (`alembic upgrade head`, 17 revisions incl. pgvector+HNSW, 0017 constraint surgery) | pass — 9.5 s |
| `/ready` (public via Caddy) + `/health` (backend-direct) against Postgres | 200 / 200 |
| Seeded data backed up (register/context/resource/note) | pass — 92.8 KB dump, 2.5 s |
| Schema destroyed (`DROP SCHEMA public CASCADE`) → 0 tables | pass |
| Restore (`scripts/restore_db.py`, `--clean --if-exists`) | pass — 40 tables, 4.2 s |
| `alembic upgrade head` after restore | no-op (correct) |
| App-level verification after restore | `/ready` 200, login 200, context/resource/chunks/note intact |

**Dry-run lessons baked into the tooling (2026-09-05):**

1. `scripts/backup_db.py`, `scripts/restore_db.py`, `scripts/generate_llm_keys_key.py`, `scripts/rotate_llm_keys.py` now self-bootstrap `backend/` onto `sys.path` — they run from the repo root exactly as documented, no `PYTHONPATH` needed (previously `ModuleNotFoundError: app`).
2. `pg_dump` **without** `-f -` is the supported invocation: `pg_dump -f -` produces a 0-byte stream under `docker exec` wrappers on Docker Desktop for Windows. `create_backup` now uses implicit stdout, so plain `PG_DUMP="docker exec -i <db> pg_dump -U aria -Fc --no-owner"` wrappers work unmodified.
3. Regression guard added for the gzip-layer bypass: `subprocess.run(stdout=GzipFile)` wrote around compression (child grabbed the fd via `fileno()`); the default runner now streams `Popen` stdout through `shutil.copyfileobj` into the gzip layer. Verify drills with the magic bytes: gzip `1f 8b` outside, `PGDMP` after decompression.

## 3. Data retention after account deletion

`DELETE /api/v1/account/data` removes every learner-owned table (contexts,
materials, chunks, notes, revisions, sessions, messages, assessments,
attempts, evaluations, evidence, learner state, adaptation decisions,
progress/activity/badges, notifications, push subscriptions, audio artifacts
and progress, preferences, goals, planner records, BYO key row, per-learner
AI usage) and revokes all sessions.

**Intentionally retained records:**

| Table | Why retained |
|---|---|
| `learners` / `learner_sessions` (revoked) | Account identity + revocation history; no personal learning content |
| `audit_log` | Security audit trail (agent/orchestration actions); retention policy |
| `workflows`, `agent_tasks`, `approval_requests` | Orchestration history and approval records |
| `ai_usage` (global) | Aggregate spend accounting (period totals, not per-learner) |
| `rate_limit_buckets` | Shared abuse-control state, no personal data |

The user-facing reset response states this scope explicitly. If a privacy
policy requires full erasure of these rows for a specific learner, it is a
manual, audited operation — do not automate blanket deletion of audit data.

## 4. Go-live gates (staging, before unrestricted production)

- [ ] Fresh `docker compose -f docker-compose.prod.yml up` on a clean host; `migrate` completes; `/ready` 200 (public), `/health` 200 (backend-direct only)
- [ ] Real Groq calls verified (tutor answer with `fallback_used=false`; rotate key — it was pasted in chat)
- [ ] Real TTS verified (artifact `READY` + playback 200; note serving provider: cloud vs local)
- [ ] Real SMTP verified (email verification + password reset delivered)
- [ ] Embeddings enabled or explicitly deferred (deterministic retrieval remains the fallback)
- [ ] TLS via Caddy with a real domain; HSTS present; `/metrics` 403 publicly
- [ ] Backup/restore drill §2 executed with recorded RPO/RTO
- [ ] Full Playwright suite green against staging (65 tests; includes full journey + axe)
- [ ] `scripts/check_prod_secrets.py --strict ...` passes (incl. password coupling)
