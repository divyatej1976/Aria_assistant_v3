# ARIA — Phase 3: System Architecture

## Step 5 — State & Workflow Architecture

**Status:** Draft v1

## Purpose

This document defines how information and business state flow through the ARIA R0 adaptive-learning loop. It establishes authoritative state transitions and ensures that learner progress is driven by validated evidence rather than AI inference.

---

# Core Workflow

```text
Learning Context
      ↓
Resources Ready
      ↓
Study Session
      ↓
Assessment Attempt
      ↓
Deterministic Evaluation
      ↓
Evidence Creation
      ↓
learner_concept_state Update
      ↓
Adaptation Decision
      ↓
Adapted Study
      ↓
Targeted Reassessment
      ↓
Additional Evidence
      ↺
```

---

# State Ownership

| State | Owner |
|-------|-------|
| Learning Context | Learning Context Module |
| Resource Status | Resources Module |
| Assessment Attempt | Assessment Module |
| Evaluation Result | Evaluation Module |
| Evidence | Evidence Module |
| learner_concept_state | learner_concept_state Module |
| Adaptation | Adaptation Module |

Each state has exactly one authoritative owner.

---

# Transition Rules

- Evidence may only be created after successful deterministic evaluation.
- learner_concept_state may only change from validated evidence.
- Adaptation decisions depend on current learner_concept_state.
- Study sessions never modify learner_concept_state directly.
- AI-generated content never bypasses workflow transitions.

---

# Workflow Invariants

- Incomplete assessments produce no evidence.
- Infrastructure failures never become learner evidence.
- Corrections propagate through dependent state.
- Reassessment produces new evidence rather than replacing historical evidence.
- Every adaptation should be traceable to supporting evidence.

---

# Recovery

If a workflow fails, completed authoritative stages remain valid while incomplete downstream stages are retried or recomputed.

---

# Future Evolution

Future releases may introduce Roadmaps, Planner, Revision and other workflows without changing the fundamental evidence-driven lifecycle.

---

# Acceptance Criteria

- Workflow stages are defined.
- State ownership is explicit.
- Transition rules are documented.
- Recovery philosophy is consistent.
- Workflow remains aligned with the frozen R0 product contract.

---

## Next

Step 6 — Failure & Recovery Architecture.
