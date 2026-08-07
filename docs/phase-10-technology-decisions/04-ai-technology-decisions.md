# Phase 10 — Technology Decisions

## Step 4 — AI Technology Decisions

**Status:** Frozen v1

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

- Single interface for multiple LLM providers
- Prevents vendor lock-in
- Future provider expansion requires configuration rather than architectural change
- Supports retries and failover when additional providers are introduced

LiteLLM is an architectural requirement from R0 because provider independence is a core architectural principle.

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

**Decision:** ✅ Selected

Used as an integration library for LLMs, embeddings, loaders, and retrieval components.

ARIA does not depend on LangChain for orchestration.

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
- LangChain
- Native Structured Outputs

## Production v1

Adds:

- LangGraph
- Gemini
- OpenAI

---

# Architecture Principles

- Provider independence is mandatory.
- Workflow complexity should justify orchestration frameworks.
- AI integrations should remain replaceable.
- Structured outputs are preferred over free-form parsing.
- AI technology evolves only when the product's capabilities require it.

---

# Acceptance Criteria

- AI technologies evaluated
- R0 vs Production responsibilities defined
- Provider independence preserved
- AI stack frozen

---

## Next

Step 5 — Database Technology Decisions