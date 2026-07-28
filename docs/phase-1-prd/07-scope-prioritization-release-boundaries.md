# ARIA — Phase 1 PRD

## Step 7 — Scope, Prioritization & Release Boundaries

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Step 7 — Complete  
**Primary sources:** `VISION.md`, Steps 1–6 of the Phase 1 PRD

---

# 1. Purpose

ARIA's full product vision is intentionally broad: a learner can define what they are preparing for, bring their own resources, study with AI, generate assessments in the format they need, receive evidence-backed feedback, revise weak areas, follow an adaptive roadmap and planner, listen to learning material, and eventually connect activity from external learning platforms.

Trying to implement all of this simultaneously would increase technical risk and make it difficult to determine whether the core learning loop actually works.

This document therefore defines **build order**, not a smaller vision.

The central principle is:

> **Do not build ARIA feature-by-feature. Build it as increasingly complete learning loops.**

---

# 2. Prioritization Principles

ARIA shall prioritize work according to the following order:

1. **Foundations before automation.**
2. **A complete learning loop before feature breadth.**
3. **Source-grounded learning before broad autonomous behaviour.**
4. **Evidence before sophisticated adaptation.**
5. **Learner control before autonomous restructuring.**
6. **Reliable deterministic workflows before unnecessary agents.**
7. **One coherent product surface before many integrations.**
8. **Measurable learner value before architectural complexity.**
9. **Graceful simple behaviour before advanced intelligence.**
10. **The full vision remains documented even when features ship later.**

---

# 3. Prioritization Vocabulary

This PRD uses four priority groups.

## MUST

Required for the first coherent usable ARIA learning loop or required foundation/security.

## SHOULD

Important to ARIA's differentiated experience and intended shortly after the first usable slice.

## COULD

Valuable capability that may follow once core loops are stable.

## LATER

Part of the product vision but intentionally deferred because it introduces substantial complexity, dependency risk, cost, or validation burden.

Priority does not mean importance to the final vision. `LATER` means **not yet**, not **never**.

---

# 4. Release Model

ARIA should evolve through coherent capability releases.

```text
R0 — Foundation
        ↓
R1 — First Learning Loop
        ↓
R2 — Evidence & Personalization
        ↓
R3 — Adaptive Learning System
        ↓
R4 — Audio & Mobile Learning
        ↓
R5 — External Activity & Integrations
        ↓
R6 — Advanced ARIA
```

These labels define dependency/order. They do not prescribe calendar dates.

---

# 5. R0 — Foundation

## Goal

Create the secure product skeleton required for every later ARIA capability.

## MUST

### Identity

- sign up;
- sign in;
- sign out;
- secure session handling;
- account ownership boundaries.

### User profile

- basic learner profile;
- timezone;
- relevant preferences;
- onboarding state.

### Goal model

Users can create learning goals such as:

```text
GATE preparation
University DBMS exam
Placement preparation
AWS certification
Python learning
Any other learner-defined preparation goal
```

Goals are **not hardcoded categories**.

### Context model

ARIA can associate relevant activity with:

```text
user
    ↓
goal
    ↓
topic / resource / activity
```

### Core data model

Foundation for:

- goals;
- resources;
- chats/study sessions;
- notes;
- assessments;
- attempts;
- evidence;
- learner state;
- roadmap;
- planner;
- revision;
- notifications.

Not every table/model must be fully feature-complete in R0, but architecture must avoid painting later requirements into a corner.

### Security baseline

Step 6 security requirements needed for development and testing must begin here rather than being postponed to launch.

## R0 Exit Condition

A learner can securely create an account, establish their learning context, create/manage a goal, and enter the application shell with data correctly isolated by account.

---

# 6. R1 — First Learning Loop

## Goal

Prove ARIA's fundamental promise:

> **Bring what you need to learn → study it → test yourself → understand what to do next.**

This is the first genuinely usable ARIA release.

## MUST

### Goal-aware Home

Home reflects the learner's actual goals rather than hardcoded DSA/AWS/etc. sections.

### Resource ingestion

Support an intentionally small initial set of reliable resource formats.

Initial candidates:

- PDF;
- pasted text;
- manually created notes.

Additional formats can follow after ingestion quality is proven.

### Resource processing

- extract usable text;
- retain source identity;
- chunk/index where required;
- expose processing state/failure;
- preserve access to source.

### Source-grounded Study Chat

The learner can ask questions about selected resources/context.

ARIA should:

