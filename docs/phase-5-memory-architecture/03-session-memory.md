# ARIA — Phase 5: Memory Architecture

## Step 3 — Session Memory

**Status:** Draft v1

## Purpose

This document defines Session Memory, the temporary memory used during an active learner session. Session Memory maintains continuity while a learner studies, asks questions, completes assessments, and receives adaptive guidance. It is intentionally short-lived and does not represent long-term learner knowledge.

---

# Responsibilities

Session Memory is responsible for:

- Tracking the active learning session.
- Maintaining temporary conversational context.
- Holding the current study objective.
- Tracking the active assessment.
- Supporting continuity within a single session.

---

# Inputs

- Current learner request
- Active learning context
- Retrieved resources
- Conversation context
- Current learner state

---

# Outputs

- Current session context
- Active study state
- Temporary AI context
- Candidate observations for Evidence Intelligence

Session Memory never updates long-term learner memory directly.

---

# Lifecycle

Session Start
↓
Initialize session context
↓
Update during interaction
↓
Transfer validated observations to Evidence Intelligence
↓
Session ends
↓
Session memory discarded

---

# Design Principles

- Short-lived by design.
- Isolated from persistent learner memory.
- Supports continuity without creating permanent knowledge.
- Privacy-conscious and disposable.

---

# Out of Scope

This document intentionally does not define:

- Persistent learner memory.
- Conversation history across sessions.
- Database implementation.
- AI adaptation logic.

---

# Acceptance Criteria

- Session memory responsibilities defined.
- Lifecycle documented.
- Separation from persistent memory established.
- Architecture aligns with previous phases.

---

## Next

Step 4 — Conversation Memory.