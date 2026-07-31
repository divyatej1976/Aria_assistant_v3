# ARIA — Phase 2: Product & UX Design

## Step 8 — UX Consistency Review & Phase 2 Freeze

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 2 — Product & UX Design  
**Status:** FINAL — reviewed and frozen for Phase 3  
**Inputs:** `VISION.md`, frozen Phase 1 PRD, Phase 2 Steps 1–7

---

# 1. Purpose

This document is the final consistency audit for ARIA Phase 2.

Its job is to answer:

1. Does the R0 UX still test the hypothesis frozen in Phase 1?
2. Did Phase 2 accidentally reintroduce feature or domain breadth?
3. Are learner-state, evidence and adaptation semantics consistent across screens?
4. Are consequential failures recoverable without corrupting the learning loop?
5. Is the product structurally specified enough for Phase 3 architecture to begin?

Phase 2 is frozen only if all five answers are yes.

---

# 2. Frozen R0 Hypothesis

> **ARIA can observe meaningful learning evidence, update a basic learner state, and use that state to appropriately change the learner's next study experience.**

The UX implements this as:

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
Basic Learner State
      ↓
Adaptation Decision
      ↓
Adapted Study
      ↓
Targeted Reassessment
      ↓
New Evidence
      ↓
State Reconsideration
      ↺
```

**Review result: ALIGNED.**

---

# 3. Domain-Scope Audit

Frozen R0 validation context:

- college-level DBMS;
- Transactions;
- Concurrency Control;
- Schedules;
- Serializability;
- Conflict Serializability where useful for the controlled loop.

Phase 2 uses DBMS as the validation fixture without redefining ARIA as a DBMS product.

The UX does not require permanent branches such as:

```text
if goal == "DBMS"
```

Future domain generalization remains an architecture/product direction rather than an R0 UX promise.

**Review result: PASS.**

---

# 4. Feature-Scope Audit

Required R0 surfaces remain:

```text
Authentication / lightweight setup
Home
Resources
Study
Assessment
Results / Evidence
Basic Learner State
Adaptation
Targeted Reassessment
Cycle Summary
Minimal Account
```

The following complete-vision systems were **not** accidentally promoted into R0 requirements:

- Notes;
- Audio;
- Planner;
- full Roadmap engine;
- Roadmap adaptation;
- mature Revision/spaced repetition;
- sophisticated Progress dashboards;
- full misconception detection;
- notifications/email reminders;
- external-platform progress tracking;
- coding sandbox;
- broad multi-agent orchestration;
- every assessment format;
- every resource type;
- multiple simultaneous goals.

**Review result: PASS.**

---

# 5. R0 Route Audit

Phase 2 converges on the following primary route-level surfaces:

```text
/auth/sign-in
/auth/sign-up
/setup
/home
/resources
/study
/assessments
/assessments/:attempt
/assessments/:attempt/results
/account
```

Exact URLs are not frozen; the route responsibilities are.

Evidence detail, answer review, adaptation explanation and cycle summary may be nested routes, drawers, panels or dedicated views depending on Phase 3/implementation decisions.

**Review result: PASS.**

---

# 6. End-to-End Journey Audit

The complete required learner journey exists in the UX specification:

```text
Sign in / sign up
      ↓
Enter DBMS validation context
      ↓
Add PDF and/or pasted text
      ↓
Resource becomes ready
      ↓
Baseline Study
      ↓
Configure MCQ
      ↓
Take assessment
      ↓
Submit
      ↓
Deterministic evaluation
      ↓
Inspect score + evidence-backed signal
      ↓
Understand why ARIA is adapting
      ↓
Use adapted Study
      ↓
Take targeted reassessment
      ↓
Receive new evidence/state
      ↓
