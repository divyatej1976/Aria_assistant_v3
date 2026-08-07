# ARIA — Phase 2: Product & UX Design

## Step 2 — R0 Screen Inventory & Information Architecture

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 2 — Product & UX Design  
**Status:** Step 2 complete  
**Inputs:** Phase 1 frozen PRD + Phase 2 Step 1 canonical user journey

---

# 1. Purpose

Step 1 defined the learner's end-to-end R0 journey. Step 2 turns that journey into a concrete product surface.

The goal is not to create one page for every backend object. The goal is to identify the smallest coherent set of learner-facing screens/views needed to complete the adaptive loop safely and understandably.

R0 must feel like one learning workspace, not a collection of disconnected mini-apps.

---

# 2. Information-Architecture Principle

ARIA's R0 information architecture is centered on the learner's **active learning context**.

```text
ARIA
│
├── Public
│   ├── Landing
│   ├── Sign Up
│   └── Sign In
│
└── Authenticated App
    │
    ├── Home / Current Learning
    │
    ├── Learning Workspace
    │   ├── Overview
    │   ├── Resources
    │   ├── Study
    │   ├── Assessment
    │   ├── Results / Evidence
    │   └── Adapted Study / Reassessment
    │
    └── Account
```

Several entries above are **views/states inside a workspace**, not necessarily separate routes.

This prevents R0 from becoming a navigation-heavy dashboard before the core loop has even been validated.

---

# 3. Top-Level Navigation

Recommended authenticated R0 navigation:

```text
ARIA
├── Home
├── Study
├── Assess
└── Account
```

However, `Study` and `Assess` always operate inside the active learning context.

Resources and learner evidence should remain contextually available rather than becoming major independent product destinations.

## Why no Planner / Notes / Roadmap / Progress tabs?

They are later-release capabilities and adding empty or fake navigation for them would misrepresent R0 and encourage scope creep.

---

# 4. Screen Inventory

R0 requires the following core screens/views.

| ID | Screen / View | Primary purpose |
|---|---|---|
| S01 | Landing | Explain ARIA R0 value and enter authentication |
| S02 | Sign Up | Create learner identity |
| S03 | Sign In | Authenticate returning learner |
| S04 | First-Time Setup | Establish validation learning context |
| S05 | Home / Current Learning | Resume the correct next step |
| S06 | Learning Context / Workspace Overview | Orient learner within DBMS context |
| S07 | Resources | Upload PDF / add pasted text and inspect processing state |
| S08 | Study | Baseline or normal learning interaction |
| S09 | Assessment Setup | Configure supported MCQ assessment |
| S10 | Assessment | Answer MCQs and submit attempt |
| S11 | Results & Evidence | Review performance and current evidence/state |
| S12 | Adaptation Explanation | Explain what ARIA observed and what changes next |
| S13 | Adapted Study | Deliver evidence-driven focused learning |
| S14 | Targeted Reassessment | Gather new independent evidence |
| S15 | Cycle Summary | Show before/after evidence/state movement and next action |
| S16 | Review / Correction | Inspect or challenge evaluation/evidence |
| S17 | Account | Basic account/session controls |

These are logical screens. Some may later be combined into routes, drawers, panels or modal states during wireframing.

---

# 5. S01 — Landing

## Purpose

Explain the R0 product clearly without advertising the entire future Learning OS as already available.

## Required content

- ARIA identity/product name;
- concise adaptive-learning value proposition;
- explanation of the simple loop: Learn → Test → Adapt → Check again;
- Get Started CTA;
- Sign In CTA;
- lightweight privacy/trust indication where appropriate.

## Primary action

`Get Started`

## Secondary action

`Sign In`

## Do not include

- fake Planner previews;
- Notes/Audio promises presented as current functionality;
- giant feature grids for R1–R5;
- unsupported universal-domain claims.

---

# 6. S02 — Sign Up

## Purpose

Create a persistent learner identity.

## Required elements

- authentication fields/mechanism appropriate to implementation;
- validation;
- terms/privacy acknowledgement where required;
- submit;
- link to Sign In.

## States

- default;
- validating;
- submitting;
- duplicate/existing identity;
- invalid input;
- provider/network failure;
- success.

Successful signup routes to First-Time Setup.

---

