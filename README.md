# ARIA

ARIA is an AI Learning Operating System. This repository is the working implementation of the product, UX, architecture, AI, memory, API, agent, prompt, and technology planning captured in `docs/` (see `docs/theme-system.md` for the frozen visual baseline and `design/README.md` for the wireframe design assets).

## Current implementation scope

Phases 0–9 of the R0 adaptive-learning loop are implemented:

- Next.js frontend (Extruded Light design system, dark default + light theme);
- FastAPI backend with learner-owned domain model;
- PostgreSQL + Alembic migrations (single metadata-driven baseline through `0006`);
- server-side session registry (sign in/out, active devices, data reset);
- resources (text/PDF ingestion with retry and replace);
- grounded Study and topology knowledge map;
- deterministic MCQ assessment with idempotent submission;
- evidence → learner-state → adaptation loop with explainable decisions;
- memory: preferences, context assembly, prerequisites, memory inspector;
- notes: generation fallback, revision scheduling, due queues, PDF export;
- progress: meaningful-activity streaks, heatmap, badges;
- planner: exam deadlines, planned tasks, missed-work recovery, in-app notifications, email reminders (SMTP with log fallback);
- Docker Compose development environment;
- CI that runs formatting, lint, type checks, tests (SQLite and Postgres), migration round trips, frontend build/lint, and a Playwright browser + accessibility smoke.

The R0 loop:

```text
Learning Context → Resources → Study → Assessment → Evaluation
→ Evidence → Learner State → Adapted Study → Reassessment
→ Memory → Notes/Revision → Progress → Planner
```

Audio and MAO remain planned product areas. They are deliberately represented in the domain and workflow boundaries so they can be added without creating parallel systems.

## Local development

### Backend

The recommended setup is a repo-local virtual environment (hermetic, interpreter-independent):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_local.ps1
.\.venv\Scripts\python.exe scripts\check_deps.py
.\.venv\Scripts\python.exe -m pytest
```

Manual alternative:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --app-dir backend
```

> **Windows notes**
> - The WindowsApps `python` launcher can fail in some sessions with a "terminated logon session"
>   error. `scripts\setup_local.ps1` discovers a real interpreter and provisions `.venv` from it,
>   so tests never depend on the launcher. Run tests with
>   `.\.venv\Scripts\python.exe -m pytest` (or `scripts\test.ps1`).
> - Non-ASCII repository paths can trip the cp1252 console encoding. Set `$env:PYTHONUTF8="1"`
>   before install/test commands if you see `UnicodeEncodeError` or mojibake — `check_deps.py` is
>   encoding-safe either way.
> - On Linux/macOS you may prefer `pip install -e ".[dev]"`; `pytest` resolves `app` via
>   `pythonpath` regardless of install method.

> If the test suite fails on imports, run `python scripts/check_deps.py` (or
> `.\.venv\Scripts\python.exe scripts\check_deps.py`). It prints the active interpreter and a
> `PASS`/`MISSING` line per dependency. If `fitz`/`pymupdf` or `litellm` show `MISSING`, the
> interpreter running the tests was not the one you provisioned — another Python on `PATH` (for
> example a leftover virtual environment) is being picked up. Provision with
> `scripts\setup_local.ps1` and use the `.venv` interpreter.

Backend API: <http://localhost:8000>  
Health check: <http://localhost:8000/health>  
OpenAPI: <http://localhost:8000/docs>

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend: <http://localhost:3000>

### Database migrations

```powershell
docker compose up -d db          # start PostgreSQL
alembic upgrade head             # apply the metadata-driven baseline migration
```

### Tests

```powershell
pytest                          # SQLite (in-memory, default)
pytest                          # same suite against Postgres when TEST_DATABASE_URL is set:
$env:TEST_DATABASE_URL="postgresql+psycopg://aria:aria@localhost:5432/aria_test"
```

### Docker Compose

```powershell
docker compose up --build
```

## Architecture rules

1. Route handlers coordinate; domain services own business rules.
2. Repositories own persistence access.
3. Provider-specific SDKs stay behind interfaces.
4. Learner-owned records require an owner identity.
5. Consequential workflows must be idempotent and auditable.
6. Memory, evidence, learner state, and mastery claims are separate concepts.
7. Deterministic logic stays deterministic; AI does not decide authorization or MCQ correctness.

See [BUILD_PLAN.md](BUILD_PLAN.md) for the implementation sequence and completion checklist.

## Security & production notes

The app is feature-complete through Phase 12 hardening but still requires
operational hardening before a public multi-instance deployment. Current status:

- **Authentication.** Sessions use HTTP-only, `SameSite=Strict` cookies with
  double-submit CSRF protection; the frontend relies on cookies (no tokens in
  `localStorage`). A legacy `Authorization: Bearer` path is still accepted for
  compatibility but is deprecated and will be removed once the cookie contract
  is the only client.
- **AI dependency.** Without `GROQ_API_KEY` the app runs on deterministic
  fallbacks (good for tests and reliability). When configured, AI calls are
  versioned, budget-capped (persisted monthly spend), and cost/token-logged.
- **Reminders.** Run automatically on a background scheduler (APScheduler) with
  a PostgreSQL advisory-lock guard so only one replica executes each job; the
  pull endpoint `POST /api/v1/planner/reminders/check` remains for dev/backfill.
- **Email.** SMTP is optional; without `SMTP_HOST` emails are logged to the
  console instead of delivered (the API reports `emails_logged` separately).
- **Idempotency contract.** Retry-sensitive POST operations are idempotent.
  Workflow creation honors the `Idempotency-Key` header; assessment submission
  honors either the `Idempotency-Key` header or the body `idempotency_key`.
  Other endpoints are not guaranteed idempotent.
- **Generated artifacts.** `__pycache__`, `.pytest_cache`, `.next`,
  `node_modules`, and the design wireframe ZIPs in `design/wireframes/` are
  git-ignored and should not be shipped in release bundles.

