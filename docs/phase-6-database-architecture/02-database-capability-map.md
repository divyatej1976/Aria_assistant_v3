# ARIA — Phase 6: Database Architecture

## Step 2 — Database Capability Map

**Status:** Draft v1

## Purpose

This document identifies every major data domain that ARIA must persist and maps each domain to its architectural responsibility. It provides the blueprint for the entity model and schema design developed in later documents.

---

# Core Data Domains (R0)

## Learner Domain
- Learner profile
- Preferences
- Goals
- Learner state

## Learning Domain
- Courses
- Topics
- Concepts
- Study sessions

## Evidence Domain
- Evidence records
- Assessments
- Revision history
- Provenance

## Resource Domain
- Uploaded resources
- Extracted content
- Metadata
- Retrieval references

## Conversation Domain
- Conversations
- Messages
- Session references

## Vector Domain
- Embeddings
- Chunk references
- Retrieval metadata

---

# Future Data Domains

- Planner
- Roadmaps
- Career planning
- Collaboration
- Notifications
- Analytics

---

# Mapping Principles

- One responsibility per domain.
- Minimize duplication.
- Preserve traceability.
- Support modular growth.
- Separate relational and vector responsibilities.

---

# Out of Scope

This document intentionally does not define:

- Table schemas.
- Foreign keys.
- Indexes.
- SQL implementation.
- ORM models.

---

# Acceptance Criteria

- Core data domains identified.
- Future domains separated.
- Domain responsibilities documented.
- Foundation prepared for entity modeling.

---

## Next

Step 3 — Core Entity Model.
