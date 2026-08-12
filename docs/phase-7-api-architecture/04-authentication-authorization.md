# ARIA — Phase 7: API Architecture

## Step 4 — Authentication & Authorization

**Status:** Draft v1

## Purpose

This document defines ARIA's authentication and authorization architecture. It establishes identity, access control and security boundaries for API communication while remaining independent of business logic.

---

# Authentication Principles

- Every protected request must be authenticated.
- Identity is verified before business logic executes.
- Authentication should be delegated to the identity provider where practical.
- Session handling must remain secure and predictable.

---

# Authorization Principles

- Access decisions are based on permissions, not assumptions.
- Apply least-privilege access.
- Authorization is enforced server-side.
- Ownership checks are explicit.

---

# Identity Responsibilities

Authentication architecture is responsible for:

- User identity.
- Session validation.
- Token validation.
- Protected endpoint access.
- Permission boundaries.

---

# Integration Strategy

- Supabase Auth provides identity management.
- FastAPI validates authenticated requests.
- Business services consume authenticated identity without managing credentials.

---

# Out of Scope

This document intentionally does not define:

- Role definitions.
- OAuth provider configuration.
- UI login flows.
- Session storage implementation.
- Endpoint-specific permissions.

---

# Acceptance Criteria

- Authentication principles documented.
- Authorization boundaries established.
- Identity responsibilities defined.
- Ready for Core Service API design.

---

## Next

Step 5 — Core Service APIs.
