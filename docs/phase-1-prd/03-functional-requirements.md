# ARIA — Phase 1 PRD

## Step 3 — Functional Requirements

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Reviewed and release-classified  
**Primary sources:** `VISION.md`, Steps 1, 2 and 7

---

# 1. Purpose

This document defines ARIA's major user-facing functional requirements while separating the **complete product vision** from the **minimum R0 adaptive-learning validation loop**.

A requirement appearing here does not automatically mean it belongs in R0.

---

# 2. Release Labels

- **R0 MUST** — required to test the first adaptive-learning hypothesis.
- **R1+** — learning-path adaptation.
- **R2+** — longitudinal learning/revision/progress.
- **R3+** — learning coordination/planning/reminders.
- **R4+** — richer learning interfaces such as Notes and Audio.
- **R5+** — mature orchestration/integrations.
- **LONG-TERM MUST** — product requirement whose exact release may be determined later.
- **SHOULD / MAY** — desirable or conditional behaviour.

R0 elimination rule:

> **If removing a feature still allows us to test whether evidence changes learner_concept_state and learner_concept_state changes future study, that feature is probably not required for R0.**

---

# 3. R0 Functional Spine

```text
Authentication
    ↓
One Goal / Learning Context
    ↓
Resources
    ↓
Study
    ↓
Assessment
    ↓
Evaluation
    ↓
Structured Evidence
    ↓
Basic learner_concept_state
    ↓
Adapted Study
    ↓
Reassessment / Second Cycle
```

Evidence and learner_concept_state receive their detailed requirements in Step 5.

---

# 4. Account & Authentication

## FR-AUTH-001 — Account creation — R0 MUST
The learner shall be able to create an account.

## FR-AUTH-002 — Sign in — R0 MUST
An existing learner shall be able to authenticate and access persistent R0 learning state.

## FR-AUTH-003 — Email verification — SHOULD
Email verification should be supported where email/password identity is used and required by the chosen authentication design.

## FR-AUTH-004 — Password recovery — SHOULD
A secure recovery/reset flow shall exist when password-based authentication is used.

## FR-AUTH-005 — Session persistence — R0 MUST
Normal return visits should preserve authenticated access appropriately.

## FR-AUTH-006 — Sign out — R0 MUST
The learner shall be able to end an authenticated session.

## FR-AUTH-007 — Account access protection — R0 MUST
Private learner data shall require appropriate authorization.

## FR-AUTH-008 — Rich account management — LATER
Full profile/security settings are not required to prove R0 beyond necessary account/privacy controls.

---

# 5. Onboarding

## FR-ONB-001 — Lightweight onboarding — R0 MUST
ARIA shall not require complete learner profiling before use.

## FR-ONB-002 — Initial intent — R0 MUST
The learner shall be able to describe the learning/preparation context they currently want help with.

## FR-ONB-003 — Custom intent — R0 MUST
The learner shall not be restricted to hardcoded subject/exam categories.

This does not mean R0 must successfully validate every possible domain.

## FR-ONB-004 — Optional skipping — SHOULD
Non-essential onboarding questions should be skippable.

## FR-ONB-005 — No universal deadline — R0 MUST
A single global deadline shall not be mandatory.

## FR-ONB-006 — Progressive guidance — SHOULD
ARIA should introduce capabilities contextually.

## FR-ONB-007 — Onboarding persistence — R0 MUST
Useful R0 onboarding/context information shall persist according to scope.

---

# 6. Goals / Learning Context

## FR-GOAL-001 — Create goal/context — R0 MUST
The learner shall be able to establish at least one learning goal/context using natural language.

## FR-GOAL-002 — Edit goal — SHOULD
The learner should be able to correct relevant R0 goal/context details.

## FR-GOAL-003 — Optional deadline — LONG-TERM MUST
Goals may contain deadlines, but R0 shall not structurally require one.

## FR-GOAL-004 — Priority — R3+
Goal priority becomes important when coordinating multiple goals.

## FR-GOAL-005 — Multiple goals — LONG-TERM MUST
ARIA shall eventually support multiple simultaneous goals; this is not required for R0.

## FR-GOAL-006 — Goal lifecycle — LATER
Pause/completed/archive lifecycle is deferred unless needed for basic implementation hygiene.

