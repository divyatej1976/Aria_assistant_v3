# ARIA — Phase 4: AI Architecture

## Step 3 — Retrieval-Augmented Generation (RAG) Architecture

**Status:** Draft v1

## Purpose

This document defines how ARIA retrieves knowledge from learner-provided resources and supplies grounded context to AI models. The objective is to maximize factual accuracy, explainability and personalization while minimizing hallucinations.

---

# RAG Pipeline

```text
Resource Upload
      ↓
Validation
      ↓
Text Extraction
      ↓
Chunking
      ↓
Metadata Enrichment
      ↓
Embedding Generation
      ↓
Vector Index
      ↓
Retrieval
      ↓
Re-ranking
      ↓
Context Assembly
      ↓
LLM Response
      ↓
Citation Generation
```

---

# Pipeline Stages

## Resource Ingestion
- Validate supported file types.
- Extract text.
- Preserve document metadata.

## Chunking
- Split documents into semantically meaningful chunks.
- Preserve context across chunk boundaries where appropriate.

## Metadata
Each chunk should include metadata such as:
- Source document
- Section or heading
- Page number (when available)
- Subject/topic
- Upload timestamp

## Embeddings
Generate vector representations for efficient semantic retrieval. Embedding providers must remain replaceable.

## Retrieval & Re-ranking
Retrieve the most relevant chunks, then re-rank them before constructing the final AI context.

### Retrieval Funnel (Illustrative Shape)

```text
Vector Index
      ↓
Similarity Search
      ↓
Candidate Chunks (broad recall)
      ↓
Re-ranking
 (relevance + recency + source quality)
      ↓
Selected Chunks (final context)
      ↓
Context Assembly
```

This shows the structural shape of retrieval narrowing from broad recall to a
small, high-quality context set. Exact candidate/selection counts, ranking
signals, and scoring formulas are implementation decisions — see Out of Scope.

## Grounded Response
Responses should be based on retrieved content and include citations whenever applicable.

---

# Architectural Principles

- Retrieval before generation.
- Prefer grounded answers over speculative ones.
- Missing evidence is preferable to fabricated information.
- Provider independence.
- Explainable source attribution.

---


# Out of Scope

This document intentionally defines the logical Retrieval-Augmented Generation (RAG) architecture only.

It does **not** define:

- The specific vector database implementation (e.g., Pinecone, Qdrant, Chroma, FAISS).
- The embedding model or embedding provider.
- Database schema design for storing vectors or metadata.
- Infrastructure deployment architecture.
- Retrieval performance optimization techniques.
- Chunk-size tuning or embedding hyperparameters.
- Prompt wording or prompt engineering details.

These concerns belong to later Architecture or Implementation phases.

The purpose of this document is to define **how retrieval integrates with ARIA's learning architecture**, not how individual technologies are configured.

# Acceptance Criteria

- Complete RAG pipeline defined.
- Retrieval stages documented.
- Grounding strategy established.
- Citation philosophy documented.
- Architecture aligns with Phase 3 principles.

---

## Next

Step 4 — Prompt Architecture.