# 7. S03 — Sign In

## Purpose

Authenticate a returning learner and restore their learning workflow.

## Required elements

- credentials/auth mechanism;
- submit;
- link to Sign Up;
- recovery mechanism if supported by chosen auth solution.

## States

- default;
- submitting;
- invalid credentials;
- expired/revoked session;
- provider/network failure;
- success.

Successful sign-in routes to Home, which determines the learner's correct resume point.

---

# 8. S04 — First-Time Setup

## Purpose

Create the R0 learning context with minimal friction.

Because the validation context is frozen, R0 may directly introduce:

```text
DBMS
Transactions, Concurrency Control,
Schedules & Serializability
```

## Required elements

- concise explanation of the validation learning context;
- confirmation/start action;
- optional minimal learner goal wording if useful.

## Important constraint

Do not build a fake universal goal-creation system merely to make R0 appear broader than it is.

The underlying model should remain extensible even though the R0 UI is constrained.

---

# 9. S05 — Home / Current Learning

## Purpose

Answer one question immediately:

> **What should I do next?**

This is a resume/orchestration surface, not a future analytics dashboard.

## Required content

### Active context card

- DBMS context;
- current focus/topic where known;
- resource readiness;
- current cycle status.

### Primary next-action card

Examples:

- Add learning material;
- Continue Study;
- Continue Assessment;
- View Results;
- Start focused review;
- Retry failed evaluation;
- Take targeted reassessment;
- Review completed cycle.

### Lightweight recent status

Only enough information to orient the learner.

## Do not include

- calendar;
- streak system unless later justified;
- roadmap timeline;
- large progress analytics suite;
- task manager;
- notification center.

---

# 10. S06 — Learning Workspace Overview

## Purpose

Provide context-level orientation without forcing the learner back to Home.

## Required content

- context title;
- current focus;
- resource summary;
- current learner-cycle stage;
- next recommended action;
- compact concept/evidence summary when evidence exists.

Possible structure:

```text
DBMS
Transactions & Concurrency

Material
1 PDF · Ready

Current learning signal
Serializability — Still building confidence

Next
Continue focused review
```

This screen may later merge with Home if wireframing shows that both are redundant in R0.

---

# 11. S07 — Resources

## Purpose

Add and manage the material ARIA is allowed to use for the active context.

## Required actions

- Upload PDF;
- Paste text;
- inspect resource status;
- retry failed processing;
- remove/replace resource where safe.

## Resource item states

```text
UPLOADING
PROCESSING
READY
FAILED
UNSUPPORTED
```

## Resource item information

- filename/title or pasted-text label;
- type;
- status;
- failure reason/action where appropriate;
- remove/replace action.

## Empty state

> Add a PDF or paste your study material to begin.

Primary CTA: `Add material`

---

# 12. S08 — Study

## Purpose

Provide the primary learning interaction.

## Core layout zones

### Context header

- active context/topic;
- selected resource grounding indicator;
- whether this is normal Study or focused/adapted Study.

### Learning conversation/content

- learner questions;
- ARIA explanations;
- examples;
- resource-grounded responses where expected.

### Input/action area

- ask/follow-up input;
- optional suggested actions;
- `Test me` CTA when appropriate.

### Lightweight source indication

Where a response relies on uploaded material, the UX should make that relationship understandable without overwhelming the learner.

## Important distinction

Study is not Notes, Planner, Roadmap or Progress. Do not quietly embed those future systems here.

---

# 13. S09 — Assessment Setup

## Purpose

Let the learner define a supported R0 MCQ assessment.

## Required controls

- topic/concept scope;
- question count within supported limits;
- difficulty;
- optional timer;
- generate/start action.

## Optional contextual information

- source material being used;
- whether this is baseline assessment or targeted reassessment.

## States

- default;
- invalid configuration;
- generating;
- bounded repair/retry;
- generation failed;
- ready.

---

# 14. S10 — Assessment

## Purpose

Allow focused completion of generated MCQs.

## Required layout

### Header

- topic;
- question progress;
- timer if enabled.

### Question area

- question;
- answer options;
- clear selected state.

### Navigation

- previous/next if supported;
- question indicator;
- submit.

## Required states

- unanswered;
- answered;
- submission confirmation;
- submitting;
- submission persisted;
- network failure/retry.