## FR-GOAL-007 — Resume goal — LATER
Rich pause/resume behaviour is deferred; R0 only requires persistence of its validation context.

## FR-GOAL-008 — Goal overview — R1+
Rich goal overview becomes meaningful with Roadmap/progress systems.

## FR-GOAL-009 — Goal decomposition — R1+
Roadmap/path decomposition is not required for R0.

## FR-GOAL-010 — Goal deletion — LONG-TERM MUST
Deletion must comply with later privacy/data requirements.

---

# 7. Home

The complete Home is ARIA's personalized learning command centre, but it is not necessary to prove R0.

## FR-HOME-001 — Personalized Home — R3+
## FR-HOME-002 — Active goals — R3+
## FR-HOME-003 — Today's work — R3+
## FR-HOME-004 — Due revision — R2/R3+
## FR-HOME-005 — Upcoming events — R3+
## FR-HOME-006 — Progress summary — R2+
## FR-HOME-007 — Recommended next action — R3+
## FR-HOME-008 — Continue learning — SHOULD
A minimal R0 entry/resume surface may exist without implementing the complete Home intelligence layer.
## FR-HOME-009 — Proposed changes — R1/R3+
## FR-HOME-010 — Honest empty state — LONG-TERM MUST
ARIA shall not fabricate personalized insights when insufficient data exists.

---

# 8. Study

Study is one of R0's core systems.

## FR-STUDY-001 — Start study interaction — R0 MUST
The learner shall be able to start a conversational learning interaction.

## FR-STUDY-002 — Context association — R0 MUST
R0 study shall be attributable to the active validation goal/topic/context.

## FR-STUDY-003 — Resource-grounded study — R0 MUST
The learner shall be able to study using selected supported resources/context.

## FR-STUDY-004 — Follow-up questions — R0 MUST
ARIA shall support multi-turn follow-up while retaining relevant session context.

## FR-STUDY-005 — Explanation adjustment — R0 MUST
The learner shall be able to request a different explanation depth/style during the session.

## FR-STUDY-006 — Guided learning — SHOULD
## FR-STUDY-007 — Socratic mode — LATER/R2+
## FR-STUDY-008 — Hinting — SHOULD
## FR-STUDY-009 — Teach-back — R2+
## FR-STUDY-010 — Rapid revision — R2/R4+

## FR-STUDY-011 — Source visibility — R0 MUST
Where study output materially depends on selected resources, relevant provenance shall be retainable/surfaceable.

## FR-STUDY-012 — Conversation persistence — R0 MUST
R0 study interactions required for repeated validation cycles shall persist.

## FR-STUDY-013 — Conversation organization/search — R4+

## FR-STUDY-014 — Downstream material — PARTIAL R0
Study context shall be usable by R0 Assessment. Notes/Audio downstream generation is deferred to R4+.

## FR-STUDY-015 — Correct active context — R0 MUST
The learner shall be able to correct goal/topic/resource context.

## FR-STUDY-016 — Evidence-driven adapted study — R0 MUST
ARIA shall be able to materially alter a subsequent study interaction using supported learner-state/evidence signals.

Examples include targeted explanation, prerequisite revisit, changed scaffolding, targeted practice, or reduced emphasis on already-supported concepts.

## FR-STUDY-017 — Adaptation rationale — R0 MUST
The system shall retain a testable reason/provenance for an R0 adaptation.

---

# 9. Resources & Retrieval

## FR-RES-001 — Add supported resources — R0 MUST
The learner shall be able to add the resource type(s) selected for the validation context.

## FR-RES-002 — File resources — PARTIAL R0
R0 needs only the smallest reliable file/input surface required for validation, for example PDF and/or pasted text. Broad file-format support is later.

## FR-RES-003 — Web links — LATER
## FR-RES-004 — Resource metadata — R0 MUST
Store metadata necessary for attribution/provenance.

## FR-RES-005 — Goal/topic association — R0 MUST
Supported resources shall be attributable to the active validation context.

## FR-RES-006 — Rich resource organization — R4+
## FR-RES-007 — Resource search — R4+

## FR-RES-008 — Content retrieval — R0 MUST
ARIA shall retrieve relevant content from the selected supported resource input for R0 learning tasks.

## FR-RES-009 — Provenance — R0 MUST
Retrieved content used by AI features shall retain source provenance where technically applicable.

