# Phase 10 — Technology Decisions

## Step 8 — R0 vs Production vs Scale Stack

**Status:** Frozen v1 — amended after R0 scope review

---

# Purpose

This document consolidates all technology decisions into a single implementation roadmap. It defines which technologies belong in each stage of ARIA's evolution and ensures operational complexity grows only when justified by product maturity.

---

# R0 Stack

## Frontend
- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui

## Backend
- FastAPI
- Python
- Pydantic v2
- SQLAlchemy 2.x
- Alembic

## AI
- LiteLLM
- Groq
- Native Structured Outputs

LangChain and LangGraph are intentionally excluded from the R0 runtime dependency set.

## Database
- Supabase (PostgreSQL, Auth, Storage, RLS)
- pgvector

## Documents
- PyMuPDF

## Testing
- Pytest
- Playwright

## Infrastructure
- Docker
- Docker Compose

---

# Production Stack (v1)

Everything in R0 plus:

## AI
- LangChain, when concrete integration or retrieval capabilities justify it
- LangGraph, when workflow branching or stateful orchestration justifies it
- Gemini
- OpenAI

## Database
- Qdrant

## Performance
- Redis

## Monitoring
- Sentry
- Langfuse

## Documents
- Unstructured
- python-docx
- Pandas
- BeautifulSoup
- markdown-it

---

# Scale Stack (v2)

Everything in Production v1 plus:

## Background Processing
- Celery (or ARQ after evaluation)

## Observability
- OpenTelemetry
- Prometheus
- Grafana

## Infrastructure
- Nginx (or managed cloud equivalent)
- Advanced CI/CD
- Horizontal scaling
- Infrastructure automation

---

# Evolution Principles

- R0 validates the adaptive-learning hypothesis.
- Production v1 supports sustained real-world usage.
- Scale v2 addresses operational growth.
- No technology enters the stack before solving a demonstrated problem.
- Framework abstractions are introduced only when their capabilities provide a concrete benefit.

---

# Acceptance Criteria

- Unified technology roadmap created
- R0 stack finalized
- Production roadmap finalized
- Scale roadmap finalized
- Elimination test consistently applied to AI framework dependencies

---

## Next

Step 9 — Technology Review