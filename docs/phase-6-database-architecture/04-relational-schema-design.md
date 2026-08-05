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