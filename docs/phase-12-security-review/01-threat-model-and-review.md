# ARIA Security Review & Threat Model

**Status:** Complete (Phase 12.10)  
**Scope:** Self-review of the current implementation against a structured threat
model. Companion to the Phase 3 security architecture and the hardening added
in Phase 12.1.

## 1. Assets and trust boundaries

| Asset | Where it lives |
|---|---|
| Learner credentials (password hashes) | `learner_sessions`, `learners` (PBKDF2-HMAC-SHA256, 310k iterations, 16-byte salt) |
| Session tokens | `learner_sessions`; HMAC-SHA256-signed opaque token delivered as an `HttpOnly`/`SameSite=Strict` cookie (`security/tokens.py`, `security/csrf.py`) |
| Learning data (contexts, notes, evidence, assessment history) | Postgres/SQLite, owner-scoped via `owner_id` on every owned model |
| AI provider keys / SMTP / VAPID / secrets | Environment only; `.env.example` contains placeholders, no real secrets |
| Audit trail | `audit_log` (orchestration) — deliberately excluded from data-reset deletion |

Trust boundaries: Browser ↔ Next.js frontend ↔ FastAPI backend ↔ Postgres,
with outbound calls to AI providers (Groq/OpenAI-compatible), SMTP, and web
push services.

## 2. Threats and controls

### T1 — Account takeover (credential stuffing / brute force)
- **Controls:** PBKDF2 password hashing; production-only sliding-window rate
  limiting on `/auth/register` and `/auth/login`
  (`security/rate_limit.py`, wired in `api/routes/auth.py`).
- **Residual:** Rate limiting is single-instance in-process state; multi-instance
  production must move it to a shared store (Phase 12.7 cache decision) or an
  edge WAF.

### T2 — Session hijacking / fixation
- **Controls:** random per-login session id; token bound to server-side
  `learner_sessions` row with `revoked_at`; `HttpOnly` + `SameSite=Strict`
  session cookie; password change and data reset revoke other/current sessions;
  session list + revoke endpoints; hard expiry (24 h).
- **Residual:** The legacy `Authorization: Bearer` path (from the localStorage
  era) is still accepted for compatibility; it should be removed once the
  cookie path is the only client.

### T3 — CSRF
- **Controls:** double-submit CSRF token (`aria_csrf` cookie + `X-CSRF-Token`
  header) enforced by `CSRFMiddleware` for cookie-authenticated state-changing
  requests; `SameSite=Strict` on both cookies; public credential endpoints
  excluded with rationale documented in `security/csrf.py`.
- **Residual:** none of consequence given `SameSite=Strict` + token check.

### T4 — Cross-site scripting (XSS) → token theft
- **Controls:** `HttpOnly` session cookie (not readable by JS); CSP, HSTS,
  `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`,
  `X-Frame-Options` served via `frontend/next.config.ts`; React escapes text.
- **Residual:** `script-src 'unsafe-inline'` is required by the Next.js runtime
  (documented tradeoff). Recommendation: introduce nonce/hash-based CSP when the
  frontend runtime allows it, and remove the legacy localStorage token storage.

### T5 — Injection (SQL / prompt / resource)
- **Controls:** SQLAlchemy ORM (parameterized); Pydantic input validation;
  AI structured-output schema validation; prompt/resource injection defenses
  already covered by existing test suites; AI system prompts instruct
  grounded-only answers.

### T6 — Cross-tenant data isolation
- **Controls:** every owned model carries `owner_id`; service/repository layer
  enforces ownership on reads/writes (covered by isolation tests across phases);
  orchestration, push, and idempotency records are all owner-scoped.

### T7 — Consequential/destructive action abuse
- **Controls:** human approval gates for `data_reset` and `evidence_invalidate`
  workflows; full audit trail; generalized `Idempotency-Key` replay prevents
  double execution of a destructive workflow; data reset excludes orchestration
  audit rows so the destructive action remains traceable.

### T8 — Secrets exposure
- **Controls:** session signing secret is fail-fast in production
  (`security/secrets.py`); keys are `repr=False`; `.env.example` has no values;
  `.gitignore` excludes `.env*`.
- **Residual:** secrets rotation and a managed secret store are operational
  concerns for 12.9 hosting.

### T9 — Denial of service
- **Controls:** production rate limiting; request logging and Prometheus
  `/metrics` for observability; `/ready` probes for orchestrators.
- **Residual:** no request-body limits or per-IP abuse rules beyond auth; add
  an edge rate limiter before public exposure.

### T10 — Supply chain
- **Residual:** no automated dependency/vulnerability scanning in CI.
  Recommendation: add `pip-audit` (backend) and `npm audit` (frontend) to CI.

## 3. Residual-risk checklist for production (12.9 hosting)

- [ ] Remove the legacy `Authorization: Bearer` path and `localStorage` token.
- [ ] Harden CSP with nonces for scripts.
- [ ] Add email verification and password-reset flows.
- [ ] Add dependency scanning (`pip-audit`, `npm audit`) to CI.
- [ ] Enforce TLS at the reverse proxy; HSTS already emitted in production.
- [ ] Move rate limiting and cache to a shared store for multi-instance deploy.
- [ ] Request-body size limits and an edge rate limiter.
- [ ] Regular re-review of this document after each production change.

## 4. Verification evidence

- `tests/test_security.py` — cookie/CSRF round-trip, bearer exemption, signout
  cookie clearing, secret fail-fast, rate-limit unit tests.
- `tests/test_injection.py`, per-phase isolation/idempotency tests.
- Playwright + axe smoke (0 critical violations) covering cookie-authenticated
  app flows.
