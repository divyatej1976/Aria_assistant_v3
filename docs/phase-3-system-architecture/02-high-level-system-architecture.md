# ARIA — Phase 3: System Architecture

## Step 2 — High-Level System Architecture

**Status:** Draft v1

## Purpose

This document defines the major architectural building blocks of ARIA R0 and the responsibilities between them. It intentionally avoids database schemas, API contracts, prompt design and implementation details.

---

# Architectural Layers

```text
Learner
   │
   ▼
Next.js Web Application
   │
   ▼
ARIA Application Backend (FastAPI)
   │
   ├── Learning Context
   ├── Resources
   ├── Study
   ├── Assessment
   ├── Evaluation
   ├── Evidence
   ├── learner_concept_state
   └── Adaptation
   │
   ├── PostgreSQL
   ├── Object Storage
   ├── Vector Search
   └── AI Provider Abstraction
```

---

# Layer Responsibilities

## Presentation Layer

Responsible for user interaction, rendering UI, authentication flow, navigation and displaying application state.

## Application Layer

Coordinates workflows and enforces business rules. It owns the adaptive-learning loop.

## Intelligence Layer

Provides bounded AI capabilities such as study assistance, grounded explanations and question generation through provider abstractions.

## Persistence Layer

Stores application state, resources, evidence and learner information.

---

# Core R0 Workflow

```text
Learning Context
      ↓
Resources
      ↓
Study
      ↓
Assessment
      ↓
Evaluation
      ↓
Evidence
      ↓
learner_concept_state
      ↓
Adaptation
      ↓
Targeted Study
```

This workflow is the architectural backbone of R0.

---

# External Dependencies

ARIA communicates with external providers only through bounded interfaces.

Examples:

- LLM Provider
- Embedding Provider
- Authentication Provider
- File Storage Provider
- Email Provider

Business logic must not depend directly on provider-specific APIs.

---

# Architectural Characteristics

- Modular monolith for R0.
- Clear separation of deterministic logic and AI generation.
- Single ownership for critical state.
- Replaceable providers.
- Explainable adaptive workflow.
- Future extensibility without premature implementation.

---

# Out of Scope

This document does not define:

- database schema;
- API endpoints;
- prompt engineering;
- memory architecture;
- deployment topology;
- implementation folders.

These are specified in later phases.

---

# Acceptance Criteria

- High-level architectural layers are defined.
- Responsibilities are separated.
- Core adaptive-learning workflow is represented.
- External dependencies remain outside the core system.
- Architecture remains consistent with the frozen Vision, PRD and UX.

---

## Next

Step 3 — Module Boundary Specification.
