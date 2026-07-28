# ARIA — Phase 1: Product Requirements Document

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document (PRD)  
**Status:** In Progress  
**Source of truth:** [`VISION.md`](../../VISION.md)

---

## Purpose

Phase 0 established what ARIA is and why it should exist.

Phase 1 translates that product vision into explicit, testable product requirements before user flows, wireframes, architecture, database design, API design, or implementation begin.

The PRD should define **what ARIA must do**, the constraints it must respect, and how we will know whether each major capability works as intended.

---

## Phase 1 Steps

```text
Step 1 — Product Overview, Goals & Non-Goals
          ↓
Step 2 — User & Learning-Context Requirements
          ↓
Step 3 — Functional Requirements
          ↓
Step 4 — Cross-System & Automation Requirements
          ↓
Step 5 — AI, Learner Model, Memory & Evidence Requirements
          ↓
Step 6 — Non-Functional, Privacy, Security & Reliability Requirements
          ↓
Step 7 — User Stories & Acceptance Criteria
          ↓
Step 8 — Success Metrics, Risks & Open Questions
          ↓
Step 9 — Canonical PRD.md
```

---

## Planned Documents

| Step | Document | Purpose |
|---|---|---|
| 1 | `01-product-overview-goals.md` | Define product context, goals, non-goals, principles and PRD boundaries. |
| 2 | `02-user-context-requirements.md` | Define requirements for goal-driven learners, multiple goals, learning contexts, onboarding and personalization context. |
| 3 | `03-functional-requirements.md` | Specify requirements for Authentication, Home, Goals, Study, Resources, Notes, Assessment, Evaluation, Roadmaps, Planner, Revision, Progress, Audio, Search, Notifications and Settings. |
| 4 | `04-cross-system-requirements.md` | Specify events, feature interactions, adaptation behaviour, automation boundaries and human approval requirements. |
| 5 | `05-ai-learning-requirements.md` | Specify AI behaviour, Learner Model, memory, evidence, misconceptions, prerequisite detection, recommendations, confidence and validation requirements. |
| 6 | `06-non-functional-requirements.md` | Specify performance, reliability, privacy, security, accessibility, observability, scalability and failure-handling requirements. |
| 7 | `07-user-stories-acceptance.md` | Convert requirements into user stories and testable acceptance criteria. |
| 8 | `08-success-risks.md` | Define success metrics, product/technical risks, assumptions, dependencies and unresolved questions. |
| 9 | `PRD.md` | Consolidate and freeze the canonical Phase 1 product requirements. |

---

## Requirement ID Convention

Requirements should use stable identifiers so later user flows, architecture, APIs and tests can reference them.

```text
FR-AUTH-001      Functional — Authentication
FR-GOAL-001      Functional — Goals
FR-STUDY-001     Functional — Study
FR-RES-001       Functional — Resources
FR-NOTE-001      Functional — Notes
FR-ASSESS-001    Functional — Assessment
FR-EVAL-001      Functional — Evaluation
FR-ROAD-001      Functional — Roadmaps
FR-PLAN-001      Functional — Planner
FR-REV-001       Functional — Revision
FR-PROG-001      Functional — Progress
FR-AUDIO-001     Functional — Audio
FR-SEARCH-001    Functional — Search
FR-NOTIF-001     Functional — Notifications
FR-SET-001       Functional — Settings

XR-001           Cross-system requirement
AI-001           AI behaviour requirement
LM-001           Learner Model requirement
MEM-001          Memory requirement
EVD-001          Evidence requirement
NFR-PERF-001     Performance requirement
NFR-SEC-001      Security requirement
NFR-PRIV-001     Privacy requirement
NFR-REL-001      Reliability requirement
NFR-ACC-001      Accessibility requirement
```

IDs should describe requirements, not implementation tasks.

---

## PRD Rules

1. `VISION.md` remains the product north star.
2. Requirements must remain domain-independent unless a capability explicitly supports a domain-specific assessment renderer or integration.
3. Do not hardcode DSA, AWS, GATE, university subjects, or any other learner goal into the core product.
4. ARIA may recommend assessment approaches, but the learner controls the final assessment specification.
5. Learning-state claims should increasingly be evidence-backed and confidence-aware.
6. Conversational memory and evidence-backed Learner Model state remain distinct concepts.
7. Progress should represent meaningful learning state rather than app activity alone.
8. Significant automated changes should be explainable and reviewable where appropriate.
9. PRD requirements describe product behaviour, not premature framework/database/API choices.
10. User flows and detailed page interaction design belong to Phase 2.
11. Wireframes and visual hierarchy belong to Phase 3.
12. System and agent architecture decisions belong to later architecture phases.

---

## Phase Completion Definition

Phase 1 is complete when:

- all major product systems have explicit requirements;
- cross-system behaviours are specified;
- AI and learning-state behaviour has constraints;
- non-functional requirements are documented;
- critical user stories have acceptance criteria;
- success measures and major risks are recorded;
- unresolved product questions are explicitly tracked;
- the final `PRD.md` is internally consistent with `VISION.md`;
- requirements are specific enough to drive Phase 2 user-flow design without inventing missing product behaviour.

---

## Current Progress

```text
Phase 0 — Product Vision                         ✓ COMPLETE

Phase 1 — Product Requirements Document
├── Step 1 — Product Overview, Goals & Non-Goals       NEXT
├── Step 2 — User & Learning-Context Requirements
├── Step 3 — Functional Requirements
├── Step 4 — Cross-System Requirements
├── Step 5 — AI & Learning Requirements
├── Step 6 — Non-Functional Requirements
├── Step 7 — User Stories & Acceptance Criteria
├── Step 8 — Success Metrics, Risks & Open Questions
└── Step 9 — Final PRD.md
```

---

## Next

Begin **Step 1 — Product Overview, Goals & Non-Goals**.

Step 1 will establish the PRD-level product definition and explicitly separate:

- what ARIA is trying to accomplish;
- what outcomes the product should create;
- what ARIA intentionally does not attempt to become;
- what principles every later functional requirement must preserve.