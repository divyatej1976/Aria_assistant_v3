# ARIA — Phase 6: Database Architecture

## Step 3 — Core Entity Model

**Status:** Draft v1

## Purpose

This document defines the core business entities that make up ARIA's relational data model. It establishes each entity's responsibility and the high-level relationships between them before translating the design into database schemas.

---

# Core Entities

## Learner
Represents a user and their persistent learning profile.

## StudySession
Represents an active or completed learning session.

## Conversation
Represents a logical conversation between the learner and ARIA.

## Message
Represents individual learner or AI messages.

## Topic
Represents a learning topic.

## Concept
Represents an individual learning concept within a topic.

## Assessment
Represents quizzes, evaluations and reassessments.

## Evidence
Represents validated learning evidence.

## Resource
Represents uploaded or managed learning material.

## ResourceChunk
Represents extracted searchable content from resources.

## learner_concept_state

**Purpose:**
Stores the current computed state of a learner for each concept.
This is derived from validated evidence and serves as the authoritative
persistent learner model used by adaptation and study planning.

**Columns:**
- id (PK)
- learner_id (FK -> learners.id)
- concept_id (FK -> concepts.id)
- mastery_score
- confidence_score
- status
- evidence_count
- last_evidence_at
- last_updated
- state_version

**Architectural Notes:**
*Design Principles*
- Evidence remains immutable.
- learner_concept_state is a derived projection built from validated evidence.
- Only validated evidence may update learner_concept_state.
- Adaptation Intelligence consumes learner_concept_state rather than raw evidence.
- Historical evidence remains preserved for auditability and reproducibility.

**Relationships:**
```text
Learner
   │
   ├───────────────┐
   │               │
Evidence      learner_concept_state
                     │
                     │
                 Concept
```

---

# Entity Principles

- One clear responsibility per entity.
- Prefer composition over duplication.
- Preserve auditability.
- Maintain stable identifiers.
- Separate logical entities from implementation details.

---

# High-Level Relationships

- Learner owns Study Sessions.
- Study Sessions contain Conversations.
- Conversations contain Messages.
- Assessments generate Evidence.
- Evidence contributes to Learner State.
- Resources produce Resource Chunks.
- Resource Chunks support Retrieval.

---

# Out of Scope

This document intentionally does not define:

- Table definitions.
- Foreign key implementation.
- SQL types.
- Indexes.
- ORM mappings.

---

# Acceptance Criteria

- Core entities identified.
- Responsibilities defined.
- High-level relationships documented.
- Ready for relational schema design.

---

## Next

Step 4 — Relational Schema Design.