## FR-RES-010 — Explicit resource selection — R0 MUST
The learner shall be able to choose the supported resource/context used for study/assessment.

## FR-RES-011 — Resource removal — LONG-TERM MUST
## FR-RES-012 — Processing status — R0 MUST
The learner shall be able to distinguish ready/processing/failed/unsupported states for R0 resources.

## FR-RES-013 — Failure recovery — R0 MUST
Resource-processing failure shall not corrupt unrelated persisted learner_concept_state.

## FR-RES-014 — External specialist resources — R5+
ARIA may later link/integrate with specialist learning platforms rather than recreating them.

---

# 10. Notes — R4+

Notes remain a major ARIA capability but are explicitly **not required for R0**.

Long-term requirements remain:

- **FR-NOTE-001** manual notes;
- **FR-NOTE-002** generate from Study;
- **FR-NOTE-003** generate from Resources;
- **FR-NOTE-004** editable notes;
- **FR-NOTE-005** contextual organization;
- **FR-NOTE-006** concise/detailed/summary/revision transformations;
- **FR-NOTE-007** source references;
- **FR-NOTE-008** search;
- **FR-NOTE-009** Notes → Assessment;
- **FR-NOTE-010** Notes → Audio;
- **FR-NOTE-011** archive/delete according to data rules.

Deferring Notes does not remove them from the ARIA vision.

---

# 11. Assessment Engine

ARIA's long-term Assessment Engine remains specification-driven. R0 implements only the subset needed to produce reliable learning evidence in the chosen validation context.

## FR-ASSESS-001 — Create assessment — R0 MUST
The learner shall be able to create/start a supported assessment for the validation context.

## FR-ASSESS-002 — Assessment specification — R0 MUST
R0 assessments shall have an explicit structured specification, even if the UI exposes only a subset of long-term configuration.

## FR-ASSESS-003 — Topic/scope — R0 MUST
## FR-ASSESS-004 — Resource/context selection — R0 MUST

## FR-ASSESS-005 — Question-format selection — PARTIAL R0
The learner shall control the final format among formats actually supported by R0.

R0 does **not** need every planned format. Long-term formats may include MCQ, multiple-select, true/false, fill-in, numerical, short/long answer, conceptual/application, problem solving, viva, teach-back, coding, and mixed sections.

## FR-ASSESS-006 — Question count / size — R0 MUST
## FR-ASSESS-007 — Difficulty — SHOULD
## FR-ASSESS-008 — Duration — SHOULD / CONTEXT-DEPENDENT
Timed behaviour is required only if selected for the R0 validation context.

## FR-ASSESS-009 — Multi-section assessments — LATER
## FR-ASSESS-010 — Advanced scoring configuration — LATER
Basic R0 scoring rules shall still be explicit.

## FR-ASSESS-011 — Feedback timing — LATER
## FR-ASSESS-012 — Natural-language configuration — SHOULD
## FR-ASSESS-013 — Specification preview/edit — R0 MUST
## FR-ASSESS-014 — ARIA recommendations — LATER

## FR-ASSESS-015 — Dynamic rendering — PARTIAL R0
R0 shall correctly render the formats it supports; universal assessment rendering is later.

## FR-ASSESS-016 — Timed assessment — CONTEXT-DEPENDENT
## FR-ASSESS-017 — Save attempt — R0 MUST
## FR-ASSESS-018 — Submit assessment — R0 MUST
## FR-ASSESS-019 — Attempt history — PARTIAL R0
R0 shall retain attempts/evidence needed for repeated validation cycles; rich history UI is later.

## FR-ASSESS-020 — Reassess — R0 MUST
The learner shall be able to complete a subsequent targeted assessment/reassessment so new evidence can update the learner-state estimate.

## FR-ASSESS-021 — Coding assessments — LATER / CONTEXT-DEPENDENT
## FR-ASSESS-022 — Viva/oral assessment — R4+
## FR-ASSESS-023 — Teach-back assessment — R2+

---

# 12. Evaluation

Evaluation is an R0 core system.

## FR-EVAL-001 — Evaluate responses — R0 MUST
Supported responses shall be evaluated according to their assessment format/rules.

## FR-EVAL-002 — Separate generation/evaluation — R0 MUST
Assessment generation and evaluation shall remain logically separable responsibilities.

## FR-EVAL-003 — Score where appropriate — R0 MUST
Deterministic scoring shall be used where appropriate.

