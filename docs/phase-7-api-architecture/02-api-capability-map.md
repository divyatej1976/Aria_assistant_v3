# ARIA — Phase 7: API Architecture

## Step 2 — API Capability Map

**Status:** Draft v1

## Purpose

This document identifies the major API capability domains required by ARIA. It maps business capabilities to API boundaries before defining specific endpoints, ensuring modularity, consistency and future extensibility.

---

# Core API Capability Domains (R0)

## Authentication
- Sign in
- Sign out
- Session management
- Token refresh

## Learner
- Profile
- Preferences
- Goals
- Progress

## Study
- Study sessions
- Learning plans
- Topic retrieval

## Conversation
- Chat sessions
- Messages
- Conversation history

## Assessment
- Quiz lifecycle
- Submission
- Results

## Evidence
- Evidence records
- Confidence updates
- learner_concept_state updates

## Resources
- Upload
- Metadata
- Retrieval
- Resource management

## AI Services
- Study assistance
- Assessment generation
- Adaptation
- Retrieval orchestration

---

# Future Capability Domains

- Planner
- Career guidance
- Collaboration
- Notifications
- Analytics
- Administration

---

# Mapping Principles

- APIs expose business capabilities.
- Keep services cohesive.
- Avoid overlapping responsibilities.
- Support independent evolution.
- Preserve clear ownership boundaries.

---

# Out of Scope

This document intentionally does not define:

- Endpoint URLs.
- HTTP methods.
- Request schemas.
- Response schemas.
- Authentication implementation.

---

# Acceptance Criteria

- Core capability domains identified.
- Future capabilities separated.
- Ownership boundaries documented.
- Ready for API design standards.

---

## Next

Step 3 — API Design Standards.
