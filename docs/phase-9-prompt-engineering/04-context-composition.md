# ARIA — Phase 9: Prompt Engineering Architecture

## Step 4 — Context Composition

**Status:** Draft v1

## Purpose

This document defines how ARIA assembles the context provided to AI models. It establishes a structured, deterministic approach to combining system instructions, learner information, memory and retrieved knowledge while minimizing irrelevant information and preserving privacy.

---

# Context Composition Principles

- Context is assembled deterministically.
- Include only information relevant to the current task.
- Prioritize validated and authoritative data.
- Minimize token usage without losing essential information.
- Preserve privacy and access controls.

---

# Standard Context Layers

1. System Instructions
2. Task Definition
3. Learner Context
4. Learner Memory
5. Retrieved Knowledge
6. Conversation Context
7. Runtime Constraints

---

# Context Sources

- Phase 4 — AI capabilities.
- Phase 5 — Memory Architecture.
- Phase 6 — Database Architecture.
- Phase 7 — API responses.
- Phase 8 — Agent orchestration.

---

# Composition Rules

- Validate context before prompt assembly.
- Exclude stale or unauthorized information.
- Prefer structured data over unstructured text.
- Maintain consistent ordering of context layers.
- Separate prompt templates from runtime context.

---

# Out of Scope

This document intentionally does not define:

- Retrieval algorithms.
- Embedding strategies.
- Context window optimization.
- Provider-specific formatting.
- Prompt template content.

---

# Acceptance Criteria

- Context layers documented.
- Context sources identified.
- Composition rules established.
- Ready for System Prompt Architecture.

---

## Next

Step 5 — System Prompt Architecture.
