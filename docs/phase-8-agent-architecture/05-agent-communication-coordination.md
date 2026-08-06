# ARIA — Phase 8: Agent Architecture

## Step 5 — Agent Communication & Coordination

**Status:** Draft v1

## Purpose

This document defines how ARIA agents communicate, coordinate work and delegate responsibilities while preserving modularity, loose coupling and architectural boundaries.

---

# Communication Principles

- Agents communicate through defined interfaces.
- Agents exchange structured information, not implementation details.
- Communication should remain asynchronous where practical.
- Avoid direct dependencies between unrelated agents.

---

# Coordination Principles

- Delegate tasks to the most appropriate agent.
- Preserve single responsibility.
- Prevent circular delegation.
- Coordinate through APIs and orchestration layers.
- Record coordination events for observability.

---

# Handoff Rules

- Transfer validated context only.
- Preserve execution traceability.
- Maintain clear ownership during handoffs.
- Escalate when coordination cannot safely continue.

---

# Out of Scope

This document intentionally does not define:

- Runtime messaging technology.
- Queue implementation.
- Distributed systems.
- Multi-agent planning algorithms.
- Prompt exchange formats.

---

# Acceptance Criteria

- Communication principles documented.
- Coordination boundaries established.
- Handoff rules defined.
- Ready for Decision-Making & Planning architecture.

---

## Next

Step 6 — Decision-Making & Planning.