- retrieve relevant material;
- explain concepts;
- answer questions;
- distinguish grounded information from unsupported assumptions where relevant;
- avoid pretending unavailable material was found.

### Notes

The learner can create/save useful notes generated manually or from study interactions.

### Assessment Builder

The learner chooses the assessment specification.

ARIA shall not assume every learner wants MCQs.

Supported specification concepts should include, as feasible for R1:

```text
topic/source
question count
question type
marks / scoring expectations
difficulty
time limit
```

Initial supported formats should prioritize formats ARIA can generate and evaluate reliably.

Suggested first formats:

- MCQ;
- short answer;
- descriptive answer with bounded rubric/feedback.

Coding-contest execution may ship later unless infrastructure is deliberately included.

### Assessment attempt

- exam card/specification;
- start assessment;
- answer questions;
- timer when selected;
- submit;
- preserve attempt.

### Evaluation

- objective scoring where deterministic;
- bounded AI evaluation where needed;
- feedback;
- source/topic association;
- validation before consequential downstream use.

### Basic evidence

Assessment results create structured learning evidence.

### Basic next-action recommendation

ARIA uses the latest activity/context to suggest a reasonable next learning action without pretending a mature Learner Model exists yet.

## R1 Explicit Non-Goals

Do not block R1 on:

- full multi-agent orchestration;
- sophisticated misconception graphs;
- automatic roadmap restructuring;
- external platform tracking;
- production-grade coding sandbox;
- advanced spaced-repetition engine;
- full audio studio;
- every possible file format;
- social/community features;
- video course hosting;
- language-learning specialization.

## R1 Exit Condition

A real learner can complete this loop end-to-end:

```text
Create goal
   ↓
Add study material
   ↓
Study with ARIA
   ↓
Generate a learner-configured assessment
   ↓
Take assessment
   ↓
Receive evaluation
   ↓
Store evidence
   ↓
Receive a grounded next action
```

---

# 7. R2 — Evidence & Personalization

## Goal

Turn ARIA from a resource-aware AI tutor into a system that starts learning from the learner's performance.

## SHOULD

### Learner Model v1

Implement concept-level states from Step 5 with deliberately conservative inference.

Initial useful states may include:

```text
UNTESTED
DEVELOPING
WEAK
STRONG
REVIEW_NEEDED
```

`MASTERED` should only be introduced when the evidence policy is sufficiently validated.

### Evidence history

Learners can inspect why ARIA believes a topic may be weak/strong.

### Teach-back

ARIA can ask the learner to explain a concept in their own words and use validated evaluation as another evidence source.

### Diagnostic questioning

ARIA can ask follow-up questions when one answer is insufficient to conclude weakness or misconception.

### Revision queue

Weak/review-needed concepts can become revision candidates.

### Memory v1

Persist useful interaction preferences and durable context separately from the Learner Model.

### Progress

Progress reflects meaningful evidence/state rather than only hours spent or pages opened.

### Recommendation Engine v1

Recommendations use:

- active goal;
- current roadmap/context if available;
- learner evidence;
- revision state;
- deadlines where known;
- learner preferences.

## R2 Exit Condition

ARIA can explain not only **what the learner studied**, but cautiously **what evidence suggests they may know, need to review, or have not yet demonstrated**.

---

# 8. R3 — Adaptive Learning System

## Goal

Connect the intelligence layer to planning and learning-path adaptation.

## SHOULD

### Roadmap Engine

Generate goal-specific roadmaps from learner intent/context rather than hardcoded curricula.

### Roadmap editing

Learners can:

- inspect;
- edit;
- reorder;
- accept/reject proposed adaptations.

### Planner

Convert roadmap items and learner commitments into actionable study sessions.

### Availability-aware planning

Plans account for available time and relevant deadlines when the learner provides them.

A universal deadline is not required during onboarding; deadlines belong to relevant goals/exams/events.

### Plan recovery

Missed work triggers feasible recovery rather than an endless overdue pile.

### Revision integration

Revision items compete appropriately with new roadmap work.

### Misconception detection v1

Use repeated evidence/diagnostic questioning before marking supported misconceptions.

### Prerequisite-gap detection v1

Use dependency knowledge + diagnostic evidence before proposing prerequisite remediation.

### Adaptation proposals

Roadmap/planner changes follow Step 4's automation classes.

### Email reminders

Email reminders may be introduced for:

- planned study sessions;
- revision due;
- approaching learner-defined deadlines;
- important accepted plan changes.

Reminder preferences and deduplication are required.

## R3 Exit Condition

