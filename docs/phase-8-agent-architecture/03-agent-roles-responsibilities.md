# ARIA — Phase 8: Agent Architecture

## Step 3 — Agent Roles & Responsibilities

**Status:** Draft v1

## Purpose

This document defines the logical agent roles within ARIA and establishes clear responsibility boundaries. Each agent owns a specific orchestration responsibility while relying on existing APIs and business services for execution.

---

# R0 Agent Roles

## Study Agent
Coordinates study sessions and learning workflows.

## Assessment Agent
Coordinates assessment generation and evaluation workflows.

## Retrieval Agent
Coordinates semantic retrieval and context acquisition.

## Adaptation Agent
Coordinates personalized learning recommendations.

## Conversation Agent
Coordinates conversational flow and interaction continuity.

---

# Responsibility Principles

- One primary orchestration responsibility per agent.
- Agents consume APIs instead of internal implementation.
- Agents do not directly modify persistent state.
- Agents may collaborate through defined coordination mechanisms.
- Business services remain authoritative.

---

# Ownership Boundaries

Agents own:
- Planning
- Coordination
- Decision orchestration

Agents do not own:
- Database access
- Authentication
- Business rules
- API implementation
- UI logic

---

# R0 Implementation Guidance

The agent roles defined in this document represent **logical architectural
responsibilities**, not mandatory runtime processes.

For the initial R0 implementation, ARIA is expected to use the smallest
practical number of runtime orchestrators while preserving the responsibility
boundaries defined here.

For example, multiple logical responsibilities may be implemented within a
single orchestration graph or workflow if doing so maintains architectural
clarity and does not violate separation of concerns.

Separate runtime agents should be introduced only when justified by clear
capability, scalability, or operational requirements rather than architectural
preference alone.

---

# Out of Scope

This document intentionally does not define:

- Agent lifecycle.
- Communication protocols.
- Prompt design.
- Runtime scheduling.
- Multi-agent execution.

---

# Acceptance Criteria

- R0 agent roles defined.
- Responsibility boundaries documented.
- Ownership principles established.
- Ready for Agent Lifecycle architecture.

---

## Next

Step 4 — Agent Lifecycle.
