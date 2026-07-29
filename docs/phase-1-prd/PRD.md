# ARIA — Canonical Product Requirements Document

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** FROZEN for R0 / baseline for subsequent phases  
**Vision source:** [`../../VISION.md`](../../VISION.md)  
**Detailed requirement sources:** `01`–`08` documents in this directory and `R0-DECISIONS.md`

---

# 1. Product Definition

ARIA is an AI-powered learning operating system initially intended for **college students, recent graduates and early-career learners** pursuing concrete academic, placement, competitive-exam, certification, interview, technical/professional skill or upskilling goals.

ARIA's long-term thesis is not merely to place many study features in one interface. It is to let learning systems share persistent learner context and evidence so that what happens next can adapt intelligently while preserving learner control.

Core problem:

> **Learners perform excessive manual coordination across fragmented study, resources, assessment, revision, planning and progress workflows.**

ARIA aims to reduce that coordination burden without automating away the intellectual effort required to learn.

---

# 2. Product Principles

1. **Vision stays broad; releases stay hypothesis-driven.**
2. **Long-term domain independence does not require universal R0 validation.**
3. **Validate specific cases before generalizing abstractions.**
4. **Avoid unnecessary domain-specific coupling, not every domain-specific implementation detail.**
5. **Evidence precedes strong learner-state claims.**
6. **Conversational memory and evidence-backed learner state are different systems.**
7. **One wrong answer is not a confirmed misconception.**
8. **One correct answer is not mastery.**
9. **Meaningful adaptation should be traceable and correctable.**
10. **Learner control remains important for consequential changes.**
11. **Not every subsystem should be an AI agent.**
12. **Use deterministic logic where deterministic logic is the correct tool.**
13. **External specialist learning platforms may remain part of the ecosystem.**
14. **ARIA earns complexity through validation.**
15. **The complete product vision is not R0 scope.**

---

# 3. Audience Boundary

Initial audience:

> **College students, recent graduates and early-career learners working toward concrete learning or preparation goals.**

Representative contexts include university subjects/exams, placements, interviews, certifications, competitive/government exams and technical/professional upskilling.

ARIA is not initially optimized for primary-school education, institutional LMS administration, classroom/teacher management or corporate training administration.

---

# 4. Long-Term Product Direction

ARIA may eventually connect:

- goals and learning contexts;
- resources;
- Study/tutoring;
- assessments and evaluation;
- structured learning evidence;
- Learner Model;
- Roadmaps;
- Revision;
- Progress;
- Planner and scheduling;
- Notes;
- Audio/voice revision;
- reminders/notifications;
- recommendations/Home;
- external learning integrations;
- bounded cross-system orchestration.

These systems are release-sequenced. Their presence in the vision does not make them R0 requirements.

---

# 5. Release Strategy

```text
R0 — Prove adaptive learning
        ↓
R1 — Prove learning-path adaptation
        ↓
R2 — Prove longitudinal learning
        ↓
R3 — Prove learning coordination
        ↓
R4 — Expand learning interfaces
        ↓
R5 — Prove mature cross-system orchestration
```

## R0
Test whether evidence can change a basic learner state and whether that state appropriately changes subsequent Study.

## R1
Introduce structured Roadmap/learning-path adaptation.

## R2
Introduce longitudinal evidence, richer Learner Model, Revision/Progress, memory v1 and conservative misconception reasoning.

## R3
Introduce Planner, deadlines, reminders, availability and multi-goal coordination.

## R4
Introduce Notes, Audio and richer resource/learning interfaces.

## R5
Validate mature cross-system orchestration, integrations and justified agentic workflows.

---

# 6. R0 Hypothesis

> **ARIA can observe meaningful learning evidence, update a basic learner state, and use that state to appropriately change the learner's next study experience.**

R0 loop:

```text
Goal / Learning Context
          ↓
       Resources
          ↓
         Study
          ↓
      Assessment
          ↓
      Evaluation
          ↓
    Basic Evidence
          ↓
 Basic Learner State
          ↓
Adapt Next Study Experience
          ↓
Targeted Reassessment
          ↓
      New Evidence
          ↺
```

The second cycle is required. R0 is not validated by a one-shot demonstration.

---

# 7. Frozen R0 Validation Slice

## Context

A **college-level DBMS** validation context, initially centered on:

- Transactions;
- Concurrency Control;
- Schedules;
- Serializability.

This is validation configuration/data, not a permanent DBMS-specific core architecture.

## Resources

R0 supports:

- PDF upload;
- pasted text.

## Study

The learner can study within the selected context/resources, ask questions and receive explanations. Where grounding is expected, ARIA uses the selected resources and does not falsely claim unavailable retrieval.

## Assessment

Required R0 assessment: **MCQ**.

Supported configuration may include:

