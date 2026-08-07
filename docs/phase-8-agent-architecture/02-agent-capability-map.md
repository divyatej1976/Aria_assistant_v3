# ARIA — Phase 8: Agent Architecture

## Step 2 — Agent Capability Map

**Status:** Draft v1

## Purpose

This document identifies the major autonomous capabilities required within ARIA before defining individual agents. It maps responsibilities to capability domains, ensuring agents are introduced because a capability exists—not because a specific AI framework supports them.

---

# Core Agent Capability Domains (R0)

## Study Orchestration
- Coordinate study workflows
- Guide learning sessions
- Sequence learning activities

## Assessment Coordination
- Coordinate assessment lifecycle
- Manage evaluation workflows

## Retrieval Coordination
- Coordinate semantic retrieval
- Manage resource discovery

## Adaptation Planning
- Produce personalized study plans
- Recommend learning adjustments

## Evidence Coordination
- Coordinate evidence processing
- Trigger learner_concept_state updates through business services

## Conversation Coordination
- Manage conversational workflows
- Preserve interaction continuity

---

# Future Capability Domains

- Career Planning
- Collaboration
- Long-term Goal Planning
- Multi-agent delegation
- External tool orchestration

---

# Mapping Principles

- Capabilities drive agent design.
- One capability may involve multiple agents.
- Agents remain loosely coupled.
- Capabilities evolve independently where practical.

---

# Out of Scope

This document intentionally does not define:

- Individual agent implementations.
- Prompt strategies.
- LLM selection.
- Agent communication protocols.
- Runtime execution.

---

# Acceptance Criteria

- Core capability domains identified.
- Future capabilities documented.
- Capability boundaries established.
- Ready for Agent Roles & Responsibilities.

---

## Next

Step 3 — Agent Roles & Responsibilities.
