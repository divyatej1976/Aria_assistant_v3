# ARIA — Phase 1 PRD

## Step 7 — Scope, Prioritization & Release Boundaries

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Reviewed and aligned with amended `VISION.md`  
**Primary sources:** `VISION.md`, Steps 1–6 of the Phase 1 PRD

---

# 1. Purpose

ARIA's complete vision is intentionally broad. This document prevents that vision from becoming the implementation scope of the first release.

Release boundaries are organized around **product hypotheses**, not arbitrary feature bundles.

> **Each release should contain the smallest coherent system needed to test the next important ARIA hypothesis.**

---

# 2. Two Independent Scope Knobs

ARIA must control two different kinds of breadth.

| Scope | Long-term direction | Early validation |
|---|---|---|
| Domain breadth | Goal-driven and domain-independent | One or a small number of representative contexts |
| Feature breadth | Complete Learning OS | Smallest loop required for the current hypothesis |

Narrowing domain breadth does not automatically solve feature breadth. Both must be controlled deliberately.

---

# 3. Prioritization Principles

1. **Validate a hypothesis before expanding the system built around it.**
2. **A complete adaptive loop before feature breadth.**
3. **Evidence before sophisticated personalization.**
4. **Specific validated contexts before universal abstraction.**
5. **Learner control before high-impact autonomous changes.**
6. **Reliable deterministic workflows before unnecessary agents.**
7. **Measurable learner value before architectural complexity.**
8. **The full vision remains documented even when capabilities ship later.**
9. **A feature's importance to the vision does not make it an R0 requirement.**
10. **The product should earn complexity.**

---

# 4. Release Vocabulary

## R0 — Validation Release

R0 is not merely a product shell and is not the market-ready MVP. It is the smallest executable ARIA slice that can test the first adaptive-learning hypothesis.

## Later Releases

Later releases add systems because they enable the next hypothesis to be tested, not because an arbitrary feature checklist says they are next.

The release labels below are PRD-level working boundaries. They may be refined as acceptance criteria are finalized, but the hypothesis order should remain explicit.

---

# 5. R0 — Prove Adaptive Learning

## Hypothesis

> **ARIA can observe meaningful learning evidence, update a basic learner_concept_state, and use that state to appropriately change the learner's next study experience.**

## Validation context

R0 should be tested using one or a small number of representative contexts from ARIA's initial audience. It does **not** need to prove equal effectiveness across university exams, placements, certifications, competitive exams, interviews, and every professional skill simultaneously.

## Required product loop

```text
Goal / Learning Context
          ↓
       Resources
          ↓
         Study
          ↓
      Assessment
          ↓
      Evaluation
          ↓
    Basic Evidence
          ↓
 Basic learner_concept_state
          ↓
Adapt Next Study Experience
          ↓
          ↺
```

## R0 MUST

### Foundation

- secure learner identity/session sufficient for testing;
- learner-owned data isolation;
- basic learner profile/context;
- one active validation goal/context at minimum;
- basic persistence required to run repeated learning cycles.

The long-term model may support multiple goals, but multiple simultaneous goals are not required to prove R0's hypothesis unless implementation makes them essentially free.

### Resources

Support a deliberately small reliable input surface sufficient for the chosen validation context, for example PDF and/or pasted text.

R0 does not need every planned file/resource type.

### Study

- learner can study within selected context/resources;
- ARIA can explain and answer questions;
- selected source/context can ground study where applicable;
- learner can continue a study interaction after adaptation.

### Assessment

R0 needs enough assessment capability to generate meaningful evidence. It does not need the complete long-term Assessment Engine.

Initial formats should be selected for reliable generation/evaluation in the chosen validation context. Learner configuration should remain possible within the formats R0 actually supports.

### Evaluation

- supported responses can be evaluated;
- deterministic scoring is used where appropriate;
- AI evaluation is bounded/validated where used;
- evaluation failure does not become false learning evidence.

### Basic Evidence

- evaluated performance creates structured evidence;
- evidence retains provenance to learner/context/topic/activity;
- one result does not automatically equal mastery or confirmed weakness.

### Basic learner_concept_state

R0 requires only enough state to support adaptation.

Example conservative states may include:

```text
UNTESTED
DEVELOPING
NEEDS_REVIEW
SUPPORTED
```

Exact state names are an implementation/design decision; the product requirement is conservative evidence-backed state rather than a sophisticated universal mastery ontology.

### Adaptive next Study

This is the defining R0 capability.

ARIA must use learner_concept_state/evidence to materially change a subsequent study experience in a way that can be inspected and tested.

Examples may include:

- prioritize a weak concept;
- provide a different explanation;
- revisit a prerequisite;
- increase/decrease scaffolding;
- ask targeted follow-up questions;
- avoid spending the same effort on already-supported concepts.

The adaptation should retain enough rationale/provenance to verify why it occurred.

## R0 Explicit Non-Goals

R0 should **not be blocked by**:

