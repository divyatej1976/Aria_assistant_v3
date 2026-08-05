# ARIA — Phase 5: Memory Architecture

## Step 7 — Context Assembly

**Status:** Draft v1

## Purpose

This document defines how ARIA assembles the information required before invoking an AI model. Context Assembly gathers relevant information from multiple memory systems and produces a focused, explainable context package for AI reasoning while avoiding unnecessary or unrelated information.

---

# Responsibilities

Context Assembly is responsible for:

- Selecting relevant conversation history.
- Retrieving applicable learner information.
- Including validated evidence where appropriate.
- Gathering relevant learning resources.
- Building a coherent context package for AI.

Context Assembly does not make learning decisions or update memory.

---

# Inputs

- Session Memory
- Conversation Memory
- Learner Memory
- Evidence Memory
- Resource Memory
- Current learner request

---

# Context Assembly Flow

Current Learner Request
↓
Relevant Session Context
↓
Relevant Conversation History
↓
Relevant Learner State
↓
Relevant Evidence
↓
Relevant Learning Resources
↓
Validated Context Package
↓
AI Prompt Construction

---

# Outputs

- Explainable context package
- Retrieved supporting information
- Context metadata for observability

---

# Design Principles

- Include only relevant information.
- Prefer validated evidence.
- Minimize unnecessary context.
- Preserve explainability.
- Respect privacy boundaries.

---

# Out of Scope

This document intentionally does not define:

- Prompt wording.
- AI reasoning.
- Database implementation.
- Memory persistence.
- Adaptation algorithms.

---

# Acceptance Criteria

- Context assembly process documented.
- Memory responsibilities integrated.
- Context remains explainable and privacy-aware.
- Architecture aligns with AI Architecture and previous memory documents.

---

## Next

Step 8 — Memory Lifecycle.