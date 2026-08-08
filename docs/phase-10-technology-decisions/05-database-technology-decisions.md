# Phase 10 — Technology Decisions

## Step 5 — Database Technology Decisions

**Status:** Frozen v1

---

# Purpose

This document evaluates ARIA's persistence technologies and explains why each database decision was made. The objective is to keep R0 operationally simple while preserving a clear migration path toward a production-scale architecture.

---

# Evaluation Criteria

- Alignment with Phase 6 Database Architecture
- Simplicity for R0
- Scalability
- Operational complexity
- AI retrieval support
- Authentication & storage capabilities
- Long-term maintainability

---

# Relational Database

## PostgreSQL

**Decision:** ✅ Selected

### Why

- Mature relational database
- Excellent SQL support
- JSONB for semi-structured data
- Strong ecosystem
- Native pgvector support
- Excellent compatibility with SQLAlchemy

---

## MySQL

**Decision:** ❌ Rejected

Strong database but weaker ecosystem for AI-oriented extensions and vector search.

---

## MongoDB

**Decision:** ❌ Rejected

Flexible schema, but ARIA's data model is highly relational and benefits from ACID guarantees.

---

# Backend Platform

## Supabase

**Decision:** ✅ Selected for R0

Provides:

- Managed PostgreSQL
- Authentication
- Storage
- Row Level Security
- Dashboard
- Backups

This significantly reduces operational complexity without compromising architectural flexibility.

---

## Alternatives

### Neon

Excellent managed PostgreSQL but does not provide integrated authentication and storage.

### Firebase

Excellent BaaS but document-oriented and less aligned with ARIA's relational architecture.

### Appwrite

Strong open-source platform but smaller ecosystem than Supabase.

---

# Vector Search

## pgvector

**Decision:** ✅ Selected for R0

Reasons:

- Single database deployment
- Simpler backups
- Lower operational overhead
- Sufficient for R0 retrieval requirements

---

## Qdrant

**Decision:** ⏳ Production v1

Introduced once retrieval scale, filtering capabilities, or ANN performance exceed pgvector's practical limits.

---

## Alternatives

- Pinecone
- Weaviate
- Milvus

Rejected for R0 due to additional infrastructure and operational complexity.

---

# Search Strategy

R0 uses:

- PostgreSQL Full-Text Search
- pgvector Semantic Search

Production introduces Hybrid Retrieval combining lexical and semantic search.

---

# Architecture Principles

- Prefer one database until evidence justifies separation.
- Keep vector and relational data together during R0.
- Introduce dedicated vector databases only when required.
- Maintain provider independence wherever practical.

---

# Final Database Stack

## R0

- Supabase
- PostgreSQL
- pgvector

## Production v1

Adds:

- Qdrant

---

# Acceptance Criteria

- Database technologies evaluated
- Alternatives documented
- R0 and Production responsibilities defined
- Database decisions frozen

---

## Next

Step 6 — Infrastructure Technology Decisions