## FR-EVAL-004 — Feedback — R0 MUST
The learner shall receive useful feedback after evaluation according to R0 behaviour.

## FR-EVAL-005 — Concept/topic-level result — R0 MUST
Evaluation shall produce enough concept/topic attribution to create meaningful evidence.

## FR-EVAL-006 — Explanation — SHOULD
## FR-EVAL-007 — Rubric evaluation — CONTEXT-DEPENDENT
Open-ended evaluation is only R0-required if the validation context uses it.

## FR-EVAL-008 — Uncertainty — R0 MUST
Subjective/uncertain evaluation shall not be represented as perfectly objective.

## FR-EVAL-009 — Structured evidence output — R0 MUST
Evaluation shall produce validated structured output usable by the Evidence system.

## FR-EVAL-010 — Review answers — R0 MUST
## FR-EVAL-011 — Correction/re-evaluation path — R0 MUST
A corrected evaluation must be able to propagate appropriately to dependent R0 evidence/state.

## FR-EVAL-012 — Evaluation failure safety — R0 MUST
Failed/invalid evaluation shall not become false negative learning evidence.

---

# 13. Roadmaps — R1+

Roadmaps are deliberately excluded from R0. R1 tests whether accumulated evidence can adapt a structured learning path.

Long-term/R1 requirements remain:

- **FR-ROAD-001** generate roadmap;
- **FR-ROAD-002** phases/milestones/topics/subtopics/prerequisites/dependencies;
- **FR-ROAD-003** learner editing;
- **FR-ROAD-004** resource attachment;
- **FR-ROAD-005** element progress/state;
- **FR-ROAD-006** dependencies;
- **FR-ROAD-007** evidence-aware adaptation proposal;
- **FR-ROAD-008** explain adaptation;
- **FR-ROAD-009** accept/modify/reject;
- **FR-ROAD-010** history/auditability;
- **FR-ROAD-011** multiple roadmaps later;
- **FR-ROAD-012** no mandatory deadline.

---

# 14. Planner — R3+

Planner is deliberately excluded from R0.

Long-term requirements remain:

- **FR-PLAN-001** create time-based plan;
- **FR-PLAN-002** availability;
- **FR-PLAN-003** multiple-goal planning;
- **FR-PLAN-004** deadlines;
- **FR-PLAN-005** roadmap scheduling;
- **FR-PLAN-006** revision scheduling;
- **FR-PLAN-007** assessment scheduling;
- **FR-PLAN-008/009** day/week views;
- **FR-PLAN-010** manual changes;
- **FR-PLAN-011/012** missed-work detection/recovery;
- **FR-PLAN-013** explain recovery;
- **FR-PLAN-014** conflict detection;
- **FR-PLAN-015** temporary availability;
- **FR-PLAN-016** learner review/approval.

---

# 15. Revision — R2+

R0 can adapt the immediate next Study experience and perform reassessment without building the complete Revision system.

Long-term requirements remain:

- **FR-REV-001** identify revision items;
- **FR-REV-002/003** schedule/surface due revision;
- **FR-REV-004** retrieval-based revision;
- **FR-REV-005** multiple revision formats;
- **FR-REV-006** evidence-informed priority;
- **FR-REV-007** history;
- **FR-REV-008** completion/evidence;
- **FR-REV-009** targeted retesting;
- **FR-REV-010** time-constrained revision.

---

# 16. Progress — R2+

R0 needs inspectable evidence/state for validation, not a full learner-facing Progress product.

Long-term requirements remain:

- **FR-PROG-001** goal progress;
- **FR-PROG-002** roadmap progress;
- **FR-PROG-003** assessment history;
- **FR-PROG-004** learner_concept_state;
- **FR-PROG-005** revision health;
- **FR-PROG-006** improvement over time;
- **FR-PROG-007** sufficiently supported misconception/gap signals;
- **FR-PROG-008** untested ≠ weak;
- **FR-PROG-009** activity ≠ mastery;
- **FR-PROG-010** uncertainty-aware readiness.

The principles behind FR-PROG-008/009 apply to R0's internal learner_concept_state even though the Progress UI is deferred.

---

# 17. Recommendations

## FR-REC-001 — Adapted next study action — R0 MUST
ARIA shall be capable of selecting an evidence/state-informed next study action within the R0 loop.

