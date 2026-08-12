# ARIA — Phase 9: Prompt Engineering Architecture

## Step 9 — Prompt Versioning & Governance

**Status:** Draft v1

## Purpose

This document defines how prompts are versioned, reviewed and governed throughout their lifecycle. It establishes architectural rules for controlled prompt evolution, traceability and change management while preserving consistency across AI providers and application releases.

---

# Versioning Principles

- Every prompt template has an identifiable version.
- Significant prompt changes create new versions.
- Prompt history remains traceable.
- Versioning is independent of AI providers.
- Deprecated prompts remain available for audit purposes where required.

---

# Governance Principles

- Prompt ownership is explicitly assigned.
- Significant changes require review before adoption.
- Architectural prompt changes should be documented using ADRs.
- Prompt documentation and implementation remain synchronized.
- Prompt governance aligns with the overall system architecture.

---

# Change Management

- Review proposed changes.
- Validate against evaluation results.
- Assess cross-phase architectural impact.
- Approve and version changes.
- Retire obsolete prompts through a controlled process.

---

# Relationship with Previous Phases

- Step 2 defines the prompt lifecycle.
- Step 8 defines prompt evaluation.
- Phase 3 establishes ADR-based architectural governance.

---

# Out of Scope

This document intentionally does not define:

- Repository branching strategies.
- Provider-specific prompt formats.
- Runtime prompt selection.
- CI/CD workflows.
- Implementation tooling.

---

# Acceptance Criteria

- Versioning principles documented.
- Governance process established.
- Change management defined.
- Ready for Prompt Review & Phase Freeze.

---

## Next

Step 10 — Prompt Review & Phase Freeze.
