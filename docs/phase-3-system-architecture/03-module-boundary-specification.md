# ARIA — Phase 3: System Architecture

## Step 3 — Module Boundary Specification

**Status:** Draft v1

## Purpose

This document defines the logical modules that make up ARIA R0, their responsibilities, ownership boundaries, and permitted interactions. The goal is to keep business logic cohesive, reduce coupling, and allow future evolution without major rewrites.

---

# Design Principles

- Each module owns one core business capability.
- Modules communicate through well-defined interfaces.
- No module reaches into another module's internal state.
- AI capabilities are consumed through dedicated services, not directly from business modules.
- Cross-module workflows are orchestrated rather than tightly coupled.

---

# Core R0 Modules

## Authentication
Owns authentication integration, user identity resolution and session validation.

## Learning Context
Owns learner goals, active context and current study scope.

## Resources
Owns uploaded learning materials, ingestion lifecycle and retrieval metadata.

## Study
Owns learner study interactions and grounded learning sessions.

## Assessment
Owns assessment creation, attempts and submission lifecycle.

## Evaluation
Owns deterministic scoring and assessment evaluation.

## Evidence
Owns validated learning evidence derived from completed evaluations.

## learner_concept_state
Owns current learner_concept_state computed from accumulated evidence.

## Adaptation
Owns adaptation decisions and preparation of the next study experience.

---

# Dependency Flow

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
```

Reverse dependencies should be avoided unless explicitly defined.

---

# Forbidden Dependencies

Examples:

- Study must not modify learner_concept_state directly.
- Assessment must not generate Evidence directly.
- AI providers must not update domain entities.
- Frontend components must not contain business rules.

---

# Shared Services

The following infrastructure services may be shared:

- Logging
- Configuration
- Authentication middleware
- AI provider abstraction
- Storage abstraction
- Event publishing

Shared services must not own business state.

---

# Extension Strategy

Future systems such as Roadmaps, Planner, Notes and Revision will be introduced as new modules rather than expanding unrelated existing modules.

---

# Acceptance Criteria

- Module responsibilities are explicit.
- Ownership boundaries are defined.
- Dependency direction is documented.
- Forbidden dependencies are identified.
- Future modules can be added without restructuring the R0 architecture.

---

## Next

Step 4 — Communication Architecture.
