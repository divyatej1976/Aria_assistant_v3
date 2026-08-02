# ARIA — Phase 3: System Architecture

## Step 7 — Security & Trust Architecture

**Status:** Draft v1

## Purpose

This document defines the trust boundaries, security principles and authorization model that protect learner data, system integrity and AI interactions throughout ARIA.

---

# Security Principles

- Security by design.
- Least privilege.
- Explicit authorization.
- Privacy-first handling of learner data.
- Validate every external input.
- Never trust AI output without validation.

---

# Trust Boundaries

Trusted:
- Validated business rules
- Authoritative database state
- Verified user identity

Untrusted:
- User input
- AI provider output
- External APIs
- Uploaded files until processed

---

# Authentication

Authentication verifies identity but does not grant permissions by itself.

Supported through an external authentication provider integrated with ARIA.

---

# Authorization

Every protected operation must verify:

- identity;
- ownership;
- required permissions.

Learners may only access and modify their own learning data.

---

# Data Protection

- Sensitive learner information should remain private.
- Secrets are never stored in source code.
- Provider credentials remain server-side.
- Audit-relevant actions should be traceable.

---

# AI Trust Rules

- AI suggestions require deterministic validation where applicable.
- AI cannot create authoritative learner state.
- AI cannot bypass authorization or ownership rules.

---

# Acceptance Criteria

- Trust boundaries are documented.
- Authentication and authorization responsibilities are separated.
- AI trust model is defined.
- Privacy principles are established.
- Architecture aligns with previous Phase 3 documents.

---

## Next

Step 8 — Observability Architecture.
