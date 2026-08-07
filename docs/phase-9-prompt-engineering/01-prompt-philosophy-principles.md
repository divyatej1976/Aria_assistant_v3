# ARIA — Phase 9: Prompt Engineering Architecture

## Step 1 — Prompt Philosophy & Principles

**Status:** Draft v1

## Purpose

This document establishes the architectural philosophy governing prompt engineering within ARIA. Prompts are treated as reusable architectural assets rather than embedded strings, ensuring maintainability, provider independence and consistent AI behavior.

---

# Prompt Philosophy

Prompts define how AI capabilities are invoked, not how business decisions are made. They guide reasoning, communication and structured output while remaining separate from business logic, system architecture and application state.

---

# Core Principles

1. Prompts are architectural assets.
2. Prompts remain provider-independent where practical.
3. Business rules never live inside prompts.
4. Prompts consume structured context rather than raw application state.
5. Structured outputs are preferred over free-form text.
6. Prompts should be reusable, testable and versioned.
7. Prompt changes should be governed through documented review.
8. Safety and consistency take precedence over creativity.

---

# Responsibilities

Prompt Engineering is responsible for:

- Prompt architecture.
- Prompt templates.
- Context composition.
- Output contracts.
- Prompt governance.

Prompt Engineering is not responsible for business rules, API implementation, database persistence, agent orchestration or UI behavior.

---

# Relationship with Previous Phases

- Phase 4 defines AI capabilities.
- Phase 8 defines who orchestrates AI.
- Phase 9 defines how AI is instructed.

---

# Out of Scope

This document intentionally does not define:

- Individual prompt templates.
- Model-specific optimizations.
- Provider configuration.
- Runtime prompt assembly.
- Evaluation metrics.

---

# Acceptance Criteria

- Prompt philosophy documented.
- Core principles established.
- Responsibilities defined.
- Phase boundaries clearly documented.

---

## Next

Step 2 — Prompt Lifecycle.
