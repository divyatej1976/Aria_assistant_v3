# ARIA — Phase 6: Database Architecture

## Step 4 — Relational Schema Design

**Status:** Draft v1

## Purpose

This document defines the high-level relational schema for ARIA. It translates the core entity model into relational tables while preserving normalization, data integrity and maintainability.

---

# Relational Design Principles

- One table per core business entity.
- Prefer normalization over duplication.
- Use surrogate primary keys.
- Preserve referential integrity.
- Keep business logic outside the database.

---

# Primary Tables

- learners
- study_sessions
- conversations
- messages
- topics
- concepts
- assessments
- evidence
- resources
- resource_chunks

Supporting tables may be introduced where relationships require normalization.

---

## learner_concept_state

### Purpose

The `learner_concept_state` table stores the current computed learning state
for each learner–concept pair.

Unlike the `evidence` table, which stores immutable observations, this table
represents the latest derived understanding of a learner's mastery for a
concept. It serves as the authoritative source for personalization,
adaptation, and study planning.

---

### Primary Fields

| Field | Description |
|--------|-------------|
| id | Primary Key |
| learner_id | Foreign Key → learners.id |
| concept_id | Foreign Key → concepts.id |
| mastery_score | Current computed mastery level |
| confidence_score | Confidence in the mastery estimate |
| status | Current learning status (e.g. Not Started, Learning, Mastered) |
| evidence_count | Number of validated evidence records contributing to this state |
| last_evidence_at | Timestamp of the latest evidence incorporated |
| last_updated | Timestamp of the most recent learner state computation |
| state_version | Version identifier for the learner state computation |

---

### Relationships

- learner_id → learners.id
- concept_id → concepts.id

Each learner may have one learner state for each concept.

---

### Constraints

Unique Constraint

(learner_id, concept_id)

Indexes

- learner_id
- concept_id
- mastery_score
- last_updated

---

### Design Notes

This table is intentionally a derived projection rather than a source of raw
observations.

Its values are produced by aggregating validated evidence collected during
learning activities.

Application components responsible for personalization and adaptive learning
consume learner state from this table rather than calculating mastery directly
from raw evidence during every request.

The evidence table remains immutable and continues to act as the historical
record supporting learner state calculations.

---

# Schema Strategy

- Stable primary keys for all entities.
- Foreign keys model entity relationships.
- Nullable fields used only when semantically appropriate.
- Audit fields included where required.
- Soft deletion preferred for user-owned data where governance requires recoverability.

---

# Design Goals

- Data consistency.
- Efficient querying.
- Future extensibility.
- Maintainable migrations.
- Clear ownership boundaries.

---

# Out of Scope

This document intentionally does not define:

- Exact SQL DDL.
- Index definitions.
- ORM classes.
- Vector database schema.
- Database tuning.

---

# Acceptance Criteria

- Relational schema strategy defined.
- Core tables identified.
- Design principles documented.
- Ready for vector database architecture.

---

## Next

Step 5 — Vector Database Architecture.