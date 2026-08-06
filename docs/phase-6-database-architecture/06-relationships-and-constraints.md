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

## Learner → learner_concept_state
One learner has many computed concept states.

## Concept → learner_concept_state
One concept has many learner states.

## Evidence → learner_concept_state
Multiple pieces of validated evidence update a single learner's state for a specific concept.

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