# ARIA — Phase 5: Memory Architecture

## Step 4 — Conversation Memory

**Status:** Draft v1

## Purpose

This document defines Conversation Memory, the memory responsible for maintaining continuity across learner interactions. It enables ARIA to understand follow-up questions, preserve conversational context, and provide coherent dialogue without confusing temporary conversation history with long-term learner knowledge.

---

# Responsibilities

Conversation Memory is responsible for:

- Preserving relevant dialogue history.
- Resolving references to earlier messages.
- Supporting multi-turn conversations.
- Maintaining conversational continuity.
- Providing context for AI reasoning.

Conversation Memory is not responsible for updating learner knowledge.

---

# Inputs

- Current learner message
- Previous conversation history
- Session context
- Active learning context

---

# Outputs

- Relevant conversation context
- Referenced dialogue history
- Context package for AI prompts

Conversation Memory provides context but does not determine learner_concept_state.

---

# Lifecycle

Conversation Starts
↓
Capture dialogue
↓
Maintain conversation history
↓
Retrieve relevant exchanges
↓
Conversation ends
↓
Persist or discard according to memory policy

---

# Design Principles

- Preserve conversational coherence.
- Retrieve only relevant history.
- Separate dialogue from learner knowledge.
- Respect privacy and retention policies.

---

# Out of Scope

This document intentionally does not define:

- Learner profile persistence.
- Evidence storage.
- Database implementation.
- AI adaptation decisions.

---

# Acceptance Criteria

- Conversation memory responsibilities defined.
- Multi-turn dialogue support documented.
- Separation from learner memory established.
- Architecture aligns with previous phases.

---

## Next

Step 5 — Learner Memory.
