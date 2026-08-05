# ARIA — Phase 6: Database Architecture

## Step 5 — Vector Database Architecture

**Status:** Draft v1

## Purpose

This document defines how ARIA stores and retrieves semantic information using a vector database. It establishes the architectural boundary between relational storage and vector storage while supporting Retrieval-Augmented Generation (RAG).

---

# Responsibilities

The Vector Database is responsible for:

- Storing embeddings.
- Organizing resource chunks.
- Supporting semantic similarity search.
- Returning relevant retrieval candidates.
- Storing retrieval metadata.

The vector database is not the source of truth for learner data or business entities.

---

# Stored Objects

- Embeddings
- Resource chunk references
- Collection metadata
- Retrieval metadata

Relational records remain the authoritative source for structured information.

---

# Design Principles

- Separate structured and semantic storage.
- Preserve links to relational entities.
- Keep embeddings replaceable.
- Support efficient similarity search.
- Avoid duplication of business data.

---

# Integration Model

Resources
↓
Chunking
↓
Embedding Generation
↓
Vector Storage
↓
Similarity Search
↓
Relevant Chunk References
↓
Context Assembly

---

# Out of Scope

This document intentionally does not define:

- Embedding model selection.
- Retrieval algorithms.
- Prompt construction.
- Database tuning.
- Provider-specific implementation.

---

# Acceptance Criteria

- Vector database responsibilities defined.
- Separation from relational storage established.
- Integration with RAG documented.
- Ready for relationship and constraint design.

---

## Next

Step 6 — Relationships & Constraints.