## Accessibility

Answer controls and navigation must be keyboard-operable and have visible focus/selection states.

---

# 15. S11 — Results & Evidence

## Purpose

Translate evaluation into understandable learner feedback without overclaiming.

## Required sections

### Assessment result

- score/result;
- question-level review access;
- correct/incorrect status.

### Concept signal

Use learner-facing language such as:

- Not enough evidence yet;
- Still building confidence;
- Worth reviewing;
- Current results look solid.

### Evidence explanation

Explain why the signal exists.

Example:

> You missed two different questions involving conflict-serializable schedules.

### Next action

- gather more evidence;
- begin focused review;
- continue normal Study;
- targeted reassessment when appropriate.

## Required actions

- `Review answers`;
- `Why this result?`;
- `This result looks wrong` where applicable;
- primary next-step CTA.

---

# 16. S12 — Adaptation Explanation

## Purpose

Make ARIA's adaptive behaviour visible before consequential Study changes.

This can be a dedicated screen, result-panel section or transition view. The information itself is mandatory even if the final route is combined with S11.

## Required structure

```text
WHAT I OBSERVED

CURRENT SIGNAL

WHAT I'M CHANGING

WHY THIS SHOULD HELP / WHAT HAPPENS NEXT
```

Example:

> **What I observed**  
> Two separate questions showed difficulty identifying conflicts in schedules.
>
> **Current signal**  
> This concept is worth reviewing.
>
> **What I'm changing**  
> We'll work through a schedule step by step before another targeted check.

Primary CTA: `Start focused review`

Secondary: `Review evidence`

---

# 17. S13 — Adapted Study

## Purpose

Deliver a materially different Study experience based on evidence.

## Required visible context

- focused concept;
- reason for focus;
- adaptation type where useful;
- path to targeted reassessment.

Example header:

```text
Focused review
Conflict Serializability

Why: Your latest assessment showed repeated difficulty here.
```

## Supported content adaptations

- simpler explanation;
- alternate framing;
- worked example;
- prerequisite recap;
- increased/decreased scaffolding;
- targeted practice;
- diagnostic check.

The learner should be able to distinguish this experience from the baseline Study experience.

---

# 18. S14 — Targeted Reassessment

## Purpose

Collect new evidence after adaptation.

The UI largely reuses S10's assessment interaction but must clearly indicate that this is a targeted check.

Example:

```text
Quick check
Conflict Serializability

Let's see how this concept looks after the review.
```

Questions should be independent enough to provide meaningful new evidence rather than simply repeat a revealed answer.

---

# 19. S15 — Cycle Summary

## Purpose

Close the adaptive loop and show the learner what happened across cycles.

## Required content

- concept;
- previous signal;
- new signal;
- activity/adaptation completed;
- reassessment outcome;
- next supported action.

Example:

```text
Cycle complete

Conflict Serializability
Before: Worth reviewing
Now: Current results look stronger

You:
✓ reviewed a worked schedule
✓ practiced conflict detection
✓ completed a targeted reassessment

[Continue studying]
[Review details]
```

Do not claim that ARIA scientifically caused improvement.

---

# 20. S16 — Review / Correction

## Purpose

Allow the learner to inspect the basis for consequential evidence/state and challenge mistakes.

## Required content

- assessment question;
- learner answer;
- correct answer;
- evaluation result;
- concept attribution;
- relevant explanation;
- current effect on evidence/state where understandable.

## Required actions

- `This evaluation looks wrong`;
- return to Results;
- optional request for more evidence where appropriate.

## Correction states

```text
CHALLENGE_SUBMITTED
UNDER_REVIEW / RECHECKING
CORRECTED
UNCHANGED
RECOMPUTING_STATE
STATE_UPDATED
```

The exact technical correction mechanism is deferred to architecture, but the UX contract is established here.

---

# 21. S17 — Account

## Purpose

Provide basic learner/account controls without becoming a settings platform.

R0 may include:

- account identity information;
- sign out;
- basic privacy/data action entry points required by implementation/validation;
- validation-data reset/delete action if exposed to the learner.

Later-release notification/audio/planner preferences do not belong here yet.

---

# 22. Global App Shell

Authenticated R0 screens should share a consistent shell.

Conceptual desktop layout:

