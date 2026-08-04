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

# Acceptance Criteria

- Adaptation workflow documented.
- Inputs and outputs defined.
- Recommendation philosophy established.
- Adaptation remains explainable and evidence-driven.

---

## Next

Step 10 — AI Safety & Reliability.
