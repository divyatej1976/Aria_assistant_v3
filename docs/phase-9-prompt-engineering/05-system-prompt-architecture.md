# ARIA — Phase 9: Prompt Engineering Architecture

## Step 5 — System Prompt Architecture

**Status:** Draft v1

## Purpose

This document defines the architectural role of system prompts within ARIA. System prompts establish stable behavioral expectations, safety boundaries and response conventions that remain independent of individual user requests while supporting provider-independent prompt engineering.

---

# System Prompt Principles

- System prompts define long-lived behavioral guidance.
- Business rules remain outside system prompts.
- System prompts are reusable across interactions.
- System prompts should remain provider-independent where practical.
- Safety instructions are centralized and consistently applied.

---

# Standard Components

Every system prompt may include:

1. System Identity
2. Core Responsibilities
3. Behavioral Expectations
4. Safety Requirements
5. Response Style
6. Output Constraints

---

# Interaction with Runtime Context

System prompts provide stable instructions.

Runtime context supplies task-specific information.

Prompt templates define interaction structure.

These responsibilities remain intentionally separated.

---

# Relationship with Previous Phases

- Phase 4 defines AI capabilities.
- Phase 8 defines agent responsibilities.
- Step 4 defines runtime context composition.

---

# Out of Scope

This document intentionally does not define:

- Individual system prompt text.
- Provider-specific prompt syntax.
- Runtime context values.
- User prompt processing.
- Output evaluation.

---

# Acceptance Criteria

- System prompt responsibilities documented.
- Stable prompt components defined.
- Runtime separation established.
- Ready for User Prompt Processing.

---

## Next

Step 6 — User Prompt Processing.