Inspect complete learning cycle
```

The second cycle is not optional for R0 validation.

**Review result: PASS.**

---

# 7. Assessment-Scope Audit

Phase 1 froze required R0 assessment to MCQ.

Phase 2 consistently treats:

- MCQ as the required formal evidence-producing format;
- question count as bounded/configurable;
- topic/concept as configurable within supported scope;
- difficulty as configurable within supported scope;
- timer as optional;
- targeted reassessment as new questions on the same concept;
- deterministic scoring as the required R0 evaluation path.

The UX does not require the long-term universal Assessment Engine to exist in R0.

**Review result: PASS.**

---

# 8. Formal vs Informal Evidence Audit

Phase 2 maintains a clear boundary:

```text
Study conversation / informal checks
        ≠
formal learner-state evidence by default
```

Formal R0 evidence originates from valid evaluated assessment opportunities.

This prevents ordinary chat interaction, hesitation or one informal wrong answer from silently becoming a learner diagnosis.

**Review result: PASS.**

---

# 9. Learner-State Semantics Audit

Frozen internal R0 states:

```text
UNTESTED
DEVELOPING
NEEDS_REVIEW
SUPPORTED
```

Frozen learner-facing defaults:

| Internal | Learner-facing |
|---|---|
| `UNTESTED` | Not enough evidence yet |
| `DEVELOPING` | Still building confidence |
| `NEEDS_REVIEW` | Worth reviewing |
| `SUPPORTED` | Current results look solid |

Across Phase 2:

- no evidence is not represented as weakness;
- one wrong answer does not automatically become `NEEDS_REVIEW`;
- one correct answer does not automatically become `SUPPORTED`;
- mixed evidence remains uncertain/conservative;
- `SUPPORTED` is not permanent mastery;
- states are not learner identity labels.

**Review result: PASS.**

---

# 10. Score vs Learner-State Audit

Phase 2 consistently preserves:

```text
Assessment score
= performance on one assessment

Learner state
= conservative conclusion derived from relevant evidence
```

The wireframes visually separate score from concept signal.

No UX rule equates a raw percentage directly with mastery/weakness.

**Review result: PASS.**

---

# 11. Evidence-Provenance Audit

A learner-facing signal can be traced conceptually through:

```text
Assessment
      ↓
Question
      ↓
Submitted answer
      ↓
Deterministic evaluation
      ↓
Concept attribution
      ↓
Evidence
      ↓
Learner state
      ↓
Adaptation rationale
```

The learner can inspect `Why this?` without being exposed to internal database IDs, prompts or implementation details.

**Review result: PASS.**

---

# 12. Adaptation Audit

Phase 2 keeps R0 adaptations bounded to Study-level actions such as:

- prioritize a concept;
- change explanation strategy;
- add a worked example;
- recap a prerequisite when justified;
- change scaffolding;
- provide targeted practice/checks;
- reduce unnecessary repetition;
- request more evidence instead of forcing a strong conclusion.

Phase 2 does not introduce Planner/Roadmap/Notes/Audio adaptation into R0.

**Review result: PASS.**

---

# 13. Explainability Audit

Before/around meaningful adaptation, the UX can answer:

```text
What did ARIA notice?
What evidence supports that?
What is ARIA changing?
Why this change?
What happens after it?
```

The learner may inspect evidence and may continue normal Study instead of being trapped in a remediation flow.

**Review result: PASS.**

---

# 14. Correction Audit

The UX supports challenge/recheck of assessment results.

If a correction changes an evaluation:

```text
Evaluation
      ↓
Evidence
      ↓
Learner State
      ↓
