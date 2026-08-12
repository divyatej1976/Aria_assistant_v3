# ARIA — Phase 4: AI Architecture

## Step 6 — Assessment Intelligence

**Status:** Draft v1

## Purpose

This document defines how ARIA designs, generates and evaluates adaptive assessments that align with learner goals, approved resources and the evidence-driven learning loop.

---

# Objectives

Assessment Intelligence should:

- Generate assessments aligned with learner goals.
- Support multiple assessment formats.
- Adapt difficulty using learner_concept_state.
- Produce high-quality explanations.
- Generate fair and grounded questions.

---

# Supported Assessment Formats

R0 supports configurable formats such as:

- Multiple Choice Questions (MCQs)
- Short Answer Questions
- Long-form Questions
- Coding Problems
- Mixed-format Tests
- Timed Practice Sessions

The learner selects the preferred assessment format based on their preparation goal.

---

# Inputs

- Learning Context
- Retrieved learning resources
- learner_concept_state
- Previous assessment evidence
- User-selected assessment configuration

---

# Outputs

- Assessment set
- Correct answers
- Explanations
- Difficulty metadata
- Evaluation guidance

Generated assessments become authoritative only after deterministic validation and evaluation.

---

# Design Principles

- Assess understanding, not memorization.
- Ground questions in approved resources.
- Match assessment style to learner goals.
- Support repeatable evaluation.
- Preserve fairness and explainability.

---

# Acceptance Criteria

- Assessment generation workflow defined.
- Multiple assessment formats supported architecturally.
- Learner-controlled assessment configuration documented.
- Assessment intelligence aligns with Phase 3 and Phase 4 principles.

---

## Next

Step 7 — Evidence Intelligence.