## FR-REC-002 — Broad recommendation types — LATER
Long-term recommendations may include Study, Revision, Assessment, prerequisites, Roadmap, Planner, or proposed changes.

## FR-REC-003 — Reason — R0 MUST
An R0 adaptation/recommendation shall have a testable understandable reason.

## FR-REC-004 — Context awareness — R0 MUST
Recommendations shall use the correct active validation context/state.

## FR-REC-005 — Time awareness — R3+
## FR-REC-006 — User override — R0 MUST
The learner remains free to ignore an adaptive recommendation and choose another supported action.

## FR-REC-007 — No fabricated certainty — R0 MUST
ARIA shall not pretend weak evidence supports strong personalization.

---

# 18. Audio Learning — R4+

Audio remains a major ARIA feature and directly supports the long-term use case of hands-free/travel/pre-exam revision, but it is not needed to prove R0's adaptive-learning hypothesis.

Long-term requirements remain:

- **FR-AUDIO-001** Notes → Audio;
- **FR-AUDIO-002** Resources → Audio;
- **FR-AUDIO-003** Study → Audio;
- **FR-AUDIO-004** purpose such as explanation/summary/revision;
- **FR-AUDIO-005** desired duration;
- **FR-AUDIO-006** evidence/state-aware adaptive revision audio;
- **FR-AUDIO-007** playback;
- **FR-AUDIO-008** regeneration;
- **FR-AUDIO-009** later interactive spoken Q&A;
- **FR-AUDIO-010** source traceability.

---

# 19. Search — R4+

Long-term requirements remain:

- **FR-SEARCH-001** unified learning search;
- **FR-SEARCH-002** chats/notes/resources/roadmaps/assessments/history;
- **FR-SEARCH-003** context filters;
- **FR-SEARCH-004** navigation;
- **FR-SEARCH-005** semantic retrieval;
- **FR-SEARCH-006** authorization boundaries.

Internal resource retrieval required for R0 Study is covered by `FR-RES-008`; that does not require a full user-facing unified Search product.

---

# 20. Notifications & Reminders — R3+

Email reminders remain part of ARIA, but R0 does not require them.

Long-term requirements remain:

- **FR-NOTIF-001** in-app notifications;
- **FR-NOTIF-002** email reminders;
- **FR-NOTIF-003** notification preferences;
- **FR-NOTIF-004** Planner reminders;
- **FR-NOTIF-005** Revision reminders;
- **FR-NOTIF-006** Assessment reminders;
- **FR-NOTIF-007** deadline reminders;
- **FR-NOTIF-008** proposed-change notifications;
- **FR-NOTIF-009** frequency control;
- **FR-NOTIF-010** disable optional notifications;
- **FR-NOTIF-011** actionable deep-link/context behaviour.

---

# 21. Settings & Learner Controls

## FR-SET-001 — Basic account/profile controls — R0 MUST
Only controls necessary for account identity and R0 use are required initially.

## FR-SET-002 — Learning preferences — SHOULD
R0 may expose preferences that materially affect Study.

## FR-SET-003 — Notification settings — R3+
## FR-SET-004 — Memory controls — R2+

## FR-SET-005 — Learner-state correction — R0 MUST
Important inaccurate R0 learner-state assumptions shall have an appropriate correction/review path.

## FR-SET-006 — Privacy/data controls — R0 MUST AS APPLICABLE
Step 6 defines the exact minimum.

## FR-SET-007 — Integrations — R5+
## FR-SET-008 — Accessibility preferences — LONG-TERM MUST
Required baseline accessibility is handled in Step 6 even if a rich preference UI is later.

## FR-SET-009 — Account deletion — LONG-TERM MUST
Must comply with privacy/data obligations.

---

# 22. Global Functional Requirements

## FR-GLOBAL-001 — Domain extensibility — R0 MUST AS PRINCIPLE
ARIA shall avoid unnecessary coupling that prevents later domain generalization.

R0 is **not required to demonstrate support for every domain** and may contain implementation details specific to the chosen validation context when those details are not incorrectly embedded as universal product rules.

## FR-GLOBAL-002 — Multiple goals — LONG-TERM MUST
Major mature systems shall eventually operate correctly with multiple goals; this is not an R0 acceptance criterion.

