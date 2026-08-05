# ARIA — Phase 6: Database Architecture

## Step 7 — Indexing & Performance Strategy

**Status:** Draft v1

## Purpose

This document defines the indexing and performance strategy for ARIA's persistence layer. It establishes architectural principles that support efficient querying, scalable growth and predictable database performance without coupling optimization to business logic.

---

# Performance Principles

- Optimize for common access patterns.
- Index intentionally, not excessively.
- Keep write performance balanced with read performance.
- Separate relational and vector optimization strategies.
- Measure before optimizing.

---

# Indexing Strategy

Primary indexes:
- Primary keys
- Foreign keys where appropriate

Secondary indexes:
- Frequently queried learner identifiers
- Session lookups
- Resource metadata
- Assessment history

Vector indexes remain the responsibility of the vector database.

---

# Query Strategy

- Prefer indexed lookups.
- Support pagination for large datasets.
- Avoid unnecessary joins.
- Retrieve only required columns.
- Design for predictable query performance.

---

# Scalability Goals

- Support increasing learner volume.
- Support growing evidence history.
- Maintain retrieval responsiveness.
- Allow future partitioning if required.

---

# Out of Scope

This document intentionally does not define:

- Database-specific tuning parameters.
- SQL execution plans.
- Hardware sizing.
- Cache implementation.
- Provider-specific optimizations.

---

# Acceptance Criteria

- Performance principles documented.
- Indexing strategy established.
- Query guidance defined.
- Ready for migration and versioning design.

---

## Next

Step 8 — Migration & Versioning.