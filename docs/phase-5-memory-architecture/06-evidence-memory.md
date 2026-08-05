# ARIA — Phase 5: Memory Architecture

## Step 6 — Evidence Memory

**Status:** Draft v1

## Purpose

This document defines Evidence Memory, the persistent record of validated learning evidence collected throughout a learner's journey. Evidence Memory preserves the history required to explain learner-state changes, support personalization, and maintain trust in ARIA's adaptive learning decisions.

---

# Responsibilities

Evidence Memory is responsible for:

- Persisting validated evidence.
- Preserving evidence provenance.
- Recording assessment outcomes.
- Recording study and revision evidence.
- Supporting explainable learner-state updates.

Evidence Memory stores validated evidence only. Raw AI outputs and unverified observations are excluded.

---

# Inputs

- Validated evidence from Evidence Intelligence.
- Assessment results.
- Verified study interactions.
- Reassessment outcomes.

Only validated evidence may be persisted.

---

# Outputs

- Historical evidence records.
- Provenance information.
- Evidence history for Learner Memory.
- Evidence retrieval for AI and deterministic services.

---

# Lifecycle

Validated Evidence Created
↓
Persist Evidence
↓
Preserve Provenance
↓
Retrieve for learner-state computation
↓
Retain according to governance policy

Evidence records remain immutable except where governance policies explicitly require correction or removal.

---

# Design Principles

- Evidence before persistence.
- Preserve provenance.
- Prefer immutability.
- Support full traceability.
- Separate evidence from learner-state computation.

---

# Out of Scope

This document intentionally does not define:

- Learner-state algorithms.
- Database schema.
- AI reasoning.
- Conversation history.
- Memory retention policy implementation.

---

# Acceptance Criteria

- Evidence Memory responsibilities defined.
- Evidence lifecycle documented.
- Provenance requirements established.
- Architecture aligns with Phase 4 Evidence Intelligence.

---

## Next

Step 7 — Context Assembly.