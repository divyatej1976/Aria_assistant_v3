# ARIA

ARIA is an AI Learning Operating System. This repository is the working implementation of the product, UX, architecture, AI, memory, API, agent, prompt, and technology planning captured in `docs/` and the wireframe design in `design/wireframes/` (see `docs/theme-system.md` for the frozen visual baseline).

## Current implementation scope

Phases 0–5 of the R0 adaptive-learning loop are implemented:

- Next.js frontend (Extruded Light design system, dark default + light theme);
- FastAPI backend with learner-owned domain model;
- PostgreSQL + Alembic migrations;
- server-side session registry (sign in/out, active devices, data reset);
- resources (text/PDF ingestion with retry and replace);
- grounded Study and topology knowledge map;
- deterministic MCQ assessment with idempotent submission;
- evidence → learner-state → adaptation loop with explainable decisions;
- Docker Compose development environment;
- CI that runs formatting, lint, type checks, and tests (SQLite and Postgres).

The R0 loop:

```text
Learning Context → Resources → Study → Assessment → Evaluation
→ Evidence → Learner State → Adapted Study → Reassessment
```

Notes, Audio, Planner, Progress, and MAO remain planned product areas. They are deliberately represented in the domain and workflow boundaries so they can be added without creating parallel systems.

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

