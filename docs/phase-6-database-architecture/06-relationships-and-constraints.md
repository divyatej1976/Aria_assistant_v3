# ARIA — Phase 6: Database Architecture

## Step 6 — Relationships & Constraints

**Status:** Draft v1

## Purpose

This document defines how ARIA's database entities relate to one another and the integrity constraints that preserve consistency across the relational model.

---

# Relationship Principles

- Every relationship has a clear owner.
- Prefer explicit foreign keys.
- Preserve referential integrity.
- Model real business relationships.
- Avoid redundant links.

---

# Core Relationships

## Learner → StudySession
One learner may have many study sessions.

## StudySession → Conversation
One study session may contain multiple conversations.

## Conversation → Message
One conversation contains many messages.

## Assessment → Evidence
One assessment may generate multiple evidence records.

## Learner → Evidence
A learner owns many evidence records.

## Learner State Relationships

```
Learner
    │
    ├────────────── learner_concept_state
    │                    │
    │                    │
    │                Concept
    │
    └────────────── Evidence
```

Relationship Rules

- A learner may have many learner concept states.
- Each learner concept state belongs to exactly one learner.
- Each learner concept state references exactly one concept.
- A learner may have at most one learner concept state for a given concept.
- Learner concept state is derived from validated evidence but does not replace evidence persistence.
- Evidence remains immutable and serves as the historical foundation for learner state computation.

## Resource → ResourceChunk
One resource produces many chunks.

## ResourceChunk → Vector Record
Each chunk is represented by one vector embedding record.

---

# Constraint Principles

- Primary keys uniquely identify records.
- Foreign keys preserve relationships.
- Required relationships should not be nullable.
- Cascading behavior should be explicit.
- Uniqueness constraints should reflect business rules.

---

# Design Goals

- Strong data integrity.
- Predictable ownership.
- Efficient joins.
- Support future extensibility.

---

# Out of Scope

This document intentionally does not define:

- SQL constraint syntax.
- Index implementation.
- Query optimization.
- Migration scripts.
- ORM relationships.

---

# Acceptance Criteria

- Core relationships documented.
- Integrity principles established.
- Constraint strategy defined.
- Ready for indexing and performance design.

---

## Next

Step 7 — Indexing & Performance Strategy.