```text
┌──────────────────────────────────────────────────────────┐
│ ARIA                                      Account/Profile │
├──────────────┬───────────────────────────────────────────┤
│ Home         │                                           │
│ Study        │              Main content                 │
│ Assess       │                                           │
│              │                                           │
│              │                                           │
└──────────────┴───────────────────────────────────────────┘
```

On smaller screens, navigation can collapse appropriately.

The shell should always preserve enough context for the learner to know what they are studying.

---

# 23. Context Header

Inside the learning workspace, a reusable context header should communicate:

- learning context: DBMS;
- current concept/focus;
- cycle stage when useful;
- resource grounding status;
- relevant next action.

Example:

```text
DBMS / Serializability
Material: Ready
Current stage: Focused review
```

This reduces orientation loss when moving between Study, Assessment and Results.

---

# 24. Global System States

Every applicable screen must account for:

```text
LOADING
EMPTY
READY
SAVING
PROCESSING
SUCCESS
FAILED_RETRYABLE
FAILED_BLOCKING
UNAUTHORIZED
SESSION_EXPIRED
OFFLINE / NETWORK_ERROR
```

Screens should not use indefinite spinners for failures that require learner action.

---

# 25. Resume Logic

Home should route the learner toward the most relevant unfinished state.

Conceptual priority:

```text
Security/session problem
        ↓
Failed consequential stage requiring action
        ↓
Unsubmitted active assessment
        ↓
Submitted attempt awaiting/requiring evaluation
        ↓
Adaptation ready
        ↓
Targeted reassessment ready
        ↓
Resource required
        ↓
Normal Study
```

This ordering is a UX concept and will be refined during detailed flows/architecture.

---

# 26. Route vs View Decision

Not every logical screen needs its own URL.

Likely dedicated routes:

```text
/
/signup
/signin
/app
/app/study
/app/assess
/app/assessment/:id
/app/results/:attemptId
/app/account
```

Possible embedded views/panels:

- Resource management;
- Adaptation Explanation;
- Cycle Summary;
- Review/Correction;
- workspace overview.

These paths are illustrative UX structure, **not a frozen frontend routing implementation**.

---

# 27. Information Hierarchy

Across R0, prioritize information in this order:

```text
1. What am I doing now?
2. What should I do next?
3. What did ARIA observe?
4. Why is ARIA changing something?
5. What evidence supports that?
6. How can I inspect/correct it?
7. Historical/system detail
```

This keeps evidence transparency available without forcing every learner to inspect internals constantly.

---

# 28. Learner-State Presentation Rules

Never present the internal state as an unquestionable identity label.

Avoid:

```text
YOU ARE WEAK
MASTERED
BAD AT SERIALIZABILITY
```

Prefer:

```text
Worth reviewing
Current results look solid
Still building confidence
Not enough evidence yet
```

When possible, pair the signal with its evidence basis.

---

# 29. Adaptation Visibility Rules

Whenever ARIA makes a meaningful evidence-driven Study adaptation, the interface must make available:

- the concept affected;
- the evidence/signal behind it;
- the type of change;
- the next expected action;
- a way to inspect/challenge the basis.

Adaptation must not feel like random content variation.

---

# 30. Error Ownership

Errors should appear where the learner can act on them.

Examples:

| Failure | Owning screen |
|---|---|
| PDF processing failed | Resources |
| Assessment generation failed | Assessment Setup |
| Assessment submit/network issue | Assessment |
| Evaluation failed | Results/pending evaluation state |
| Adapted content generation failed | Adaptation/Adapted Study |
| Session expired | Global auth boundary |
| Evaluation challenged | Review/Correction |

Do not dump unrelated backend errors onto Home as generic alerts.

---

# 31. Empty States

R0 needs intentional empty states.

## No resource

> Add study material to start learning with ARIA.

## No assessment yet

> Study a concept, then test your understanding when you're ready.

## No evidence

> No learning signal yet. Complete an assessment to give ARIA evidence to work with.

## No adaptation

> ARIA will adapt Study when the evidence supports a useful change.

Empty states must not manufacture progress/evidence that does not exist.

---

# 32. Responsive Design Expectations

R0 should be usable on desktop and common mobile widths even if desktop is the primary build target.

On smaller screens:

- sidebar becomes compact navigation/drawer;
- assessment options remain comfortably tappable;
- results/evidence cards stack vertically;
- adaptation explanations preserve reading order;
- no essential action exists only on hover;
- long Study conversations remain readable.

---

# 33. Accessibility Baseline

Screen design must support the Step 6 baseline:

- keyboard navigation;
- visible focus;
- semantic labels;
- sufficient contrast;
- errors not conveyed by colour alone;
- accessible form validation;
- logical heading order;
- adequate target sizes;
- screen-reader-compatible status changes where practical;
- timer design that does not make assessment inaccessible.

Accessibility is part of R0 design, not post-validation decoration.

---

# 34. Screen Reuse Opportunities

To keep R0 buildable:

- S10 Assessment and S14 Targeted Reassessment should share the same assessment shell;
- S08 Study and S13 Adapted Study should share the same core Study shell with adaptation context;
- S11 Results and S15 Cycle Summary may reuse evidence/result cards;
- S12 Adaptation Explanation may live inside Results and/or as a transition panel;
- S16 Review/Correction can be a drawer/detail route rather than an entire parallel subsystem.

This preserves UX clarity while minimizing unnecessary frontend surface area.

---

# 35. Minimum Route-Level Product Surface

After reuse, R0 can plausibly be implemented with a compact route-level surface:

```text
Public
├── Landing
├── Sign Up
└── Sign In

App
├── Home / Workspace
├── Study
├── Assessment Setup
├── Assessment Session
├── Results
└── Account
```

Resources, adaptation, reassessment, correction and cycle summary can be expressed as contextual states/views within these surfaces.

This is intentionally much smaller than the 17 logical UX screens.

---

# 36. Scope Guardrail

A screen should enter R0 only if removing it or its function prevents one of these:

- learner identity/context;
- resource grounding;
- baseline Study;
- assessment/evaluation;
- evidence understanding;
- learner-state transparency;
- adaptation;
- correction/control;
- reassessment;
- safe recovery/resume.

If a proposed screen exists primarily for Planner, Notes, Roadmap, Audio, advanced Progress, social features, gamification or other future capabilities, it is not an R0 screen.

---

# 37. Step 1 → Step 2 Traceability

| Step 1 journey stage | Step 2 surface |
|---|---|
| Landing | S01 |
| Sign up / sign in | S02 / S03 |
| First-time setup | S04 |
| Resume workflow | S05 |
| Learning context | S05 / S06 |
| Add PDF/text | S07 |
| Baseline Study | S08 |
| Configure MCQ | S09 |
| Assessment | S10 |
| Evaluation/result | S11 |
| learner_concept_state | S11 |
| Adaptation explanation | S12 |
| Adapted Study | S13 |
| Targeted reassessment | S14 |
| State reconsideration | S11 / S15 |
| Cycle summary | S15 |
| Challenge/correction | S16 |
| Returning learner | S05 resume logic |
| Failure/retry | owning screen + global states |

Every Step 1 journey stage now has an owning R0 product surface.

---

# 38. Step 2 Completion Checklist

- [x] top-level information architecture defined;
- [x] authenticated navigation bounded;
- [x] logical screen inventory defined;
- [x] minimum route-level surface identified;
- [x] each screen has a clear purpose;
- [x] major states identified;
- [x] learner-state presentation rules defined;
- [x] adaptation transparency surface defined;
- [x] correction surface defined;
- [x] failure ownership defined;
- [x] resume logic defined conceptually;
- [x] responsive expectations defined;
- [x] accessibility baseline carried forward;
- [x] future-release navigation excluded;
- [x] Step 1 journey fully mapped to Step 2 surfaces.

---

# 39. Step 2 Completion

**Phase 2 — Step 2 is complete.**

ARIA R0 now has a bounded information architecture and screen inventory. The next task is not to add more screens—it is to define exactly how learners move through these surfaces under happy-path and non-happy-path conditions.

Next:

# Step 3 — Detailed User Flows & State Transitions

Step 3 will specify the actual transitions for first-time setup, resource ingestion, Study → assessment, evaluation, evidence/state update, adaptation, reassessment, correction, retry, returning-user resume and critical failure paths.
---

## Next

Step 3 — Detailed User Flows & State Transitions.