- question count within limits;
- topic/concept scope;
- difficulty within supported levels;
- optional time limit;
- targeted reassessment.

Short-answer evaluation is optional for R0 and cannot block completion.

## Evaluation

Required MCQ evaluation is deterministic. Invalid/failed evaluation creates no learning evidence.

## Evidence

Usable evaluated responses create structured concept-attributed evidence with provenance to learner, context, assessment/attempt/question and evaluation.

## Basic Learner State

```text
UNTESTED
DEVELOPING
NEEDS_REVIEW
SUPPORTED
```

Each state retains supporting evidence/provenance, confidence, update time and reason/rule.

## Adaptation

R0 may:

- prioritize a weak/uncertain concept;
- change explanation strategy;
- add a worked example;
- recap prerequisites when justified;
- increase/decrease scaffolding;
- provide targeted practice/check questions;
- reduce unnecessary repetition for supported concepts;
- request more evidence instead of forcing a strong conclusion.

---

# 8. R0 Evidence Policy

Initial conservative defaults:

```text
No sufficient evidence
        → UNTESTED

One usable observation
        → DEVELOPING

≥2 aligned weak observations across distinct opportunities
        → candidate NEEDS_REVIEW

≥2 aligned correct observations across distinct opportunities,
including independent/later evidence
        → candidate SUPPORTED

Mixed / contradictory evidence
        → DEVELOPING or lower-confidence conservative prior state
```

Rules:

- one result cannot establish a strong state;
- `SUPPORTED` is not permanent mastery;
- no evidence is not weakness;
- invalid evaluation is not evidence;
- corrections propagate into dependent state/adaptation;
- reassessment can strengthen, weaken or reverse prior state;
- these are R0 engineering/validation defaults, not universal educational-science claims.

---

# 9. R0 Functional Requirements Summary

R0 requires:

- account creation/authenticated persistent learner identity;
- one active validation goal/context minimum;
- persistent context across sessions;
- learner-owned data isolation;
- PDF/pasted-text resource handling;
- grounded Study interaction;
- configurable MCQ assessment;
- deterministic MCQ evaluation;
- structured concept-attributed evidence;
- conservative basic learner state;
- traceable Study adaptation;
- targeted reassessment/second cycle;
- correction propagation;
- failure-safe persistence;
- enough instrumentation/audit information to validate Gate A.

Detailed requirement IDs remain in the source Step documents.

---

# 10. Cross-System Requirements

R0 requires one bounded chain:

```text
Context
  ↓
Study / Resources
  ↓
Assessment Submitted
  ↓
Evaluation
  ↓
Evidence Recorded
  ↓
Learner-State Reconsideration
  ↓
Adaptation Decision
  ↓
Adapted Study
  ↓
Targeted Reassessment
  ↓
New Evidence
  ↺
```

Consequential transitions must retain context/provenance.

Retries must not duplicate consequential state.

Failure in one downstream stage must not erase valid prior state.

R0 does not require event-bus infrastructure, microservices, a multi-agent framework or fan-out to Planner/Roadmap/Progress/Notifications.

---

# 11. AI & Learner-Model Boundaries

ARIA separates:

- **Context** — relevant information for the current activity;
- **Memory** — durable useful learner/environment information, introduced more fully later;
- **Evidence** — observations of learning performance;
- **Learner State** — conservative conclusions derived from evidence;
- **Adaptation** — action selected using state + context + rules/AI where justified.

R0 does not require:

- lifelong memory;
- universal mastery ontology;
- full misconception engine;
- universal prerequisite graph;
- autonomous multi-agent tutoring.

AI output used in consequential structured flows must be validated/bounded where applicable. Deterministic decisions should remain deterministic when appropriate.

---

# 12. Security, Privacy & Reliability

R0 is a real small-scale application handling private learner data, not a throwaway unsafe demo.

R0 blockers include:

- established authentication mechanism;
- trusted-boundary/server authorization;
- object-level and cross-user data isolation;
- private-by-default resources, conversations, attempts, evidence and learner state;
- secrets not committed/exposed to clients;
- appropriate session/token security;
- HTTPS/TLS for remote deployment;
- common web protections appropriate to the chosen stack;
- prompt/resource injection boundaries where untrusted content is processed;
- data minimization;
- referential/evidence integrity;
- explicit processing/failure states;
- bounded retries/model/resource usage;
- idempotency for consequential operations;
- correction/recomputation support;
- validation-data reset/delete support;
- baseline accessibility;
- traceability of the adaptive loop.

R0 does not require internet-scale distributed architecture or public-production SLAs before the hypothesis is validated.

---

# 13. Gate A — Engineering Validation

Gate A is mandatory and rigorous.

Required controlled scenarios:

