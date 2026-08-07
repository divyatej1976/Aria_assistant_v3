# ARIA — Phase 8: Agent Architecture

## Step 4 — Agent Lifecycle

**Status:** Draft v1

## Purpose

This document defines the standard lifecycle that every ARIA agent follows from task reception through completion or recovery. A consistent lifecycle improves predictability, observability and reliability across all agents.

---

# Standard Agent Lifecycle

1. Receive Task
2. Validate Context
3. Plan Actions
4. Acquire Required Information
5. Execute Through APIs
6. Observe Results
7. Determine Next Action
8. Complete or Escalate
9. Record Execution Metadata

---

# Lifecycle Principles

- Every task begins with context validation.
- Planning precedes execution.
- Agents execute through APIs only.
- Failures trigger controlled recovery or escalation.
- Execution remains observable and auditable.

---

# Failure & Recovery

- Detect execution failures.
- Retry only when safe.
- Escalate unrecoverable failures.
- Preserve execution history.
- Never corrupt business state.

---

# Out of Scope

This document intentionally does not define:

- Runtime scheduling.
- Prompt execution.
- LLM provider behavior.
- Multi-agent workflows.
- Retry algorithms.

---

# Acceptance Criteria

- Standard lifecycle defined.
- Recovery principles documented.
- Lifecycle responsibilities established.
- Ready for Agent Communication & Coordination.

---

## Next

Step 5 — Agent Communication & Coordination.
