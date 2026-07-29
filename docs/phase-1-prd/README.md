# ARIA — Phase 1: Product Requirements Document

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document (PRD)  
**Status:** Consistency audit complete — R0 decisions pending before freeze  
**Source of truth:** [`VISION.md`](../../VISION.md)

---

## Purpose

Phase 0 established what ARIA is and why it should exist. Phase 1 translates that vision into explicit, testable product requirements before user flows, wireframes, architecture, database design, API design, or implementation begin.

The reviewed Phase 0 vision introduced three corrections that every Phase 1 document must preserve:

1. **Domain breadth:** ARIA's long-term model is domain-independent, while early validation uses a constrained representative context.
2. **Feature breadth:** the complete Learning OS is not R0 scope; R0 is the smallest loop that tests adaptive learning.
3. **Validation breadth:** R0 uses rigorous Gate A engineering validation plus small-scale Gate B directional real-user evidence, without causal overclaiming.

---

## Phase 1 Documents

| Document | Purpose | Review status |
|---|---|---|
| `01-product-overview-goals.md` | Product context, goals, audience, R0 hypothesis and boundaries | ✓ Audited |
| `02-user-context-requirements.md` | Learner identity, goals, contexts, onboarding and continuity | ✓ Audited |
| `03-functional-requirements.md` | Full-vision functional requirements with release classification | ✓ Audited |
| `04-cross-system-requirements.md` | R0 adaptive chain plus later orchestration requirements | ✓ Audited |
| `05-ai-learner-model-memory-evidence.md` | AI behaviour, evidence, basic learner state and later intelligence | ✓ Audited |
| `06-non-functional-privacy-security-reliability-accessibility.md` | R0 safety/readiness vs public-production requirements | ✓ Audited |
| `07-scope-prioritization-release-boundaries.md` | Hypothesis-driven release boundaries | ✓ Audited |
| `08-acceptance-criteria-success-metrics-prd-closure.md` | R0 Gate A/Gate B acceptance and later-release direction | ✓ Audited |
| `PRD.md` | Final consolidated source of truth | ○ Freeze pending R0 decisions |

---

## Requirement ID Convention

Requirement identifiers remain useful for traceability even when a requirement belongs to a later release rather than R0.

```text
FR-*            Functional requirements
UR-*            User/context requirements
XR-*            Cross-system requirements
AI-*            AI/intelligence requirements
NFR-*           Non-functional requirements
AC-R0-*         R0 acceptance criteria
```

A requirement existing in Phase 1 does **not** automatically mean it is an R0 implementation requirement. Its release label controls scope.

---

## Canonical R0 Definition

All eight documents now converge on the same first hypothesis:

> **Can ARIA observe meaningful learning evidence, update a basic learner state, and use that state to appropriately change the learner's next study experience?**

Canonical R0 loop:

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

The **second cycle is part of R0**. A one-shot Study → Assessment demo does not prove adaptive learning.

---

## Canonical Release Direction

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

### R0
One validation context; small supported resource/assessment surface; Study → Assessment → Evaluation → Evidence → Basic Learner State → Adapted Study → reassessment.

### R1
Roadmap / structured learning-path adaptation.

### R2
Longitudinal evidence, richer learner model, Revision/Progress, conservative misconception reasoning and memory v1.

### R3
Planner, deadlines, reminders, availability and multi-goal coordination.

### R4
Notes, Audio and richer learning interfaces/resources.

### R5
Mature cross-system orchestration, integrations and justified agentic workflows.

Candidate capabilities may move when later hypotheses are refined, but R0 remains protected by its elimination test.

---

## R0 Explicit Non-Goals

Unless a selected validation context makes one strictly necessary, R0 is not blocked by:

- Notes;
- Audio;
- Planner;
- reminders/notifications;
- full Roadmap generation or adaptation;
- sophisticated Progress dashboards;
- mature Revision/spaced repetition;
- full misconception detection;
- universal prerequisite graphs;
- external learning-platform tracking;
- production coding sandbox infrastructure;
- advanced multi-agent orchestration;
- every resource type;
- every assessment type;
- multiple simultaneous goals;
- broad domain generalization;
- internet-scale/distributed infrastructure;
- public-production operational maturity.

These are deferred, not deleted from ARIA's vision.

---

## Domain & Audience Rule

Initial audience:

> **College students, recent graduates, and early-career learners working toward concrete learning or preparation goals.**

Long-term ARIA remains goal-driven and domain-extensible.

R0 does **not** prove the universal case. The intended sequence is:

```text
specific context
      ↓
validate
      ↓
second structurally different context
      ↓
find broken assumptions
      ↓
generalize only what evidence justifies
```

Core architecture/product models should avoid unnecessary hardcoded domain branches, but R0 may contain implementation details specific to its chosen validation case where those details do not unnecessarily prevent later generalization.

---

## Assessment Rule

ARIA's complete product does not impose one universal exam format.

For R0:

- support only the assessment format(s) needed to generate reliable evidence in the selected validation context;
- allow learner configuration within what R0 actually supports where useful;
- do not build every planned assessment modality merely to preserve the long-term vision;
- use deterministic evaluation when deterministic scoring is appropriate;
- bound and validate AI evaluation when used.

---

## Evidence / Learner-State Rule

Across the PRD:

```text
Observation / evaluated performance
          ↓
Structured Evidence
          ↓
Conservative Basic Learner State
          ↓
Confidence-aware Adaptation
```

R0 must preserve these distinctions:

