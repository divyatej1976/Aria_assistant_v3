# ARIA — Phase 7: API Architecture

## Step 6 — AI Service APIs

**Status:** Draft v1

## Purpose

This document defines the API boundaries for ARIA's AI capabilities. It separates AI services from business services so that reasoning, retrieval and adaptation remain modular, replaceable and independently evolvable.

---

# AI Service Domains

## Study Intelligence
Provides learning assistance and concept explanations.

## Assessment Intelligence
Generates assessments and evaluates responses.

## Evidence Intelligence
Processes validated learning evidence.

## Adaptation Intelligence
Produces personalized learning recommendations.

## Retrieval Intelligence
Coordinates semantic retrieval and RAG workflows.

---

# AI Service Principles

- AI services expose capabilities, not providers.
- AI outputs require validation before business use.
- Services remain provider-independent.
- AI services do not directly modify persistent state.
- Business services remain authoritative for state changes.

---

# Integration Principles

- Business services invoke AI services through stable contracts.
- AI services may use retrieval systems without exposing implementation details.
- Provider failures must degrade gracefully.

---

# Out of Scope

This document intentionally does not define:

- Prompt engineering.
- Model selection.
- Provider configuration.
- Internal LangGraph workflows.
- Endpoint implementation.

---

# Acceptance Criteria

- AI service domains documented.
- AI boundaries established.
- Integration principles defined.
- Ready for error handling and validation architecture.

---

## Next

Step 7 — Error Handling & Validation.