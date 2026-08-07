# ARIA — Phase 3: System Architecture

## Step 1 — System Boundary & Architecture Principles

**Status:** Draft v1

This document establishes the engineering constitution for ARIA. It defines architectural principles that remain stable even if technologies, providers, or implementation details change.

## Purpose

This document defines:

- What ARIA owns.
- What ARIA depends on.
- Core architectural principles.
- AI boundaries.
- Trust boundaries.
- State ownership philosophy.
- Failure philosophy.
- Extensibility philosophy.

Future architecture documents must conform to these principles.

---

## Engineering Definition

ARIA is an AI-native adaptive learning platform composed of deterministic domain systems and bounded AI capabilities that work together to deliver explainable, evidence-driven personalized learning.

---

## R0 Boundary

R0 implements only the validated adaptive-learning loop:

Learning Context → Resources → Study → Assessment → Evaluation → Evidence → learner_concept_state → Adaptation → Targeted Reassessment.

Roadmaps, Planner, Notes, Audio, advanced Progress and other vision features remain future releases.

---

## Inside ARIA

- Learning Context
- Resources
- Study
- Assessment
- Evaluation
- Evidence
- learner_concept_state
- Adaptation
- Authentication integration
- Authorization

## Outside ARIA

- LLM providers
- Embedding providers
- Email providers
- Storage providers
- Hosting platform
- Browser / Operating System

---

## Core Principles

1. Business logic belongs to ARIA.
2. AI generates; ARIA decides.
3. Deterministic systems own learner_concept_state.
4. Evidence precedes adaptation.
5. Explainability is a product feature.
6. Insufficient evidence is a valid outcome.
7. Failures remain local whenever possible.
8. Every important state has one owner.
9. Build for extension without implementing the future.
10. Providers should be replaceable.

---

## AI Boundary

AI may:

- explain concepts;
- generate questions;
- summarize;
- generate adapted explanations.

AI may not:

- directly modify learner_concept_state;
- invent evidence;
- bypass authorization;
- fabricate progress.

---

## Trust Model

- User input: untrusted until validated.
- LLM output: untrusted until processed.
- Database: authoritative persistence.
- Evidence after validation: trusted.
- learner_concept_state: derived only from validated evidence.

---

## Architecture Philosophy

Architecture should remain modular, observable, recoverable, explainable and replaceable. R0 architecture must support future growth without prematurely implementing future systems.

---

## ADR Policy

Major architectural decisions should be recorded as Architectural Decision Records (ADRs), documenting rationale, alternatives, trade-offs and review conditions.

---

## Acceptance Criteria

- System boundaries are explicit.
- AI responsibilities are bounded.
- Deterministic ownership is defined.
- Extension philosophy matches the frozen Vision and PRD.
- This document acts as the governing reference for all remaining Phase 3 documents.

---

## Next

Step 2 — High-Level System Architecture.
