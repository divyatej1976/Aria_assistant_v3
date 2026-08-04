# ARIA — Phase 4: AI Architecture

## Step 4 — Prompt Architecture

**Status:** Draft v1

## Purpose

This document defines how prompts are designed, versioned, reused and governed across ARIA. Prompts are treated as architectural assets rather than ad-hoc strings embedded in application code.

---

# Design Principles

- Separate prompts by capability.
- Keep prompts provider-agnostic.
- Use structured inputs and outputs.
- Prefer reusable templates over duplicated prompts.
- Version prompts to enable safe iteration.
- Ground prompts with retrieved learner resources whenever applicable.

---

# Prompt Categories

- Study prompts
- Assessment generation prompts
- Evaluation assistance prompts
- Adaptation prompts
- Summarization prompts
- Retrieval augmentation prompts

Each category has a defined purpose and expected output contract.

---

# Prompt Contract

Every prompt should specify:

- Objective
- Required inputs
- Context sources
- Output format
- Validation rules
- Failure handling
- Prompt version

---

# Grounding Rules

- Prefer retrieved evidence over model memory.
- Cite retrieved sources when answering.
- If context is insufficient, acknowledge uncertainty instead of fabricating information.

---

# Prompt Governance

Prompt changes should be version-controlled, reviewed and evaluated before replacing existing production prompts.

---

# Acceptance Criteria

- Prompt architecture is standardized.
- Prompt contracts are defined.
- Grounding philosophy is documented.
- Prompt evolution is governed through versioning.

---

## Next

Step 5 — Study Intelligence.
