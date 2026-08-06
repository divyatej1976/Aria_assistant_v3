# ARIA — Phase 9: Prompt Engineering Architecture

## Step 6 — User Prompt Processing

**Status:** Draft v1

## Purpose

This document defines how ARIA processes user requests before they are combined with prompt templates and runtime context. It establishes a deterministic pipeline for validation, normalization, classification and routing while preserving security, consistency and provider independence.

---

# Processing Principles

- Validate user input before AI processing.
- Normalize requests into a consistent internal representation.
- Classify intent before prompt selection.
- Apply safety and authorization checks.
- Route requests using deterministic rules.

---

# Processing Pipeline

1. Receive User Input
2. Validate Request
3. Normalize Input
4. Classify Intent
5. Apply Safety & Authorization Checks
6. Select Agent & Prompt Template
7. Assemble Runtime Context
8. Invoke AI Provider

---

# Routing Rules

- Routing decisions are deterministic.
- Business rules govern routing.
- Prompt templates are selected based on classified intent.
- Runtime context is assembled only after successful validation.

---

# Relationship with Previous Phases

- Phase 7 validates API requests.
- Phase 8 determines agent responsibilities.
- Step 4 defines context composition.
- Step 5 defines system prompt behavior.

---

# Out of Scope

This document intentionally does not define:

- Intent classification algorithms.
- Provider-specific request formats.
- Prompt template contents.
- Output validation.
- Runtime performance optimization.

---

# Acceptance Criteria

- Processing pipeline documented.
- Routing principles established.
- Responsibilities clearly separated.
- Ready for Output Contracts & Structured Responses.

---

## Next

Step 7 — Output Contracts & Structured Responses.