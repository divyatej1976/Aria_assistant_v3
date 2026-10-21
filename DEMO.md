# ARIA — Evaluator Guide

Start here. This page explains what ARIA is, how to run it, and what to try in five minutes.

## What it is

ARIA is an AI study companion. A learner says what they are preparing for (an exam, an interview, a subject), and ARIA builds the study environment around that goal:

- **Plan**: a roadmap of milestones, each with its outcome, effort, activity and a check.
- **Learn**: a tutor chat that answers from the learner's own documents when it can, and says so when it can't.
- **Practice**: quizzes generated from a chat, a document or a topic, followed by a debrief.
- **Library and Audio**: upload PDFs and images (read with OCR), and turn notes or chats into audio.
- **Progress**: streaks, an activity heatmap and a topic map built from quiz evidence.

Stack: Next.js frontend (`frontend-v2/`), FastAPI backend (`backend/`), SQLite for local runs (PostgreSQL with pgvector in production), Groq for the language model.

## How to run (Windows, Python 3.11+, Node 20+)

From the project folder:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_local.ps1   # Python venv + packages
cd frontend-v2; npm install; cd ..
copy .env.example .env      # then set GROQ_API_KEY=gsk_... (free at console.groq.com/keys)
.venv\Scripts\python.exe scripts\dev.py   # starts the backend on :8000 and the app on :3000
```

Open <http://localhost:3000> and sign up with any email address. No email is sent locally.

Without a Groq key the app still runs, but tutor answers fall back to excerpts from uploaded documents and roadmaps use a general starter plan. A key can also be added later in **Account**.

## 5-minute walkthrough

1. **Sign up → onboarding.** Pick a subject and goal. Home then suggests a first step.
2. **Plan → Roadmap.** Create a roadmap (goal, level, hours per week, deadline). Open a milestone to see its outcome, effort and check, then press **Study** on it.
3. **Learn.** Ask something like "Explain conditional probability with an example." Answers come in short labelled blocks, with formulas rendered as math. Try **Go deeper** / **Shorter**, then **Quick check** to get a quiz on the chat.
4. **Practice.** Take the quiz. Try flagging a question and the review screen before submitting, then read the debrief.
5. **Library.** Upload a PDF or a photo of notes, then ask about it in Learn. The reply says "From your material" and names the file.
6. **Audio and Progress.** Turn a chat into audio, then see the streak, heatmap and topic map update.

## Key folders

| Folder | What's in it |
|---|---|
| `frontend-v2/` | The app (Next.js). `app/app/*` holds the pages, `components/` the UI. |
| `backend/app/` | The API (FastAPI): `api/routes`, `services` (tutor, roadmap, quizzes, OCR, audio), `assessment`, `db` |
| `database/` | Alembic migrations |
| `tests/` | Backend tests (pytest). Browser tests are in `frontend-v2/tests` (Playwright). |
| `docs/` | Design work by phase (research, PRD, UX, architecture, AI, data, API, security) and review reports |
| `VISION.md`, `BUILD_PLAN.md` | The full product vision and the build plan |
| `frontend/` | **Retired** first version of the app. It is kept for reference only; ignore it. |

## Status

- **Working:** everything in the walkthrough, plus sign-in security (HttpOnly cookies, CSRF, rate limits), password reset, exam planner and reminders, and Docker production files.
- **Tested:** about 590 backend tests and about 150 browser tests (including accessibility checks), last reviewed 16 Oct 2026. See `docs/current-app-testing-2026-10-16.md`. The four quiz bugs that review found have since been fixed.
- **Known limits:**
  - Answer quality depends on the Groq model.
  - Tutor images appear only from Wikimedia.
  - One audio test is timing-sensitive and occasionally fails.
  - Production use needs PostgreSQL and the secrets listed in `README.md`.
