# ARIA — Phase 3: System Architecture

## Step 4 — Communication Architecture

**Status:** Draft v1

## Purpose

This document defines how components within ARIA communicate, when interactions are synchronous or asynchronous, and the architectural rules that govern reliable communication.

---

# Communication Principles

- Prefer synchronous communication for user-facing request/response workflows.
- Use asynchronous processing only for long-running or non-interactive work.
- Modules communicate through explicit interfaces rather than direct implementation access.
- Communication must be idempotent where retries are possible.
- Failures should not cascade across unrelated modules.

---

# Synchronous Workflows

Examples:

- Authentication
- Fetch learning context
- Start study session
- Submit assessment
- Retrieve learner_concept_state

These operations should provide immediate responses.

---

# Asynchronous Workflows

Examples:

- PDF ingestion
- Embedding generation
- Background indexing
- Email notifications
- Future audio generation

These should be processed independently of the learner's active request whenever practical.

---

# Communication Pattern

```text
Frontend
    │
    ▼
Application API
    │
    ├── Module Calls
    ├── AI Provider
    ├── Storage
    └── Background Jobs
```

The frontend communicates only with the application API. Internal modules communicate through defined service interfaces.

---

# Retry Strategy

Retryable operations must:

- avoid duplicate business effects;
- detect repeated requests;
- remain safe under network failures.

---

# Error Propagation

- Infrastructure failures should produce recoverable application errors.
- AI provider failures should not corrupt learner_concept_state.
- Partial failures must not create inconsistent evidence.

---

# Future Evolution

Future releases may introduce an event bus or message queue if operational evidence justifies additional complexity.

---

# Acceptance Criteria

- Communication rules are defined.
- Sync vs async responsibilities are identified.
- Retry philosophy is documented.
- Error propagation boundaries are established.
- Architecture remains suitable for modular growth.

---

## Next

Step 5 — State & Workflow Architecture.