Pending / existing Adaptation
```

must be recomputed, updated or invalidated as required.

Stale `NEEDS_REVIEW` messaging cannot remain presented as current after its supporting evidence is corrected.

**Review result: PASS.**

---

# 15. Reassessment Independence Audit

Targeted reassessment is explicitly described as a **new evidence opportunity**, not repetition of a revealed answer.

The UX communicates that new questions are used so ARIA can gather another signal on the concept.

This is essential to Gate A and to defensible Gate B observations.

**Review result: PASS.**

---

# 16. Causal-Claim Audit

Phase 2 does not claim:

- ARIA caused learning improvement;
- one before/after result proves effectiveness;
- a learner has permanently mastered a concept;
- R0 is statistically validated.

The cycle UI uses wording such as:

> Your latest check added new correct evidence. ARIA updated the current signal accordingly.

This remains compatible with the frozen Gate B standard: directional real-user evidence, not causal proof.

**Review result: PASS.**

---

# 17. Grounding-Honesty Audit

When Study uses learner material, the UX exposes source context.

When retrieval fails, ARIA must either:

- retry grounding; or
- explicitly switch to a general explanation without claiming it came from the resource.

This prevents source/grounding theater.

**Review result: PASS.**

---

# 18. Failure-Recovery Audit

The central recovery invariant is consistent across Phase 2:

> **If stage N fails, valid completed stages before N remain valid, and incomplete stages after N must not be represented as complete.**

Examples:

- PDF processing failure does not create a ready resource;
- assessment-generation failure creates no evidence;
- uncertain submission is reconciled before another attempt is created;
- evaluation failure creates no false negative evidence;
- evidence failure does not pretend learner state updated;
- learner-state failure does not pretend adaptation is current;
- adapted-Study generation failure does not erase assessment/evidence/state;
- retry cannot duplicate consequential state.

**Review result: PASS.**

---

# 19. Refresh / Multi-Tab / Resume Audit

Phase 2 defines authoritative-state recovery for:

- refresh;
- session expiry;
- returning later;
- another tab submitting an assessment;
- async resource processing;
- evaluation pending/failure;
- correction propagation;
- adaptation readiness.

Back navigation cannot unsubmit assessments or revert evidence/state.

**Review result: PASS.**

---

# 20. Home Audit

Home remains a **next-action surface**, not a mature Progress dashboard.

It may show:

- current learning context;
- current actionable learning signal;
- resume/recovery state;
- next meaningful action;
- recent cycle summary.

It does not require charts, streaks, fake mastery percentages or future-system widgets.

**Review result: PASS.**

---

# 21. Navigation Audit

R0 navigation remains intentionally small:

```text
Home
Study
Assessments
Resources
Account
```

Future features do not appear as disabled navigation clutter.

This keeps the visible product consistent with actual R0 scope.

**Review result: PASS.**

---

# 22. Responsive UX Audit

Phase 2 defines three structural behaviours:

## Desktop
Navigation + primary task area + optional contextual panel.

## Tablet
Collapsed navigation and drawers where necessary.

## Mobile
Single-task hierarchy with contextual details moved to sheets/full-screen views.

No requirement depends on desktop-only hover or permanently visible side panels.

**Review result: PASS.**

---

# 23. Accessibility Audit

Phase 2 consistently requires:

- semantic headings/landmarks;
- keyboard-accessible primary interactions;
- visible focus;
- labeled form and MCQ controls;
- non-colour-only status/error communication;
- touch-friendly targets;
- accessible modal/drawer focus handling;
- understandable async status;
- timer warnings not conveyed only visually;
- no essential hover-only interactions.

Exact WCAG conformance testing belongs to implementation/testing, but accessibility is now an architectural/UI constraint rather than an afterthought.

**Review result: PASS.**

---

# 24. Gate A UX Coverage Audit

Phase 2 provides learner-facing/system-visible states needed to demonstrate the frozen Gate A scenarios:

| Gate A scenario | UX coverage |
|---|---|
| Weak evidence → targeted adaptation | Results + signal + adaptation + focused Study |
| Supported evidence behaves differently | `SUPPORTED` signal + reduced repetition behaviour |
| Insufficient evidence | `DEVELOPING` / request-more-evidence UX |
| Evaluation failure | explicit no-evidence failure state |
| Contradictory evidence | mixed-results conservative state |
| Context isolation | persistent learning-context boundaries |
| Correction propagation | challenge + update pipeline |
| Retry/idempotency | stage-specific retry/uncertain-submission UX |
| Downstream AI failure | preservation/recovery states |
| Repeated adaptive cycle | targeted reassessment + cycle summary |
| Cross-user isolation | authorization-safe error state |

**Review result: PASS.**

---

# 25. Gate B UX Coverage Audit

The UX supports collection of directional user evidence by making the following observable:

- baseline assessment result;
- evidence/state shown;
- adaptation presented;
- adaptation rationale;
- whether learner accepts/skips adaptation;
- adapted Study interaction;
- targeted reassessment;
- new evidence/state;
- correction/challenge behaviour;
- complete cycle completion.

Phase 2 also identifies product events sufficient to support R0 validation without requiring a mature analytics product.

**Review result: PASS.**

---

# 26. Contradiction Review

The following potential contradictions were explicitly checked:

### Vision says broad assessment; R0 says MCQ

**Resolved:** Vision describes long-term learner-controlled assessment formats. R0 deliberately validates with MCQ.

### Vision says domain-independent; R0 uses DBMS

**Resolved:** domain independence is long-term direction; DBMS is the validation fixture.

### Vision contains Roadmap/Planner/Notes/Audio; R0 does not

**Resolved:** complete vision does not equal R0 scope.

### Learner control vs adaptation

**Resolved:** adaptation is inspectable and bounded; the learner may inspect rationale and continue normal Study.

### AI personalization vs conservative evidence

**Resolved:** strong state/adaptation requires evidence; uncertainty is a valid product outcome.

### Score vs state

**Resolved:** explicitly separate in semantics and wireframes.

### Failure vs evidence

**Resolved:** infrastructure/provider failures cannot become negative learner evidence.

**No blocking Phase 2 contradiction remains.**

---

# 27. Accidental Scope-Creep Review

Items that appeared during UX exploration but remain implementation details or deferred capabilities rather than new R0 product systems:

- source-detail panels;
- evidence drawers;
- cycle timeline;
- optional timer;
- compact account screen;
- lightweight product-validation events;
- recovery cards.

These support the frozen R0 loop and do not materially expand the product hypothesis.

**No blocking feature-scope creep remains.**

---

# 28. Phase 3 Architecture Inputs Frozen by UX

Phase 3 must support these product invariants:

1. **Learner ownership/isolation** for private resources, attempts, evidence and state.
2. **Persistent learning context** across repeated cycles.
3. **Resource lifecycle** with explicit processing states.
4. **Grounded Study** with source provenance/failure honesty.
5. **Assessment lifecycle** separate from evaluation lifecycle.
6. **Deterministic MCQ evaluation** for required R0 evidence.
7. **Structured concept-attributed evidence** with provenance.
8. **Conservative learner-state computation** from multiple evidence opportunities.
9. **Inspectable adaptation decision** separate from Study generation.
10. **Targeted reassessment** as a new evidence opportunity.
11. **Correction propagation** through dependent state.
12. **Idempotent consequential operations** and safe retries.
13. **Authoritative workflow recovery** after refresh/session/multi-tab conditions.
14. **Event/telemetry support** sufficient for Gate A/B validation.
15. **Responsive/accessibility-compatible APIs/states** — UI cannot depend on hidden synchronous assumptions.

These are architecture requirements inherited from the product/UX contract.

---

# 29. What Phase 3 Must Not Invent

Phase 3 must not silently add product scope by introducing architecture that requires:

- Planner;
- Roadmap;
- Notes;
- Audio;
- full Revision;
- universal domain ontology;
- universal assessment engine;
- multi-agent swarm architecture;
- coding execution environment;
- broad third-party integrations;
- complex real-time collaboration.

Architecture may remain extensible for future systems, but R0 should not pay their full implementation cost upfront.

---

# 30. Decisions Intentionally Left to Phase 3

Phase 2 does **not** freeze:

- frontend framework;
- backend framework;
- relational/document/vector storage choices;
- object/file storage;
- authentication provider;
- LLM/provider choice;
- embedding model;
- retrieval architecture;
- queue/job infrastructure;
- event bus/workflow engine;
- caching;
- deployment platform;
- observability vendor;
- API protocol/style;
- exact database schema;
- exact retry/backoff mechanism;
- exact state-machine implementation.

These are now ready to be decided against the frozen product contract.

---

# 31. Decisions Intentionally Left to Visual Design / Implementation

Phase 2 also does not freeze:

- brand colours;
- typography;
- icon family;
- spacing/radius tokens;
- final responsive breakpoints;
- animation;
- final microcopy polishing;
- final component library;
- illustration style.

Structural hierarchy and semantic behaviour are frozen; visual expression is not.

---

# 32. Phase 2 Document Set

The frozen Phase 2 specification consists of:

```text
docs/phase-2-product-ux/

