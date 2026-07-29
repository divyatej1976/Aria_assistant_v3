# ARIA — Phase 1: Product Requirements Document

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document (PRD)  
**Status:** In Progress — consistency review after Phase 0 amendments  
**Source of truth:** [`VISION.md`](../../VISION.md)

---

## Purpose

Phase 0 established what ARIA is and why it should exist. Phase 1 translates that vision into explicit, testable product requirements before user flows, wireframes, architecture, database design, API design, or implementation begin.

The reviewed Phase 0 vision introduced three corrections that every Phase 1 document must preserve:

1. **Domain breadth:** ARIA's long-term model is domain-independent, while early validation may use constrained representative contexts.
2. **Feature breadth:** the complete Learning OS is not R0 scope; R0 is the smallest loop that tests adaptive learning.
3. **Validation breadth:** R0 uses rigorous Gate A engineering validation plus small-scale Gate B directional real-user evidence, without causal overclaiming.

---

## Phase 1 Documents

| Document | Purpose | Review status |
|---|---|---|
| `01-product-overview-goals.md` | Product context, goals, audience, R0 hypothesis and boundaries | ✓ Realigned |
| `02-user-context-requirements.md` | Learner identity, goals, contexts, onboarding and continuity | Audit pending |
| `03-functional-requirements.md` | Full-vision functional requirements | Audit pending |
| `04-cross-system-requirements.md` | Cross-system events, automation and approval boundaries | Audit pending |
| `05-ai-learner-model-memory-evidence.md` | AI behaviour, Learner Model, memory, evidence and confidence | Audit pending |
| `06-non-functional-privacy-security-reliability-accessibility.md` | Performance, privacy, security, reliability and accessibility | Audit pending |
| `07-scope-prioritization-release-boundaries.md` | Hypothesis-driven release boundaries | ✓ Realigned |
| `08-acceptance-criteria-success-metrics-prd-closure.md` | R0 Gate A/Gate B acceptance and later-release direction | ✓ Realigned |
| `PRD.md` | Final consolidated source of truth | Not yet created/frozen |

---

## Requirement ID Convention

Existing requirement identifiers remain useful for later traceability, even when a requirement belongs to a later release rather than R0.

Examples:

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
XR-001           Cross-system requirement
AI-001           AI behaviour requirement
LM-001           Learner Model requirement
MEM-001          Memory requirement
EVD-001          Evidence requirement
NFR-*            Non-functional requirement
```

A requirement existing in the PRD does **not** automatically mean it is an R0 requirement.

---

## PRD Rules

1. `VISION.md` remains the product north star.
2. Initial audience is college students, recent graduates, and early-career learners.
3. Long-term domain independence does not require universal R0 validation.
4. Avoid unnecessary domain-specific coupling; do not prematurely build a universal ontology.
5. Validate specific contexts, then generalize when structurally different cases expose assumptions.
6. The complete product feature map does not define R0 scope.
7. R0 is the smallest end-to-end loop required to test adaptive learning.
8. Assessment remains learner-configurable within the formats actually supported by a release.
9. Learning-state claims should be evidence-backed and confidence-aware.
10. Conversational memory and evidence-backed Learner Model state remain distinct.
11. Significant automated changes should be explainable/reviewable where appropriate.
12. Not every subsystem should be an AI agent.
13. Gate A is rigorous engineering validation.
14. Gate B is directional real-user evidence at solo-capstone scale and must not be represented as statistically proven causal improvement.
15. User flows belong to Phase 2; wireframes to Phase 3; architecture choices to later phases.

---

## Current Release Direction

```text
R0 — Prove adaptive learning
        ↓
R1 — Prove learning-path adaptation
        ↓
R2 — Prove longitudinal learning
        ↓
R3 — Prove learning coordination
        ↓
R4 — Expand learning interfaces
        ↓
R5 — Prove mature cross-system orchestration
```

These boundaries are driven by hypotheses rather than calendar dates or arbitrary feature counts.

---

## Phase Completion Definition

Phase 1 is complete when:

- all major product systems have explicit long-term requirements;
- R0 requirements are clearly distinguished from later-release requirements;
- the R0 validation context is chosen;
- Gate A scenarios and completion criteria are defined;
- Gate B collection/reporting scope is realistic;
- cross-system and AI behaviour constraints are internally consistent;
- non-functional requirements needed by R0 are identified;
- major risks/assumptions/open questions are recorded;
- the final `PRD.md` is internally consistent with `VISION.md`;
- requirements are specific enough to drive Phase 2 without inventing missing product behaviour.

---

## Current Progress

```text
Phase 0 — Product Vision                         ✓ COMPLETE & REVIEWED

Phase 1 — Product Requirements Document         IN PROGRESS
├── 01 Product Overview                         ✓ REALIGNED
├── 02 User & Learning Context                   ◐ AUDIT PENDING
├── 03 Functional Requirements                  ◐ AUDIT PENDING
├── 04 Cross-System Requirements                ◐ AUDIT PENDING
├── 05 AI / Learner Model / Evidence            ◐ AUDIT PENDING
├── 06 Non-Functional Requirements              ◐ AUDIT PENDING
├── 07 Scope / Release Boundaries                ✓ REALIGNED
├── 08 Acceptance / Success / Validation         ✓ REALIGNED
└── Canonical PRD.md                             ○ NOT FROZEN
```

---

## Next

Audit Steps 2–6 against the reviewed `VISION.md`, changing only assumptions that conflict with the new audience, R0 scope, release boundaries, or Gate A/Gate B validation model. Preserve good full-vision requirements by marking them as later-release requirements rather than deleting them merely because they are outside R0.