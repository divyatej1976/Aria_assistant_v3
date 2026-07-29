# ARIA — Phase 1: Product Requirements Document

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document (PRD)  
**Status:** ✓ COMPLETE — FROZEN FOR R0  
**Source of truth:** [`PRD.md`](./PRD.md)  
**Vision:** [`VISION.md`](../../VISION.md)

---

## Phase 1 Result

Phase 1 has converted the reviewed ARIA vision into an executable R0 product specification while preserving the larger Learning OS direction.

The three major scope corrections are frozen:

1. **Domain breadth:** long-term domain-extensible; R0 validates one concrete context before generalization.
2. **Feature breadth:** the complete Learning OS is not R0; R0 is the smallest complete adaptive-learning loop.
3. **Validation breadth:** Gate A is rigorous engineering validation; Gate B is small-scale directional real-user evidence without causal overclaiming.

---

## Canonical Documents

| Document | Role | Status |
|---|---|---|
| `PRD.md` | Canonical Phase 1 / R0 product baseline | ✓ FROZEN |
| `R0-DECISIONS.md` | Concrete R0 validation and implementation choices | ✓ FROZEN |
| `01-product-overview-goals.md` | Product goals, audience, domain and R0 hypothesis | ✓ AUDITED |
| `02-user-context-requirements.md` | Learner identity, goals, context and continuity | ✓ AUDITED |
| `03-functional-requirements.md` | Full-vision functional requirements by release | ✓ AUDITED |
| `04-cross-system-requirements.md` | Adaptive chain and later orchestration | ✓ AUDITED |
| `05-ai-learner-model-memory-evidence.md` | AI, evidence and learner-state requirements | ✓ AUDITED |
| `06-non-functional-privacy-security-reliability-accessibility.md` | Security, privacy, reliability and accessibility | ✓ AUDITED |
| `07-scope-prioritization-release-boundaries.md` | R0–R5 hypothesis-driven boundaries | ✓ AUDITED |
| `08-acceptance-criteria-success-metrics-prd-closure.md` | Gate A/Gate B acceptance and closure | ✓ COMPLETE |

---

## Frozen R0

```text
Authenticated learner
        ↓
One DBMS validation context
        ↓
PDF and/or pasted text
        ↓
Grounded Study
        ↓
Configurable MCQ assessment
        ↓
Deterministic evaluation
        ↓
Concept-attributed evidence
        ↓
UNTESTED / DEVELOPING / NEEDS_REVIEW / SUPPORTED
        ↓
Traceable Study adaptation
        ↓
Targeted MCQ reassessment
        ↓
New evidence + state reconsideration
        ↺
```

Initial validation content is college-level DBMS, centered on Transactions, Concurrency Control, Schedules and Serializability. This is a validation fixture rather than a permanent hardcoded product domain.

---

## Evidence Defaults

R0 begins conservatively:

- no sufficient evidence → `UNTESTED`;
- one usable observation → `DEVELOPING`;
- at least two aligned weak observations across distinct opportunities → candidate `NEEDS_REVIEW`;
- at least two aligned correct observations across distinct opportunities, including independent/later evidence → candidate `SUPPORTED`;
- mixed/contradictory evidence → conservative/uncertain state.

One answer never becomes permanent mastery or confirmed misconception.

---

## Validation Finish Line

### Gate A

Controlled, reproducible validation of evidence → state → adaptation → reassessment, including failure, correction, idempotency, context/user isolation and second-cycle scenarios.

**Zero unresolved critical Gate A failures are allowed at R0 exit.**

### Gate B

Target 5–10 learners where realistically available, two connected cycles each where feasible, and 10+ total adaptive cycles as a practical target.

Results are reported as directional evidence, not causal proof.

---

## Release Direction

```text
R0 — Adaptive learning
 ↓
R1 — Learning-path / Roadmap adaptation
 ↓
R2 — Longitudinal learning / Revision / Progress / richer learner model
 ↓
R3 — Planner / deadlines / reminders / multi-goal coordination
 ↓
R4 — Notes / Audio / richer learning interfaces
 ↓
R5 — Mature orchestration / integrations / justified agentic workflows
```

---

## Explicit R0 Deferrals

Notes, Audio, Planner, reminders, full Roadmaps, sophisticated Progress, mature Revision, full misconception detection, broad external integrations, production coding sandbox, advanced multi-agent orchestration, every resource/assessment type, multiple simultaneous goals, universal-domain validation and internet-scale architecture are **not R0 blockers**.

They remain part of ARIA's later product direction.

---

## Phase Status

```text
Phase 0 — Product Vision                         ✓ COMPLETE
Phase 1 — Product Requirements Document         ✓ COMPLETE / FROZEN
├── Steps 1–8                                   ✓ AUDITED
├── Consistency audit                           ✓ COMPLETE
├── R0 decisions                                ✓ RESOLVED
├── Requirement traceability                    ✓ CHECKED
└── Canonical PRD.md                             ✓ CREATED / FROZEN
```

---

## Next

Use `PRD.md` as the product baseline for the next phase.

The next phase should translate the frozen R0 requirements into concrete product flows and/or system design without silently re-expanding R0 scope. Architecture and implementation choices should satisfy the PRD rather than rewrite the product requirements to fit a preferred technology.