ARIA can operate a controlled adaptive loop:

```text
Plan
 ↓
Learn
 ↓
Assess
 ↓
Evidence
 ↓
Learner Model
 ↓
Revision / adaptation proposal
 ↓
Learner approval where needed
 ↓
Updated plan
 ↓
Next action
```

---

# 9. R4 — Audio & Mobile Learning

## Goal

Support learning when reading or typing is inconvenient, including revision while travelling or immediately before an exam.

This is **not merely speech-to-text chat**.

## SHOULD / COULD

### Notes/resources → audio

Learners can generate listenable learning material from selected notes/resources.

### Audio modes

Potential modes include:

```text
Quick revision
Detailed explanation
Question-and-answer revision
Flash review
Topic recap
Exam-before-you-enter recap
```

### Audio grounding

Generated audio remains grounded in the selected learner material/context where requested.

### Audio player

Support:

- play/pause;
- seek;
- playback speed;
- resume position;
- source/title context.

### Interactive voice revision

ARIA can conduct a hands-free question/revision session where technically and safely feasible.

The learner can answer questions verbally and receive the next question/feedback.

### Audio generation lifecycle

Long audio generation uses queued/processing/ready/failed states and cost controls from Step 6.

## R4 Exit Condition

A learner can select their own material and create a useful audio revision experience without manually rebuilding the content in another application.

---

# 10. R5 — External Activity & Integrations

## Goal

Reduce manual fragmentation across learning platforms without trying to replace specialized platforms.

ARIA is **not** trying to become LeetCode, YouTube, or every learning platform.

It should coordinate learning around them where integrations legally and technically permit it.

## COULD

### External resource links

Roadmap items may link to external learning resources appropriate to the learner's goal.

These are dynamically recommended, not hardcoded globally.

### External activity tracking

Where supported through legitimate APIs/integrations, ARIA may ingest relevant completion/activity signals.

Potential examples:

```text
coding-practice activity
course progress
video/resource completion
calendar events
```

### LeetCode-style integration boundary

For placement/DSA learners, ARIA may recommend coding problems and track supported activity where legitimate integration mechanisms exist.

ARIA should not attempt to duplicate the coding platform itself unless a later product decision explicitly introduces an internal coding environment.

### Calendar integration

Planner items may synchronize with supported external calendars.

### Integration permission model

Every external integration shall have explicit user authorization and revocation.

## R5 Explicit Non-Goals

- scraping platforms in violation of their terms;
- pretending unsupported external activity was tracked;
- requiring external integrations for core ARIA functionality;
- replacing specialized platforms merely for feature-count parity.

## R5 Exit Condition

ARIA can coordinate selected external learning activity while remaining useful as a standalone learning system.

---

# 11. R6 — Advanced ARIA

## Goal

Expand ARIA into the fuller autonomous-but-controlled learning operating system envisioned by the product.

## COULD / LATER

Potential capabilities include:

### Advanced Learner Model

- richer mastery modelling;
- forgetting curves;
- concept dependency graphs;
- cross-goal transferable knowledge;
- stronger evidence calibration.

### Advanced misconception reasoning

- misconception pattern library;
- targeted counterexamples;
- repeated diagnostic loops;
- remediation effectiveness tracking.

### Advanced assessment modes

Depending on learner goals:

- timed competitive-style assessments;
- coding assessments;
- viva/oral examinations;
- mixed-format exams;
- section-level timing;
- negative marking;
- custom marking schemes;
- exam templates derived from learner specification.

### Advanced planning

- scenario planning;
- workload balancing across goals;
- exam proximity strategies;
- recovery optimization;
- adaptive revision spacing.

### Advanced agentic workflows

Only after deterministic boundaries, validation, evaluation, observability, and permissions are mature.

Possible specialized reasoning components may handle:

```text
study assistance
assessment generation
assessment evaluation
learner-state reasoning
roadmap generation
planning
revision
resource retrieval
```

This list does **not** mandate one agent per capability.

### Additional modalities

- richer voice interaction;
- diagrams/visual learning support;
- supported image-based study material;
- additional document/media types.

### Advanced integrations

Only where there is demonstrated learner value and reliable APIs/permission models.

---

# 12. Cross-Release Foundation Matrix

