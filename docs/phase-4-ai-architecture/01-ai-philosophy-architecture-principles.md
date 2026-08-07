# ARIA — Phase 4: AI Architecture

## Step 1 — AI Philosophy & Architecture Principles

**Status:** Draft v1

## Purpose

This document establishes the principles governing every AI capability within ARIA. It defines where AI is appropriate, where deterministic systems must remain authoritative, and how AI contributes to adaptive learning while preserving correctness, explainability and learner trust.

---

# AI Philosophy

ARIA is an AI-native adaptive learning platform—not a general-purpose chatbot. AI exists to enhance learning, while deterministic systems remain the source of truth for learner_concept_state, evidence and progression.

---

# Core AI Principles

1. AI assists; deterministic systems decide.
2. AI generates possibilities, not authoritative state.
3. Every learner-affecting AI output should be explainable.
4. AI should be grounded in learner resources whenever possible.
5. Lack of confidence should lead to clarification, not fabrication.
6. AI capabilities must remain provider-independent.
7. AI must respect privacy, authorization and ownership boundaries.
8. Human learners remain in control of important learning decisions.

---

# AI Responsibilities

AI may:
- Explain concepts.
- Generate study material.
- Generate assessments.
- Summarize resources.
- Recommend study directions.

AI may not:
- Modify learner_concept_state directly.
- Invent evidence.
- Bypass validation.
- Override authorization.
- Fabricate progress.

---

# Relationship with Phase 3

All AI capabilities operate within the architectural constraints established during Phase 3. AI augments existing workflows but does not replace deterministic ownership of critical business logic.

---

# Acceptance Criteria

- AI purpose is clearly defined.
- AI boundaries are explicit.
- Core AI principles are documented.
- AI responsibilities align with Phase 3 architecture.

---

## Next

Step 2 — AI Capability Map.
