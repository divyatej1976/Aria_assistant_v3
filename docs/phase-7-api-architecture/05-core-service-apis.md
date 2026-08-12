# ARIA — Phase 7: API Architecture

## Step 5 — Core Service APIs

**Status:** Draft v1

## Purpose

This document defines the primary business service APIs that form ARIA's application layer. It establishes service boundaries and responsibilities before individual endpoints are designed.

---

# Core Services

## Learner Service
Responsible for learner profile, preferences, goals and progress.

## Study Service
Responsible for study sessions, learning workflows and topic management.

## Conversation Service
Responsible for conversations, chat history and message management.

## Assessment Service
Responsible for assessments, submissions and results.

## Resource Service
Responsible for resource upload, metadata and retrieval coordination.

## Evidence Service
Responsible for evidence records and learner_concept_state updates.

---

# Service Principles

- One business responsibility per service.
- Services communicate through stable contracts.
- Services remain implementation-independent.
- Business rules remain inside services.
- Persistence remains hidden behind service boundaries.

---

# Cross-Service Communication

Services may collaborate through defined APIs but should avoid unnecessary coupling. Shared business workflows should be orchestrated by the application layer rather than creating circular dependencies.

---

# Out of Scope

This document intentionally does not define:

- Individual endpoints.
- HTTP methods.
- Database operations.
- AI orchestration.
- Internal implementation.

---

# Acceptance Criteria

- Core services identified.
- Responsibilities documented.
- Service boundaries established.
- Ready for AI Service API architecture.

---

## Next

Step 6 — AI Service APIs.