- one wrong answer ≠ confirmed misconception;
- one correct answer ≠ mastery;
- no evidence ≠ weakness;
- evaluation failure ≠ negative learner evidence;
- contradictory evidence ≠ silent high confidence;
- conversational memory ≠ learning evidence;
- correction must be able to propagate into dependent state/adaptation.

---

## Automation Rule

R0 requires a bounded adaptive workflow, not a multi-agent platform.

The implementation may use deterministic services, normal application code, model calls, explicit workflow state or another simple architecture capable of satisfying the requirements.

Every subsystem does not need to become an AI agent.

Agentic/tool orchestration is introduced only when it provides justified product value and retains validation, authorization, idempotency, failure isolation and human-control boundaries.

---

## R0 Non-Functional Bar

The Step 6 audit separates:

```text
safe/correct R0
      ↓
small-scale validation deployment
      ↓
public production readiness
      ↓
future scale
```

R0 **does require**:

- secure identity/authentication appropriate to deployment;
- server/trusted-boundary authorization;
- cross-user data isolation;
- private learner resources/state;
- secrets hygiene;
- prompt-injection boundaries;
- evidence integrity;
- retry/idempotency safety;
- correction consistency;
- explicit failure states;
- traceability of the adaptive loop;
- baseline accessibility;
- bounded resource/model usage.

R0 does **not require** public uptime SLAs, distributed architecture, mature production backup operations, every browser/device, Audio/notification controls for features not in R0, or scale infrastructure for hypothetical traffic.

---

## Validation Standard

### Gate A — Engineering Validation

Mandatory, rigorous and reproducible.

It proves that the machinery correctly closes the loop under controlled scenarios, including weak/supported/insufficient/contradictory evidence, evaluation failure, context isolation, correction, retry/idempotency and a repeated adaptive cycle.

### Gate B — Real-User Signal

Small-scale directional evidence from available target learners.

Gate B may report before/after observations, adaptation relevance, confusion, corrections and qualitative feedback. It does **not** claim statistical significance or causal educational improvement without the study design/evidence needed for such a claim.

Defensible project statement:

> **The adaptive pipeline was rigorously validated through controlled engineering scenarios. Small-scale real-user testing then provided directional before/after evidence and qualitative feedback, without claiming statistically established causal improvement.**

---

## Final Consistency Audit — Results

The Phase 1 documents were rechecked after the Step 1–6 realignment.

### Resolved

✓ Universal-domain support is no longer an R0 requirement.  
✓ Full-vision feature breadth is no longer treated as R0.  
✓ R0 is consistently defined around adaptive Study rather than a foundation-only shell.  
✓ Notes/Audio/Planner/Roadmap orchestration/full misconception detection are explicitly later.  
✓ Multiple simultaneous goals are no longer required for R0.  
✓ Gate A and Gate B have distinct standards.  
✓ The second adaptive cycle is part of validation.  
✓ Evidence, memory and learner state are separated.  
✓ AI failure cannot become false learner evidence.  
✓ Retry/idempotency and correction propagation are required.  
✓ Step 6 now distinguishes R0 engineering safety from public-production maturity.  
✓ Accessibility begins in R0 rather than being deferred as polish.  
✓ Premature scale/agent architecture is not required.

### No blocking contradiction found

The audited Step 1–8 documents now describe the same R0 product thesis and release direction.

---

## Remaining R0 Decisions Before PRD Freeze

The audit intentionally does **not** invent these choices. They are product/validation decisions that must now be made explicitly:

1. **Validation context** — the concrete first learning context for Gate A and Gate B.
2. **Resource surface** — e.g. PDF, pasted text, or both for R0.
3. **Assessment surface** — exact format(s) supported in R0.
4. **Basic learner-state representation** — exact conservative state model/fields.
5. **Allowed adaptation actions** — exactly how R0 may change the next Study experience.
6. **Evidence/adaptation policy** — what evidence is enough for each state/adaptation transition.
7. **Critical Gate A failure definition** — which failures block R0 completion.
8. **Gate B practical scope** — realistic number of target users/sessions and reporting method.

These are not scope-expansion questions. Resolving them turns the now-consistent PRD into an executable specification.

---

## Phase Completion Definition

Phase 1 is complete/frozen when:

- Steps 1–8 remain internally consistent;
- the eight R0 decisions above are resolved;
- acceptance criteria are updated with those concrete decisions where needed;
- requirement traceability is checked once more;
- canonical `PRD.md` is produced;
- no unresolved question blocks Phase 2 product-flow/design work.

---

## Current Progress

```text
Phase 0 — Product Vision                         ✓ COMPLETE & REVIEWED

Phase 1 — Product Requirements Document         FINALIZATION
├── 01 Product Overview                         ✓ AUDITED
├── 02 User & Learning Context                  ✓ AUDITED
├── 03 Functional Requirements                  ✓ AUDITED
├── 04 Cross-System Requirements                ✓ AUDITED
├── 05 AI / Learner Model / Evidence            ✓ AUDITED
├── 06 Non-Functional Requirements              ✓ AUDITED
├── 07 Scope / Release Boundaries               ✓ AUDITED
├── 08 Acceptance / Success / Validation        ✓ AUDITED
├── Final consistency audit                     ✓ COMPLETE
└── Canonical PRD.md                             ○ WAITING ON R0 DECISIONS
```

---

## Next

**Resolve the eight concrete R0 decisions.**

Once they are decided, update the affected requirements/acceptance criteria, run the final traceability check, consolidate the documents into canonical `PRD.md`, and freeze Phase 1.

Only then should ARIA move into the next product-design/architecture phase.