| Capability | R0 | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Authentication | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Goals/context | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Resources | foundation | ✓ | improve | improve | audio source | external | advanced |
| Study chat | foundation | ✓ | personalized | adaptive | voice | external context | advanced |
| Notes | foundation | ✓ | improve | integrated | audio source | — | advanced |
| Assessments | foundation | ✓ | improve | adaptive | oral support | external signals | advanced |
| Evidence | foundation | basic | ✓ | ✓ | voice evidence | external signals | advanced |
| Learner Model | schema | minimal | v1 | ✓ | ✓ | ✓ | advanced |
| Revision | schema | basic recommendation | ✓ | integrated | audio | — | advanced |
| Roadmap | schema | optional/basic | basic | ✓ | ✓ | external links | advanced |
| Planner | schema | optional/basic | basic | ✓ | ✓ | calendar | advanced |
| Audio | — | — | — | preparation | ✓ | — | advanced |
| Integrations | — | — | — | email | — | ✓ | advanced |
| Agentic orchestration | — | minimal | minimal | bounded | bounded | bounded | advanced |

---

# 13. MUST / SHOULD / COULD / LATER Summary

## MUST — First coherent product

- authentication;
- learner/account isolation;
- flexible goals;
- goal-aware context;
- Home shell;
- resource ingestion;
- resource-grounded study;
- notes;
- learner-configured assessment generation;
- assessment attempt;
- evaluation;
- basic structured evidence;
- basic next-action recommendation;
- security/reliability baseline.

## SHOULD — ARIA differentiation

- Learner Model;
- teach-back;
- diagnostic questioning;
- revision queue;
- meaningful progress;
- persistent memory;
- roadmap generation;
- adaptive roadmap proposals;
- planner;
- missed-work recovery;
- misconception detection;
- prerequisite-gap detection;
- email reminders;
- notes/resources-to-audio;
- interactive audio revision.

## COULD

- external calendar sync;
- supported external activity tracking;
- richer assessment formats;
- coding-practice coordination;
- advanced voice;
- richer progress analytics;
- additional resource formats;
- deeper cross-goal intelligence.

## LATER

- broad autonomous multi-agent behaviour;
- internal replacement for specialized coding platforms;
- large-scale social/community features;
- video-course hosting platform;
- every possible learning modality;
- integrations without reliable APIs/permissions;
- autonomous high-impact changes without learner control.

---

# 14. What ARIA Must Not Hardcode

The following must remain learner/context-driven rather than universal fixed navigation/content assumptions:

```text
DSA
AWS
GATE
UPSC
bank exams
university subjects
placement preparation
certifications
specific roadmaps
specific resource lists
specific exam formats
```

ARIA may display any of these when relevant to a learner.

It shall not assume they are relevant to every learner.

The product model is:

```text
Learner intent/context
        ↓
Relevant goals
        ↓
Relevant roadmap/resources/assessments
        ↓
Personalized workspace
```

not:

```text
Hardcoded learning categories
        ↓
Learner forced into categories
```

---

# 15. What ARIA Should Not Replace

ARIA's goal is coordination and learning intelligence, not feature cloning.

Unless later evidence supports expansion, ARIA should not attempt to replace:

- dedicated coding judges/practice platforms;
- full video-hosting/course marketplaces;
- general-purpose office suites;
- every note-taking editor;
- every research database;
- every calendar application.

ARIA may integrate, recommend, organize, reason over, or coordinate with these tools where valuable.

---

# 16. Vertical Slice Strategy

Every major implementation milestone should preferably produce a demonstrable learner loop rather than isolated backend components.

Example bad sequencing:

```text
Build 15 agents
Build 8 databases
Build audio
Build calendar integration
Build analytics
...
Eventually connect them
```

Preferred sequencing:

```text
Goal
 ↓
Resource
 ↓
Study
 ↓
Assessment
 ↓
Evaluation
 ↓
Next action
```

Then deepen it:

```text
Assessment
 ↓
Evidence
 ↓
Learner Model
 ↓
Revision
```

Then:

```text
Learner Model
 ↓
Roadmap
 ↓
Planner
 ↓
Recovery
```

Then:

```text
Notes / Resources
 ↓
Audio revision
```

Then connect external ecosystems.

---

# 17. Feature Dependency Rules

## REL-DEP-001

Learner Model implementation depends on reliable evidence representation.

## REL-DEP-002

Adaptive roadmap behaviour depends on Learner Model confidence and Step 4 approval controls.

## REL-DEP-003

Planner adaptation depends on a stable roadmap/task representation.

## REL-DEP-004

Misconception detection depends on repeated/diagnostic evidence rather than raw chat memory.

## REL-DEP-005

Prerequisite-gap adaptation depends on concept dependency knowledge plus evidence.

## REL-DEP-006

