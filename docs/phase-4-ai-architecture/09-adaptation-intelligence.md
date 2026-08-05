# ARIA — Phase 4: AI Architecture

## Step 9 — Adaptation Intelligence

**Status:** Draft v1

## Purpose

This document defines how ARIA determines the most effective next learning experience using validated learner state, learning context and evidence. Adaptation Intelligence is the decision engine of the adaptive-learning loop.

---

# Objectives

Adaptation Intelligence should:

- Recommend what to study next.
- Match learning activities to learner goals.
- Balance reinforcement and progression.
- Explain why each recommendation was made.
- Adapt continuously as new evidence becomes available.

---

# Inputs

- Current Learner State
- Validated Evidence
- Learning Context
- Assessment history
- Learner preferences

Adaptation decisions must never rely solely on raw AI output.

---

# Decision Pipeline

```text
Learner State
      ↓
Evidence Analysis
      ↓
Adaptation Decision
      ↓
Recommended Study Activity
      ↓
New Evidence
      ↺
```

### Decision Logic Shape (Illustrative)

```text
Validated Evidence (per concept)
      ↓
Evidence Aggregation
      ↓
Mastery / Confidence Estimate
      ↓
Compare Against Adaptation Thresholds
      ↓
Decision Policy
 (reinforce / progress / re-explain differently)
      ↓
Recommendation + Explanation
```

This shows the structural shape of how evidence becomes a decision — not the
scoring formula or threshold values themselves, which remain implementation
decisions (see Out of Scope). The key architectural commitment is that a
decision policy step exists between raw evidence and any recommendation,
so adaptation is never a direct AI-output-to-recommendation shortcut.

---

# Recommendation Types

- New study topics
- Targeted revision
- Additional practice
- Easier explanations
- Higher-difficulty challenges
- Different assessment formats

Recommendations should align with learner-selected goals and preferences.

---

# Design Principles

- Evidence before recommendation.
- Explain every adaptation.
- Adapt conservatively.
- Avoid unnecessary repetition.
- Personalize without overfitting to limited evidence.

---


# Out of Scope

This document defines the architectural responsibilities of Adaptation Intelligence.

It intentionally does **not** define:

- Recommendation algorithms.
- Reinforcement learning techniques.
- Scheduling heuristics.
- Long-term roadmap generation.
- Planner functionality.
- Future multi-agent coordination.

These concerns belong to implementation or future releases.

This document defines **what Adaptation Intelligence must accomplish**, not the specific algorithms used to achieve it.

# Acceptance Criteria

- Adaptation workflow documented.
- Inputs and outputs defined.
- Recommendation philosophy established.
- Adaptation remains explainable and evidence-driven.

---

## Next

Step 10 — AI Safety & Reliability.