1. repeated weak evidence causes expected targeted adaptation;
2. supported evidence causes appropriately different behaviour;
3. insufficient evidence does not create strong conclusions;
4. evaluation failure creates no false evidence;
5. contradictory evidence remains uncertainty-aware;
6. context isolation is preserved;
7. corrections propagate;
8. retries are idempotent for consequential state;
9. downstream AI failure preserves valid persisted state;
10. adapted Study → reassessment → new evidence closes the second cycle;
11. cross-user private-data isolation holds.

Critical failures include authorization/privacy violations, wrong evidence attribution, false evidence creation, incorrect controlled state transitions, unrelated adaptations, correction failure, duplicate consequential state, loss of valid persisted state, inability to close the repeated cycle or unsafe security/secrets handling.

**Gate A passes only with zero unresolved critical failures and reproducible passing critical scenarios.**

---

# 14. Gate B — Real-User Signal

Target:

- 5–10 target learners where realistically available;
- at least two connected cycles per participant where feasible;
- aim for 10+ completed adaptive cycles total;
- report actual numbers honestly.

Collect:

- baseline assessment observations;
- adaptation and targeted reassessment observations;
- adaptation relevance/usefulness;
- whether learners understand why ARIA adapted;
- incorrect/confusing adaptations;
- corrections;
- qualitative feedback;
- willingness to continue.

If fewer than five usable participants are available, report the exercise as a pilot.

Gate B provides directional evidence. It does not establish causal learning improvement or statistical significance.

---

# 15. R0 Explicit Non-Goals

R0 is not blocked by:

- Notes;
- Audio;
- Planner;
- reminders/notifications;
- full Roadmap generation/adaptation;
- sophisticated Progress dashboards;
- mature Revision/spaced repetition;
- full misconception detection;
- universal prerequisite graphs;
- external-platform tracking;
- production coding sandbox;
- advanced multi-agent orchestration;
- every resource type;
- every assessment format;
- multiple simultaneous goals;
- broad domain validation;
- public-production operational maturity;
- distributed scale architecture.

These capabilities remain in ARIA's later vision.

---

# 16. R0 Exit Condition

R0 does not exit because screens exist or because the pipeline executed once.

R0 exits when:

1. implementation satisfies the R0 functional/non-functional blockers;
2. Gate A passes reproducibly with zero unresolved critical failures;
3. Gate B is conducted and reported at the achievable project scale;
4. results, limitations and failures are documented honestly.

Defensible validation statement:

> **The adaptive pipeline was rigorously validated through controlled engineering scenarios. Small-scale real-user testing then provided directional before/after evidence and qualitative feedback, without claiming statistically established causal improvement.**

---

# 17. Requirement Traceability

| Product concern | Primary detailed source | R0 disposition |
|---|---|---|
| Product goals/audience/domain | `01-product-overview-goals.md` | R0 constrained, long-term broad |
| Identity/goals/context | `02-user-context-requirements.md` | one persistent validation context required |
| User-facing functionality | `03-functional-requirements.md` | release-classified; R0 adaptive spine only |
| Cross-system behaviour | `04-cross-system-requirements.md` | bounded R0 adaptive chain |
| AI/evidence/learner model | `05-ai-learner-model-memory-evidence.md` | basic evidence-backed state; richer intelligence later |
| Security/privacy/reliability/accessibility | `06-non-functional-privacy-security-reliability-accessibility.md` | R0 blockers/targets separated from public maturity |
| Release boundaries | `07-scope-prioritization-release-boundaries.md` | R0–R5 hypothesis sequence |
| Acceptance/validation | `08-acceptance-criteria-success-metrics-prd-closure.md` | Gate A + Gate B |
| Concrete R0 choices | `R0-DECISIONS.md` | frozen implementation baseline |

No unresolved traceability conflict currently blocks the next phase.

---

# 18. Change Control

This PRD is frozen as the **R0 baseline**, not frozen forever.

Changes are allowed when implementation/validation exposes a genuine incorrect assumption or blocker. Such changes should be documented deliberately rather than silently expanding scope.

A desired long-term feature is not sufficient reason to pull it into R0.

---

# 19. Phase 1 Closure

The following are complete:

- Phase 0 vision alignment;
- audience/domain correction;
- R0 feature-scope correction;
- Gate A/Gate B validation correction;
- Steps 1–8 consistency audit;
- R0 validation context selection;
- resource/assessment surface selection;
- learner-state definition;
- adaptation policy;
- evidence thresholds;
- critical Gate A definition;
- practical Gate B scope;
- final requirement traceability review;
- canonical PRD consolidation.

> **PHASE 1 — PRODUCT REQUIREMENTS DOCUMENT: FROZEN FOR R0.**

The next phase may now use this document as its product baseline without inventing missing R0 product behaviour.