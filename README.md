# ARIA — AI Learning System

ARIA is an AI tutor that organises your studying around **what you are actually preparing for**: a course, an exam, a skill or a job interview. Each subject gets its own chats, files, quizzes, roadmap and progress, and everything ARIA claims about what you know is backed by evidence from your own answers.

| Home | Learn (Noir theme) |
| --- | --- |
| ![Home dashboard](docs/screenshots/verification/aurora-1440-dashboard-progress.png) | ![Tutor chat](docs/screenshots/verification/noir-1440-learn-focus.png) |
| **Roadmap** | **Practice** |
| ![Roadmap milestones](docs/screenshots/verification/aurora-1440-roadmap-expanded-states.png) | ![Quiz scores](docs/screenshots/verification/aurora-1440-assess-scores.png) |

---

## What you can do

- **Learn** — chat with a tutor that answers in short, labelled blocks and adapts to the depth you pick (Auto, Quick, Balanced, Deep). Ask it to *quiz you* and it asks one question and waits; answer it and you get a clear *Correct / Partly right / Not quite*. Attach a PDF or image to a chat, or speak your question.
- **Library** — add PDFs, images (OCR) and notes that every chat in the subject can use. Answers say what came *from your document* and what ARIA added *beyond* it.
- **Practice** — quiz yourself on your chats, your library, a topic or your weak spots. Presets (Quick practice, Topic test, Mock exam), multiple choice, true/false and short answer, timers, flag-for-review, and a debrief that explains what each mistake says about your understanding.
- **Plan** — turn a goal into a roadmap with milestones (outcome, effort, activity, check), a "this week" view, exam dates and deadlines, and reminders.
- **Audio** — turn a chat, notes or pasted text into an episode to listen to on the go.
- **Progress** — streaks, a 26-week activity heatmap, badges, and a topic map where each concept is *untested*, *developing*, *needs review* or *strong* — based on quiz evidence, never on the AI's opinion.
- **Account** — export everything ARIA stores, delete a subject or all your data, see and revoke signed-in devices, and optionally use your own Groq key.

Two palettes (Aurora light, Noir dark), responsive down to 320 px, keyboard accessible and checked with axe.

---

## How it works

```text
Goal or material ─► Roadmap ─► Tutor chats (grounded in your files)
       ▲                                 │
       │                                 ▼
 Adaptive plan ◄─ Learner state ◄─ Quiz answers = evidence
```

**Architecture rules**

1. Route handlers coordinate; services own business rules.
2. Every learner-owned record carries an owner and is checked on access.
3. Consequential actions are idempotent and auditable (retries never double-submit a quiz or double-create audio).
4. Memory, evidence, learner state and mastery are separate concepts.
5. Deterministic logic stays deterministic: the AI never decides authorisation or whether an answer is correct.

**Stack**

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 16, React 19, Tailwind CSS 4, Motion; Playwright + axe-core tests |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2, Alembic (32 migrations), APScheduler |
| AI | Groq via LiteLLM (default `openai/gpt-oss-120b`), LangGraph for chat actions, Groq speech-to-text / text-to-speech |
| Data | PostgreSQL 16 + pgvector in production; SQLite for local development and tests |
| Security | HttpOnly `SameSite=Strict` session cookies, double-submit CSRF, database-backed rate limits, encrypted per-learner API keys, email verification and password reset |

Design and planning documents live in [`docs/`](docs/) (product, architecture, AI, memory, database, API, security), with the visual system in [`docs/theme-system.md`](docs/theme-system.md) and a walkthrough in [DEMO.md](DEMO.md).

---

## Run it locally

**One-time setup** (Windows PowerShell; Python 3.11+ and Node 20+):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_local.ps1
cd frontend-v2; npm install; cd ..
```

Copy `.env.example` to `.env` and add a `GROQ_API_KEY` for AI answers. Without one, ARIA still runs and uses labelled offline fallbacks.

**Start everything with one command:**

```powershell
python scripts/dev.py                                # API :8000, app :3000, SQLite aria-dev.db
python scripts/dev.py --api-port 8030 --web-port 3030
```

It checks the ports, applies migrations, starts the backend and frontend, and confirms they can talk to each other. Set `DATABASE_URL` to use PostgreSQL instead of SQLite.

- App: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>

---

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest                 # ~600 backend tests (SQLite)
$env:TEST_DATABASE_URL="postgresql+psycopg://aria:aria@localhost:5432/aria_test"; .\.venv\Scripts\python.exe -m pytest
cd frontend-v2; npx tsc --noEmit; npx eslint app components lib; npx playwright test
```

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs a secrets scan, ruff, a dependency audit, the backend suite on SQLite and on PostgreSQL with pgvector, and an Alembic upgrade → downgrade → upgrade round trip.

---

## Deploy

### Render (recommended)

[`render.yaml`](render.yaml) is a Render Blueprint: managed PostgreSQL 16 with pgvector, a private backend and frontend, and a public Caddy proxy so the app and `/api` share one origin (the session cookies require it).

1. In Render: **New → Blueprint**, pick this repository and branch.
2. Enter the values it asks for: your public URL (for example `https://aria.onrender.com`) for `ARIA_PUBLIC_URL`, `ARIA_CORS_ORIGINS` and `NEXT_PUBLIC_API_URL`; the host alone for `ARIA_TRUSTED_HOSTS`; `GROQ_API_KEY`; an encryption key from `python scripts/generate_llm_keys_key.py`; and SMTP details for verification and reset emails.
3. Deploy. Migrations run before each backend release; check `/healthz` and `/ready`.

### Docker Compose on your own server

`docker-compose.prod.yml` runs PostgreSQL, a one-off migration job, the backend, the frontend and Caddy with automatic HTTPS:

```powershell
python scripts/check_prod_secrets.py --strict --ai-tutoring
docker compose -f docker-compose.prod.yml up -d --build
```

The compose file lists every required variable; the backend refuses to start in production without a PostgreSQL database and a strong `ARIA_SESSION_SECRET`.

Both production configurations enable `ARIA_BRAIN_ROUTING`: in Learn, ask
"Make audio from this chat" to create an audio action. LangGraph saves only
identifiers and execution status in PostgreSQL checkpoints, initialized before
the backend accepts requests. Startup serializes checkpoint schema setup across
workers. Set `ARIA_BRAIN_ROUTING=false` to disable chat actions; normal tutoring
and the Audio page remain available. Local SQLite development is opt-in via the
same flag and uses `ARIA_BRAIN_CHECKPOINT_PATH` for checkpoints. This workflow
creates audio from the current chat; general note-selection commands are not
enabled by the deterministic router.

---

## Project status

ARIA is feature-complete for a **private beta**. Before opening sign-ups widely:

- **AI capacity** — Groq's free tier allows 8,000 tokens per minute *shared by all users*; a paid tier is needed beyond a handful of active learners.
- **Legal pages** — a privacy policy and terms are not written yet.
- **Live verification** — run the deployment, email delivery and a backup restore on the real host.

---

See [DEMO.md](DEMO.md) for a guided tour and test scenarios.
