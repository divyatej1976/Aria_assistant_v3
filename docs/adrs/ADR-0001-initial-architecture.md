# ADR-0001 — Initial ARIA Architecture

## Status
Accepted

## Context
ARIA required a stable architectural foundation before implementation.

## Decision
The project adopts the following foundational decisions:

1. AI assists; deterministic systems decide.
2. Evidence drives learner-state updates.
3. Learner state is explainable and reproducible.
4. R0 validates a constrained learning domain before broader generalization.
5. Architecture remains modular and provider-independent.
6. Major architectural changes require new ADRs.

## Alternatives Considered
- Fully AI-driven learner model.
- Domain-specific architecture.
- Monolithic tightly coupled design.

## Consequences
### Benefits
- Explainability
- Extensibility
- Testability
- Long-term maintainability

### Trade-offs
- More architectural discipline.
- Additional documentation effort.

## Related Documents
- Phase 0 Vision
- Phase 1 PRD
- Phase 3 System Architecture
- Phase 4 AI Architecture