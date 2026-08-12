# ARIA — Phase 3: System Architecture

## Step 6 — Failure & Recovery Architecture

**Status:** Draft v1

## Purpose

This document defines how ARIA responds to failures while preserving correctness, learner trust, and data integrity. The goal is graceful degradation: failures should interrupt as little of the learner experience as possible without compromising authoritative state.

---

# Failure Principles

- Never corrupt learner_concept_state.
- Never create evidence from incomplete or failed workflows.
- Prefer recovery over restart.
- Failures should remain isolated.
- Retries must be safe and idempotent.
- Surface actionable errors to the user when recovery is not automatic.

---

# Failure Categories

## Infrastructure
- Network interruptions
- Database connectivity
- Storage unavailable

## External Providers
- LLM unavailable
- Embedding service failure
- Email delivery failure

## Business Workflow
- Invalid assessment submission
- Missing learning resources
- Interrupted study session

---

# Recovery Strategy

- Persist completed authoritative stages.
- Retry only incomplete downstream operations.
- Prevent duplicate evidence creation.
- Preserve learner progress whenever possible.
- Record recoverable failures for later inspection.

---

# Graceful Degradation

Examples:

- If AI explanation generation fails, deterministic evaluation still succeeds.
- If email delivery fails, learning progress remains unaffected.
- If embedding generation is delayed, already-ingested resources remain available.

---

# Invariants

- learner_concept_state never becomes partially updated.
- Historical evidence is immutable.
- Adaptation decisions are reproducible from stored evidence.
- Recovery never bypasses validation.

---

# Acceptance Criteria

- Failure classes are documented.
- Recovery philosophy is defined.
- Core invariants are protected.
- User trust is preserved during failures.
- Architecture remains consistent with previous Phase 3 documents.

---

## Next

Step 7 — Security & Trust Architecture.
