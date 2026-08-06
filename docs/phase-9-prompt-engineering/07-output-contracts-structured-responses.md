# ARIA — Phase 9: Prompt Engineering Architecture

## Step 7 — Output Contracts & Structured Responses

**Status:** Draft v1

## Purpose

This document defines how AI-generated responses are represented within ARIA. It establishes structured output contracts, validation principles and response handling rules so that AI outputs can be consumed reliably by application components while remaining provider-independent.

---

# Output Contract Principles

- Prefer structured outputs over free-form responses.
- Every AI response should conform to a defined contract where practical.
- Response validation occurs before application consumption.
- AI output never bypasses application validation.
- Provider-specific response formats are abstracted behind a common interface.

---

# Standard Output Components

Every structured response may include:

1. Response Metadata
2. Primary Result
3. Supporting Evidence or References
4. Confidence Indicators (where applicable)
5. Validation Status
6. Error Information (if applicable)

---

# Validation Rules

- Validate schema before processing.
- Reject malformed or incomplete responses.
- Retry according to application policy when appropriate.
- Log validation failures for evaluation and improvement.

---

# Relationship with Previous Phases

- Step 3 defines prompt templates.
- Step 5 defines system prompt behavior.
- Step 6 defines request processing.
- Phase 7 defines API response handling.

---

# Out of Scope

This document intentionally does not define:

- Concrete JSON schemas.
- Provider-specific structured output features.
- Business validation rules.
- Retry algorithms.
- Evaluation metrics.

---

# Acceptance Criteria

- Output contract principles documented.
- Response validation responsibilities defined.
- Structured response architecture established.
- Ready for Prompt Evaluation & Testing.

---

## Next

Step 8 — Prompt Evaluation & Testing.