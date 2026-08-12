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

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --app-dir backend
```

> **Windows note:** if `pip install -e ".[dev]"` fails to build the editable wheel with a
> `UnicodeEncodeError` (this happens when the repository path contains non-ASCII characters),
> install the dependencies directly instead — `pytest` resolves `app` via `pythonpath`:

```powershell
pip install fastapi "uvicorn[standard]" pydantic-settings sqlalchemy alembic "psycopg[binary]" pymupdf litellm httpx pytest pytest-asyncio ruff
```

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