## FR-GLOBAL-003 — Context preservation — R0 MUST
Relevant context shall persist through the R0 functional spine.

## FR-GLOBAL-004 — Context correction — R0 MUST
## FR-GLOBAL-005 — User override — R0 MUST WHERE APPLICABLE
## FR-GLOBAL-006 — Honest empty/unknown states — R0 MUST
## FR-GLOBAL-007 — Graceful partial intelligence — R0 MUST
Core behaviour shall remain useful when advanced learner modeling/orchestration is unavailable.

## FR-GLOBAL-008 — Provenance — R0 MUST
Material AI outputs based on resources/evidence shall retain appropriate provenance.

## FR-GLOBAL-009 — Explainability — R0 MUST
Significant R0 adaptive decisions shall have a reason that can be surfaced/inspected.

## FR-GLOBAL-010 — External ecosystem — R5+
ARIA may integrate/link to specialist platforms rather than rebuilding them.

---

# 23. R0 Functional Product Map

```text
                    R0 ARIA
                       │
              Identity / Account
                       │
             Goal / Learning Context
                       │
                   Resources
                       │
                     Study
                       │
                  Assessment
                       │
                  Evaluation
                       │
                    Evidence
                       │
              Basic learner_concept_state
                       │
                Adapted Study
                       │
                  Reassessment
                       │
                       ↺
```

Everything outside this map must justify itself using the R0 elimination test.

---

# 24. Complete Product Map

```text
                         ARIA
                          │
       ┌──────────────────┼───────────────────┐
       │                  │                   │
   IDENTITY            LEARNING          ORGANIZATION
       │                  │                   │
 Authentication         Study               Goals
 Onboarding             Resources           Roadmaps
 Settings               Notes               Planner
                        Assessment           Revision
                        Evaluation           Progress
                        Audio                Recommendations
                          │                   │
                          └─────────┬─────────┘
                                    │
                              Home + Search
                                    │
                              Notifications
```

This remains the long-term product map, not R0 scope.

---

# 25. R0 End-to-End Functional Scenario

Illustrative only; the final validation context is still an open PRD decision.

```text
Learner creates/enters:
"Prepare DBMS Transactions"
        ↓
Adds/selects supported notes/PDF
        ↓
Studies Transactions with ARIA
        ↓
Takes supported assessment
        ↓
ARIA evaluates responses
        ↓
Structured concept evidence is stored
        ↓
Basic learner_concept_state updates conservatively
        ↓
ARIA identifies a supported next-study adaptation
        ↓
Example: focus on conflict serializability with different scaffolding
        ↓
Learner studies adapted material
        ↓
Targeted reassessment
        ↓
New evidence updates/qualifies previous state
```

This scenario is intentionally missing Roadmap, Planner, Notes, Audio, full Progress, reminders, and multi-goal coordination. Their absence is the scope decision, not an omission from the vision.

---

# 26. Functional Scope Validation

The reviewed Step 3 now preserves both truths:

**ARIA's complete vision remains broad:** Goals, Home, Study, Resources, Notes, Assessment, Evaluation, Roadmaps, Planner, Revision, Progress, Recommendations, Audio, Search, Notifications, Settings and future integrations remain part of the product direction.

**R0 remains narrow:** Authentication + one context + Resources + Study + Assessment + Evaluation + Evidence + Basic learner_concept_state + Adapted Study + Reassessment.

R0 does not require universal domain support, multiple simultaneous goals, full Notes, Audio, Planner, Roadmap, Progress, Revision, Search, notifications, coding infrastructure, oral assessment, or mature orchestration.

---

# 27. Step 3 Completion

**Step 3 — Functional Requirements has been audited and realigned.**

The old document described almost every full-vision capability using mandatory language without release boundaries. The requirements are now preserved but classified so they cannot silently become R0 implementation scope.

Next:

# Step 4 — Cross-System & Automation Requirements Audit

Step 4 should narrow the R0 event/automation chain to:

```text
Assessment submitted
        ↓
Evaluation
        ↓
Evidence
        ↓
Basic learner_concept_state
        ↓
Adaptation decision
        ↓
Adapted Study
        ↓
Reassessment
```

Later Progress, Revision, Roadmap, Planner, Home, notifications and advanced orchestration should remain documented without being required to validate R0.
---

## Next

Step 4 — Cross-System & Automation Requirements.
