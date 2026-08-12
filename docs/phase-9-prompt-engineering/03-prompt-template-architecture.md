# ARIA — Phase 9: Prompt Engineering Architecture

## Step 3 — Prompt Template Architecture

**Status:** Draft v1

## Purpose

This document defines the architectural structure of prompt templates used throughout ARIA. It establishes reusable prompt categories, standard composition patterns and separation between template design and runtime context, ensuring consistency, maintainability and provider independence.

---

# Template Principles

- Prompt templates are reusable architectural assets.
- Templates define structure, not runtime data.
- Templates remain provider-independent where practical.
- Business logic must never be embedded in templates.
- Templates should support structured outputs.

---

# Standard Prompt Categories

- Study Prompt
- Assessment Prompt
- Retrieval Prompt
- Explanation Prompt
- Adaptation Prompt
- Conversation Prompt
- Evaluation Prompt

Each category represents a reusable architectural template rather than a single prompt.

---

# Template Components

Every prompt template may contain:

- System Instructions
- Task Definition
- Context Placeholders
- Constraints
- Output Contract
- Safety Requirements

---

# Relationship with Previous Phases

- Phase 8 determines which agent uses a template.
- Phase 4 defines the AI capability being invoked.
- Runtime context is defined separately in Step 4.

---

# Out of Scope

This document intentionally does not define:

- Individual prompts.
- Runtime context values.
- Provider-specific syntax.
- Prompt optimization techniques.
- Testing methodology.

---

# Acceptance Criteria

- Prompt categories documented.
- Template structure established.
- Responsibilities separated from runtime context.
- Ready for Context Composition.

---

## Next

Step 4 — Context Composition.
