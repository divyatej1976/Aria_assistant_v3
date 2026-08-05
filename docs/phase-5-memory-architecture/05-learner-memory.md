# ARIA — Phase 5: Memory Architecture

## Step 5 — Learner Memory

**Status:** Draft v1

## Purpose

This document defines Learner Memory, the persistent representation of a learner across sessions. Learner Memory stores stable learner information that enables long-term personalization while remaining evidence-driven, explainable and under learner control.

---

# Responsibilities

Learner Memory is responsible for:

- Maintaining learner goals.
- Recording learning preferences.
- Preserving the current learner state.
- Tracking long-term learning progress.
- Supporting personalized learning experiences.

Learner Memory does not store temporary conversation context or raw AI outputs.

---

# Inputs

- Validated learner state
- Verified evidence
- Learner preferences
- Learner profile updates

Only validated information may update Learner Memory.

---

# Outputs

- Current learner profile
- Learning goals
- Personalization context
- Stable learner state for AI and system components

---

# Lifecycle

Learner Created
↓
Initialize profile
↓
Update using validated evidence
↓
Refine over multiple learning sessions
↓
Support long-term personalization

Learner Memory persists across sessions until modified or removed according to governance policies.

---

# Design Principles

- Evidence before persistence.
- Explain every significant learner-state change.
- Preserve provenance.
- Learner owns personal information.
- Separate learner identity from conversation history.

---

# Out of Scope

This document intentionally does not define:

- Evidence storage implementation.
- Database schema.
- AI adaptation algorithms.
- Session memory.
- Conversation memory.

---

# Acceptance Criteria

- Learner Memory responsibilities defined.
- Persistent learner information identified.
- Update rules documented.
- Architecture aligns with previous phases.

---

## Next

Step 6 — Evidence Memory.