01-r0-end-to-end-user-journey.md
02-r0-information-architecture-screen-inventory.md
03-r0-detailed-interaction-flows-state-transitions.md
04-study-experience-adaptation-ux.md
05-assessment-results-learner-state-ux.md
06-error-empty-loading-recovery-ux.md
07-r0-wireframe-specification.md
08-ux-consistency-review-phase-2-freeze.md
```

Together these documents define the R0 learner-facing product contract.

---

# 33. Phase 2 Freeze Rule

From this point forward:

> **Phase 2 is treated as frozen input to Phase 3.**

Changes are still allowed when implementation reveals a real contradiction, impossible requirement, usability defect or newly discovered constraint.

However, such changes should be explicit and traced back into the relevant Phase 2 document rather than silently changing the product during architecture/coding.

---

# 34. Phase 2 Exit Checklist

- [x] R0 hypothesis preserved
- [x] DBMS validation fixture preserved without permanent domain coupling
- [x] feature breadth constrained
- [x] complete two-cycle learner journey specified
- [x] MCQ assessment scope consistent
- [x] formal evidence boundary explicit
- [x] learner-state semantics consistent
- [x] score/state distinction explicit
- [x] evidence provenance inspectable
- [x] adaptation bounded and explainable
- [x] correction propagation specified
- [x] targeted reassessment independence specified
- [x] causal overclaiming avoided
- [x] grounding honesty specified
- [x] failure/retry/resume contract specified
- [x] responsive hierarchy specified
- [x] accessibility constraints specified
- [x] Gate A UX coverage complete
- [x] Gate B observability supported
- [x] no blocking contradiction remains
- [x] no blocking accidental scope creep remains
- [x] Phase 3 architecture inputs identified

---

# 35. Final Phase 2 Decision

## **PHASE 2 — PRODUCT & UX DESIGN: FROZEN ✅**

ARIA R0 now has a coherent learner-facing specification that is narrow enough to build, broad enough to test the actual adaptive-learning hypothesis, and explicit enough for architecture to be designed against concrete product invariants rather than imagined future requirements.

The product being handed to Phase 3 is not the entire ARIA vision.

It is the first validated slice:

```text
RESOURCE-GROUNDED STUDY
          ↓
FORMAL MCQ ASSESSMENT
          ↓
DETERMINISTIC EVALUATION
          ↓
STRUCTURED EVIDENCE
          ↓
BASIC LEARNER STATE
          ↓
EXPLAINABLE STUDY ADAPTATION
          ↓
TARGETED REASSESSMENT
          ↓
NEW EVIDENCE
          ↺
```

That is the system Phase 3 must now make technically real.

---

# 36. Next Phase

# Phase 3 — System Architecture

The first architecture step should define the **R0 system boundary and architecture principles** before choosing individual technologies.

Recommended Phase 3 sequence:

```text
1. System boundary + architecture principles
2. Domain model + ownership boundaries
3. Data model + persistence strategy
4. Service/module architecture
5. API contracts + state machines
6. AI/RAG architecture
7. Evidence + learner-state engine
8. Assessment/evaluation architecture
9. Adaptation engine
10. Async jobs/events/retries/idempotency
11. Security/privacy/authorization architecture
12. Observability + Gate A test architecture
13. Deployment topology + technology decisions
14. Architecture review + Phase 3 freeze
```

**Step 8: COMPLETE.**