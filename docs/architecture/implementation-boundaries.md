# ARIA Implementation Boundaries

## Dependency direction

```text
HTTP/API routes
      ↓
Application services and workflows
      ↓
Domain entities and invariants
      ↓
Repositories / provider interfaces
      ↓
Infrastructure implementations
```

Routes must not contain business rules. UI components must not decide learner state. AI providers must not write directly to persistence.

## Ownership model

Every learner-owned record carries an `owner_id` or is reachable through an owner-scoped parent. Every read and write must establish the authenticated learner before accessing the record.

## Consequential workflow model

Consequential operations use an idempotency key and preserve intermediate state:

```text
Submitted → Evaluating → Evaluated → Evidence recorded → State updated → Adaptation ready
```

Failures preserve valid previous stages and expose a retryable state.

## Future capability extension points

- Notes consume resources, messages, and concepts.
- Audio consumes approved notes/resources and creates retryable jobs.
- Planner consumes goals, deadlines, availability, progress, and learner state.
- Progress consumes meaningful activity, assessments, evidence, and completed plans.
- MAO coordinates application services and cannot bypass domain rules or authorization.