Audio generation depends on reliable source/resource selection and content processing.

## REL-DEP-007

External activity tracking depends on legitimate integration access and explicit user authorization.

## REL-DEP-008

Advanced agentic orchestration depends on mature tool authorization, validation, observability, retry limits, and evaluation.

## REL-DEP-009

Email reminders depend on stable planner/revision/deadline state and notification preferences.

## REL-DEP-010

Progress analytics depend on meaningful learning events/evidence, not merely UI activity.

---

# 18. Anti-Premature-Complexity Rules

During early implementation, ARIA should resist building complexity merely because it may eventually be useful.

Do **not** prematurely build:

1. microservices for every feature;
2. one AI agent per page;
3. complex inter-agent protocols before workflows require them;
4. a knowledge graph before simpler concept relationships prove insufficient;
5. a custom vector database;
6. a custom authentication system;
7. a custom coding judge without demonstrated need;
8. every external integration at once;
9. an elaborate event infrastructure before event volume/requirements justify it;
10. complex ML mastery models before sufficient real learner evidence exists.

This does not forbid these technologies later. It prevents architecture from becoming a research project before ARIA becomes a usable product.

---

# 19. Release Evaluation Questions

Before advancing a major release, the team should be able to answer:

### R1

Can a learner actually learn something useful end-to-end inside ARIA?

### R2

Does ARIA's evidence model produce learner-state conclusions that are more useful than simple test scores?

### R3

Do adaptive roadmap/planner changes help learners recover and progress without making the product feel uncontrollable?

### R4

Does audio materially improve revision/accessibility/travel learning rather than merely demonstrating text-to-speech?

### R5

Do integrations reduce fragmentation enough to justify their maintenance and permission complexity?

### R6

Does additional autonomy measurably improve learning workflows enough to justify agentic complexity?

---

# 20. Product Success Progression

ARIA's success should mature alongside the releases.

```text
R1:
Can users complete the core learning loop?

R2:
Does ARIA understand performance better over time?

R3:
Does ARIA improve what learners do next?

R4:
Can ARIA support learning beyond screen-reading workflows?

R5:
Can ARIA reduce fragmentation across tools?

R6:
Can ARIA coordinate increasingly complex learning with trustworthy autonomy?
```

---

# 21. Full-Vision Preservation

Deferring a capability shall not delete it from the product vision.

The PRD should preserve future requirements so early architecture understands likely direction while implementation remains focused.

ARIA can therefore simultaneously have:

```text
A large product vision
        +
A small first release
        +
Clear expansion boundaries
```

These are not contradictions.

---

# 22. Step 7 Decisions

Step 7 establishes the implementation strategy:

1. **ARIA remains the all-in-one coordinated learning system envisioned from the beginning.**
2. **The product will not attempt to implement every capability simultaneously.**
3. **The first usable ARIA is a complete learning loop, not a collection of half-built pages.**
4. **Goals, resources, assessment formats, and recommendations remain user/context-driven rather than hardcoded.**
5. **Evidence precedes sophisticated personalization.**
6. **Personalization precedes high-impact adaptation.**
7. **Roadmap/planner automation remains learner-controlled.**
8. **Audio is a real learning mode, not simply voice input.**
9. **ARIA coordinates specialized external platforms instead of automatically cloning them.**
10. **Advanced multi-agent architecture is deliberately deferred until simpler reliable workflows prove insufficient.**
11. **Release boundaries protect buildability without shrinking the final product vision.**

---

# 23. Step 7 Completion

**Step 7 — Scope, Prioritization & Release Boundaries is complete.**

Phase 1 PRD now contains:

```text
01 — Product Overview & Goals
02 — User & Learning Context Requirements
03 — Functional Requirements
04 — Cross-System & Automation Requirements
05 — AI, Learner Model, Memory & Evidence Requirements
06 — Non-Functional, Privacy, Security, Reliability & Accessibility
07 — Scope, Prioritization & Release Boundaries
```

Next:

# Step 8 — Acceptance Criteria, Success Metrics & PRD Closure

Step 8 should convert the requirements into testable product outcomes and close Phase 1.

It will define:

```text
core user journeys
acceptance criteria
release-level Definition of Done
product success metrics
learning-quality metrics
AI quality/evaluation metrics
reliability metrics
safety/control metrics
R1 launch gates
open questions / assumptions
out-of-scope confirmation
PRD traceability
Phase 1 completion checklist
```

After Step 8, ARIA should be ready to move from **what the product must do** into the next major phase: **system architecture and technical design**.