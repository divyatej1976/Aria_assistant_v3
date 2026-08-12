# Phase 10 — Technology Decisions

## Step 4 — AI Technology Decisions

**Status:** Frozen v1 — amended after R0 scope review

---

# Purpose

This document evaluates the AI technologies considered for ARIA and explains why each technology is adopted, deferred, or rejected. The goal is to keep the architecture provider-independent while ensuring the R0 implementation remains as simple as possible.

---

# Evaluation Criteria

- Alignment with AI Architecture (Phase 4)
- Support for R0 adaptive-learning hypothesis
- Provider independence
- Structured output support
- Maintainability
- Operational complexity
- Scalability
- Long-term flexibility

---

# AI Technologies Evaluated

## LiteLLM

**Decision:** ✅ Selected for R0

### Why

- Provides a provider abstraction boundary from the first implementation.
- Prevents application logic from being coupled directly to a single LLM SDK.
- Allows future provider expansion without changing the application-level LLM interface.

LiteLLM is retained as an explicit architectural abstraction. R0 still uses only one actual provider.

---

## Groq

**Decision:** ✅ Selected for R0

### Why

- Excellent inference speed
- Cost-effective for development
- Sufficient to validate ARIA's adaptive-learning hypothesis

R0 intentionally uses a single provider behind LiteLLM.

---

## Gemini

**Decision:** ⏳ Production v1

Added once multiple-provider resilience or capability expansion becomes necessary.

---

## OpenAI

**Decision:** ⏳ Production v1

Integrated only when additional models or capabilities justify another provider.

---

## LangChain

**Decision:** ⏳ Deferred to Production v1

LangChain was originally listed as an R0 dependency, but it did not pass the same elimination test applied to the rest of the technology stack:

> If LangChain is removed, can R0 still validate the adaptive-learning hypothesis?

**Yes.**

R0 can implement its required retrieval pipeline directly using the technologies already selected:

```text
PyMuPDF
   ↓
Chunking / preprocessing
   ↓
Embedding generation
   ↓
PostgreSQL + pgvector
   ↓
Similarity query
   ↓
Context assembly
   ↓
LiteLLM → Groq
```

The required glue code is straightforward application logic. LangChain would therefore introduce an additional abstraction layer without providing a capability that R0 requires for hypothesis validation.

LangChain remains a strong Production v1 candidate for integrations such as model wrappers, loaders, retrieval components, and other ecosystem integrations. It should be introduced when those capabilities create a demonstrated benefit rather than because they are anticipated.

This decision is consistent with the LangGraph decision: both frameworks are deferred when their abstractions are not required by R0.

---

## LangGraph

**Decision:** ⏳ Deferred to Production v1

LangGraph is intentionally excluded from R0.

The R0 workflow is a linear pipeline that does not require graph-based orchestration.

LangGraph becomes appropriate once workflows require:

- branching
- conditional execution
- retries
- stateful orchestration
- reusable workflow nodes

Its adoption should be driven by demonstrated workflow complexity rather than anticipated future needs.

---

## Structured Outputs

**Decision:** ✅ Native Structured Outputs

Provider-native structured outputs are preferred.

Additional libraries such as Instructor may be evaluated later if they provide clear implementation benefits.

---

# Final AI Stack

## R0

- LiteLLM
- Groq
- Native Structured Outputs

LangChain and LangGraph are intentionally excluded from the R0 runtime dependency set.

## Production v1

Adds:

- LangChain, when concrete integration or retrieval capabilities justify it
- LangGraph, when workflow branching or stateful orchestration justifies it
- Gemini
- OpenAI

---

# Architecture Principles

- Provider independence is mandatory.
- Framework abstractions must earn their place through demonstrated need.
- Workflow complexity should justify orchestration frameworks.
- AI integrations should remain replaceable.
- Structured outputs are preferred over free-form parsing.
- AI technology evolves only when the product's capabilities require it.

---

# Acceptance Criteria

- AI technologies evaluated
- R0 vs Production responsibilities defined
- Elimination test applied consistently
- Provider independence preserved
- AI stack frozen

---

## Next

Step 5 — Database Technology Decisions