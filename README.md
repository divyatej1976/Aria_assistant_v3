# ARIA — AI Learning Operating System

ARIA is a learner-controlled, context-aware AI learning system designed to coordinate the parts of studying that are usually fragmented across multiple tools.

Instead of forcing every learner into the same subjects, exam formats, resources, or roadmap, ARIA builds the learning environment around **what the learner is actually preparing for**.

This repository contains the complete working implementation of the product, UX, architecture, AI, memory, API, agent, prompt, security, and technology planning captured in `docs/` (see `docs/theme-system.md` for the frozen visual baseline, `design/README.md` for wireframe design assets, and [DEMO.md](DEMO.md) for a comprehensive demo guide).

---

## 1. Product Vision & Learning Loop

```text
Learner Goal / Ingested Material
    ↓
Personalized Roadmap & Context Breakdown
    ↓
Resources + Grounded Socratic Study
    ↓
Notes + Spaced Revision Queue + PDF Export
    ↓
Learner-configured Diagnostic Assessments
    ↓
Evaluation + Structured Learning Evidence
    ↓
Evidence-backed Learner State Model
    ↓
Progress Heatmap, Streaks & Motivation Milestones
    ↓
Adaptive Roadmap, Exam Planner & Reminders
    ↓
Multi-Agent Orchestration & Governance
    ↺
```

---

## 2. Current Implementation Scope

Phases 0–12 of the adaptive-learning operating system and post-Phase-12 security/operational hardening are fully implemented:

- **Next.js Frontend**: Extruded Light design system, dark default + light theme, responsive layouts, accessible focus management, Playwright + Axe-core accessibility testing.
- **FastAPI Backend**: Learner-owned domain model, asynchronous SQLAlchemy with PostgreSQL and `pgvector` similarity search. (Prod = bundled PostgreSQL only; SQLite is a dev/test fallback and the backend refuses to boot it with `ARIA_ENV=production`.)
- **Database & Migrations**: Complete Alembic migration sequence (`0001` through `0014`), including email verification and account security.
- **Authentication & Security**: HttpOnly `SameSite=Strict` cookie sessions, double-submit CSRF tokens, sliding-window rate limiting, and secure password-reset / email-verification flows.
- **Resource Ingestion**: Text and PDF ingestion pipeline with concept extraction, chunking, and vector embeddings.
- **Grounded Study**: Multimodal Socratic study interface, voice speech-to-text input, and concept topology knowledge map.
- **Adaptive Assessments**: Deterministic & AI-generated MCQ assessments with idempotent submission, immediate scoring, and concept-linked evidence logs.
- **Learner Memory & Evidence**: Dynamic learner mastery modeling, preferences, context assembly, prerequisite detection, and memory inspector.
- **Notes & Spaced Revision**: Automated note generation, spaced repetition queues, revision tracking, and client-side PDF export.
- **Progress & Consistency**: Meaningful-learning streaks, GitHub/contribution-style activity heatmap, and achievement badges.
- **Planner & Reminders**: Exam milestones, study tasks, missed-work recovery, in-app notifications, and scheduled email reminders (APScheduler with PostgreSQL advisory-lock guards).
- **Multi-Agent Orchestration**: Workflow orchestration with human approval gates, audit trails, idempotent execution replay, and AI cost budget management.
- **Deployment & Production Ready**: Production Dockerfiles, `docker-compose.prod.yml`, automated `pg_dump` backup/restore scripts, and Prometheus `/metrics` monitoring.

---

## 3. Local Development & Setup

For a full interactive walkthrough and test guide, refer to **[DEMO.md](DEMO.md)**.

### Backend Setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_local.ps1
.\.venv\Scripts\python.exe scripts\check_deps.py
.\.venv\Scripts\python.exe -m pytest
```

Manual alternative:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --app-dir backend
```

- Backend API: <http://localhost:8000>
- Health check: <http://localhost:8000/health>
- OpenAPI Documentation: <http://localhost:8000/docs>

### Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

- Frontend App: <http://localhost:3000>

### Database Migrations

```powershell
docker compose up -d db          # start PostgreSQL
alembic upgrade head             # apply all database migrations
```

### Docker Compose (Production Setup — Bundled PostgreSQL Only)

> Bundled `db` is the only supported prod model until an external-DB compose file exists.
> Compose alone exposes `3000/8000`; a reverse proxy must route `public domain → frontend:3000`, `/api/* → backend:8000` + TLS.
> Generate a URL-safe DB password `^[A-Za-z0-9._~-]+$` (no `: / @ #`).

```powershell
$env:POSTGRES_PASSWORD="example-UrlSafe_2x9.~-password"
$env:DATABASE_URL="postgresql+psycopg://aria:$env:POSTGRES_PASSWORD@db:5432/aria"
$env:ARIA_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
$env:ARIA_CORS_ORIGINS="https://your-domain.com"
$env:ARIA_TRUSTED_HOSTS="your-domain.com,localhost,127.0.0.1"
$env:ARIA_PUBLIC_URL="https://your-domain.com"
$env:NEXT_PUBLIC_API_URL="https://your-domain.com"
# SMTP/Groq/semantic required for unrestricted prod:
$env:SMTP_HOST="smtp.example.com"; $env:SMTP_FROM="ARIA <noreply@your-domain.com>"
$env:GROQ_API_KEY="..."

python scripts/check_prod_secrets.py --strict --ai-tutoring --semantic-enabled
docker compose -f docker-compose.prod.yml config --quiet  # never log plain config (secrets)
docker compose -f docker-compose.prod.yml up -d --build
curl http://localhost:8000/ready   # readiness DB ok (bundled proxy routes /ready -> backend:8000)
curl http://localhost:8000/health  # liveness
```

---

## 4. Architecture Rules

1. Route handlers coordinate; domain services own business rules.
2. Repositories own persistence access.
3. Provider-specific SDKs stay behind interfaces.
4. Learner-owned records require an owner identity.
5. Consequential workflows must be idempotent and auditable.
6. Memory, evidence, learner state, and mastery claims are separate concepts.
7. Deterministic logic stays deterministic; AI does not decide authorization or MCQ correctness.

---

## 5. Security & Production Notes

### Required Production Environment Variables

| Variable | Purpose | Failure if missing |
| --- | --- | --- |
| `ARIA_SESSION_SECRET` | Signs session/action tokens | Backend refuses to start (`ARIA_ENV=production`) |
| `DATABASE_URL` | Backend + migrations connection | Backend/migrate cannot connect |
| `ARIA_CORS_ORIGINS` | Allowed browser origins | Frontend API calls rejected by CORS |
| `ARIA_TRUSTED_HOSTS` | Host allowlist (prod only) | Requests with other `Host` headers rejected |
| `NEXT_PUBLIC_API_URL` | Frontend API base URL (drives CSP `connect-src`) | API calls target `http://localhost:8000` |
| `ARIA_PUBLIC_URL` | Base URL for links in emails (reset/verify) | Emails link to `http://localhost:3000` |

---

*For detailed demo scenarios, test commands, and architectural notes, see [DEMO.md](DEMO.md).*