- Notes system;
- Audio generation;
- Planner;
- email reminders;
- full Roadmap engine;
- automatic Roadmap restructuring;
- sophisticated Progress dashboards;
- mature spaced repetition;
- full misconception detection;
- prerequisite graphs beyond what a narrow validation case needs;
- external platform tracking;
- coding sandbox infrastructure unless deliberately selected as the validation context;
- full multi-agent orchestration;
- every resource type;
- every assessment format;
- multiple simultaneous goals;
- proving domain generality.

## R0 Exit Condition

R0 does **not** exit merely because these systems exist.

It exits only when:

1. **Gate A** rigorously demonstrates the adaptive pipeline in controlled/reproducible scenarios; and
2. **Gate B** collects appropriately scoped real-user directional evidence from available target users.

Exact criteria are defined in Step 8.

---

# 6. R1 — Prove Learning-Path Adaptation

## Hypothesis

> **ARIA can use accumulated learning evidence to maintain and adapt a structured learning path rather than only adapting the next individual study interaction.**

## Candidate capabilities

- Roadmap Engine v1;
- topics/subtopics and dependencies;
- learner-editable roadmap;
- evidence-aware roadmap recommendations;
- explainable adaptation proposals;
- learner accept/modify/reject flow;
- stronger goal structure where needed.

## Exit direction

A learner can follow a structured path and ARIA can propose justified path changes based on learning evidence without silently rewriting the learner's plan.

---

# 7. R2 — Prove Longitudinal Learning

## Hypothesis

> **ARIA can use evidence accumulated over time to decide what deserves review and represent changing learning state responsibly.**

## Candidate capabilities

- richer Learner Model;
- evidence history;
- revision queue;
- repeated retrieval/reassessment;
- teach-back/diagnostic questioning;
- progress based on evidence;
- memory v1 kept distinct from Learner Model;
- conservative misconception hypotheses;
- stronger confidence handling.

Full misconception detection should only emerge when repeated evidence supports it.

---

# 8. R3 — Prove Learning Coordination

## Hypothesis

> **ARIA can coordinate learning work over time using goals, learning paths, evidence, revision needs, deadlines, and learner availability.**

## Candidate capabilities

- Planner;
- availability-aware scheduling;
- deadline-aware prioritization;
- missed-work recovery;
- revision vs new-learning prioritization;
- reminders/notifications;
- intelligent Home/next actions;
- multiple-goal conflict handling where needed.

## Exit direction

ARIA reduces manual learning-management work rather than merely generating a static schedule.

---

# 9. R4 — Expand Learning Interfaces

## Hypothesis

> **Additional learning interfaces can extend ARIA's connected learner context without fragmenting it.**

## Candidate capabilities

### Notes

- manual/AI-assisted notes;
- save from study;
- notes grounded in resources/interactions;
- revision-oriented transformations.

### Audio

- notes/resources → audio;
- quick revision;
- detailed explanation;
- question-and-answer revision;
- exam-before-you-enter recap;
- playback controls;
- interactive voice revision where feasible.

### Richer resources/search

- additional resource types;
- stronger search across learner content;
- richer resource workflows.

Notes remain part of the complete ARIA vision even though they are intentionally not required to prove R0.

---

# 10. R5 — Prove Cross-System Orchestration

## Hypothesis

> **ARIA's mature systems can coordinate through shared state/events without creating unreliable autonomous chains.**

## Candidate capabilities

- richer cross-system event flows;
- recommendations using multiple systems;
- advanced adaptation;
- stronger human-in-the-loop controls;
- workflow retries/idempotency;
- auditability/observability;
- justified multi-agent orchestration where useful;
- external learning integrations where technically/legal feasible.

External integrations should connect specialist platforms rather than recreate them.

---

# 11. R0 Feature Elimination Test

Before adding anything to R0, ask:

> **If this feature is removed, can we still test whether ARIA's learner_concept_state changes future learning appropriately?**

If the answer is yes, default to deferring it.

Exceptions are allowed for foundational security, privacy, persistence, or engineering requirements necessary to run the validation safely and reliably.

---

# 12. Domain Generalization Test

R0 should not attempt to prove the universal case.

After a concrete validation context works, introduce a **structurally different** learning context and ask:

- Which assumptions still hold?
- Which data structures are too specific?
- Which assessment/evidence rules are domain-specific?
- Which learner-state concepts generalize?
- Which UI/workflow assumptions break?

Only then should those abstractions be generalized.

---

# 13. Release Promotion Rule

A release is not promoted because all planned screens exist.

Promotion requires evidence that the release's hypothesis has been sufficiently tested at the level appropriate to that release.

For R0 specifically:

```text
Implementation complete
        ≠
R0 validated
```

Gate A and Gate B define the actual finish line.

---

# 14. Step 7 Exit Condition

Step 7 is complete when:

- long-term vision is preserved;
- R0 domain breadth is constrained;
- R0 feature breadth is constrained;
- R0 is defined around adaptive learning rather than a foundation-only shell;
- later releases each have a clear hypothesis direction;
- full features are not mistaken for first-release requirements;
- release completion depends on validation, not feature presence alone.

**Step 7 is aligned with the reviewed Phase 0 vision.**
---

## Next

Step 8 — Acceptance Criteria, Success Metrics & PRD Closure.
