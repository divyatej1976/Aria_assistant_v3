# ARIA — Phase 1 PRD

## Step 2 — User & Learning-Context Requirements

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Reviewed and aligned with amended `VISION.md`  
**Primary sources:** `VISION.md`, `01-product-overview-goals.md`, `07-scope-prioritization-release-boundaries.md`

---

# 1. Purpose

This document defines what ARIA must know about a learner, how learning contexts should be represented, and how identity, goals, preferences, constraints, and inferred information behave across the product.

It distinguishes **long-term product-model requirements** from the smaller subset required to validate R0.

Long-term principle:

> **One learner identity may contain many goals and learning contexts, while each context preserves the information relevant to that goal.**

R0 does not need to implement the entire multi-goal model to prove adaptive learning.

---

# 2. Audience & User Model

ARIA initially serves college students, recent graduates, and early-career learners working toward academic, placement, competitive-exam, certification, interview, technical/professional skill, or upskilling goals.

ARIA should model a person as a persistent learner rather than permanently classifying them as one exam candidate, subject-specific user, or learner category.

Long-term model:

```text
Learner
│
├── Account / Identity
├── Global Preferences
├── Memory
├── Goal A
│   └── Learning Context A
├── Goal B
│   └── Learning Context B
└── Additional contexts/history where appropriate
```

The product must not permanently classify the learner as only a university student, competitive-exam candidate, coding learner, certification learner, interview candidate, or self-directed learner. Those are contexts the learner may enter, leave, or combine.

---

# 3. Requirement Scope Labels

Requirements use these maturity labels:

- **R0 MUST** — necessary to validate the first adaptive-learning loop.
- **LONG-TERM MUST** — required by the complete product model but not required for R0 validation.
- **SHOULD / MAY** — desirable or conditional behaviour whose release can be determined later.

Requirement identifiers remain stable for traceability.

```text
UR-ID-*       Identity and account context
UR-ONB-*      Onboarding
UR-GOAL-*     Goals
UR-CTX-*      Learning contexts
UR-DEAD-*     Deadlines / time constraints
UR-PREF-*     Preferences
UR-CONT-*     Continuity
UR-SWITCH-*   Context switching
UR-INF-*      Inference and correction
UR-MULTI-*    Multiple goals
UR-STATE-*    Goal/context lifecycle
```

---

# 4. Identity Requirements

## UR-ID-001 — Persistent learner identity — R0 MUST

ARIA shall associate persistent validation data with an authenticated learner identity.

## UR-ID-002 — Identity is broader than a goal — LONG-TERM MUST

The learner account shall remain stable as goals are created, completed, paused, archived, or deleted.

## UR-ID-003 — Global vs context-specific information — LONG-TERM MUST

ARIA shall distinguish information that applies globally from information that applies only to a specific learning context.

Example:

```text
Global:
"Prefer concise explanations first."

Context-specific:
"For this university exam, answers should follow the uploaded syllabus."
```

## UR-ID-004 — Context leakage prevention — R0 MUST

Information/evidence from one validation context shall not silently contaminate an unrelated context.

R0 may demonstrate this through controlled fixtures even if the user-facing product initially exposes only one active goal.

---

# 5. Onboarding Requirements

## UR-ONB-001 — Lightweight onboarding — R0 MUST

Initial onboarding shall request only information necessary to begin using ARIA effectively.

## UR-ONB-002 — No mandatory universal deadline — R0 MUST

Onboarding shall not assume every learner has one deadline or examination date. Deadlines belong to goals/events where relevant.

## UR-ONB-003 — Broad starting intent — R0 MUST

ARIA may ask what the learner currently wants help with or allow creation of an initial goal/context in the learner's own language.

Examples such as learning a topic, preparing for an exam, interview, certification, or custom goal are illustrative rather than hardcoded product categories.

## UR-ONB-004 — Optional initial preferences — SHOULD

ARIA may collect a small set of immediately useful preferences. They remain editable.

## UR-ONB-005 — Progressive discovery — LONG-TERM MUST

Information not required initially should be collected when it becomes relevant.

## UR-ONB-006 — Product guidance — SHOULD

Major capabilities should be introduced contextually rather than through a long signup questionnaire.

---

# 6. Goal Requirements

## UR-GOAL-001 — Create a learning goal/context — R0 MUST

The learner shall be able to establish at least one learning goal/context for the R0 validation loop.

Examples:

```text
Prepare for a DBMS semester exam
Learn FastAPI fundamentals
Prepare one certification topic
Revise a defined subject unit
```

Examples are not hardcoded categories.

## UR-GOAL-002 — Custom goal language — R0 MUST

Learners shall be able to describe the validation goal/context in their own words rather than selecting only from predefined domain categories.

## UR-GOAL-003 — Goal metadata — LONG-TERM MUST

A goal may eventually contain title, description, desired outcome, optional deadlines, priority, status, resources, roadmap, plan, and assessment context. Not every field is mandatory.

R0 only needs metadata necessary for the selected validation context.

## UR-GOAL-004 — Goals without deadlines — LONG-TERM MUST

ARIA's product model shall support open-ended goals. R0 should not make a deadline structurally mandatory.

## UR-GOAL-005 — Goal refinement — SHOULD

Learners should be able to modify a goal as intention changes.

## UR-GOAL-006 — Goal decomposition — LATER RELEASE

Broad-goal decomposition into phases, milestones, topics, or subgoals is primarily a learning-path/Roadmap concern and is not required for R0.

## UR-GOAL-007 — Suggested goals require confirmation — LONG-TERM MUST

ARIA shall not silently create consequential long-term goals from casual conversation without appropriate learner confirmation.

---

# 7. Multiple-Goal Requirements

Multiple simultaneous goals are part of ARIA's complete product model, **not an R0 validation requirement**.

## UR-MULTI-001 — Multiple simultaneous goals — LONG-TERM MUST

ARIA shall eventually support multiple active learning goals for one learner.

## UR-MULTI-002 — Independent contexts — LONG-TERM MUST

Each goal shall be capable of maintaining its own relevant resources, roadmap, assessment configuration, progress, deadlines, and learning state.

## UR-MULTI-003 — Shared learner identity — LONG-TERM MUST

Multiple goals shall remain connected to the same learner identity while preserving context boundaries.

## UR-MULTI-004 — Goal priority — LATER RELEASE

Learners can eventually indicate/modify priority. Evidence/deadline-based reprioritization must remain visible.

## UR-MULTI-005 — Scheduling conflicts — R3+

Cross-goal time allocation belongs to the learning-coordination release and is not an R0 requirement.

## UR-MULTI-006 — Goal-specific progress/evidence — LONG-TERM MUST

Progress/evidence from one goal shall not be incorrectly interpreted as another goal's progress. Justified reuse should retain provenance.

---

# 8. Learning Context Requirements

A **Learning Context** represents the active information surrounding a learning activity.

Long-term it may include learner, goal, topic/concept, resources, current activity, relevant history, assessment context, Roadmap/Plan state, learner-state evidence, preferences, and time constraints.

R0 requires only the subset needed for the adaptive loop.

## UR-CTX-001 — Context association — R0 MUST

Study, assessment, evaluation, evidence, learner_concept_state, and subsequent adaptation shall be attributable to the relevant validation goal/context and concept/topic where applicable.

## UR-CTX-002 — Exploratory learning — LATER RELEASE

ARIA may eventually support learning not attached to a formal goal. R0 may require an explicit validation context to simplify evidence attribution.

## UR-CTX-003 — Context propagation — R0 MUST

Relevant context shall propagate through the R0 loop without requiring the learner to repeatedly reselect the same goal/topic/resources.

```text
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
Adapted Study
```

## UR-CTX-004 — Context visibility — R0 MUST

The active validation goal/topic/resource context shall be understandable where ambiguity could produce incorrect evidence or adaptation.

## UR-CTX-005 — Context correction — R0 MUST

The learner shall be able to correct the active goal/topic/resources when ARIA's assumed context is incorrect.

## UR-CTX-006 — Context isolation — R0 MUST

Context-specific evidence shall not silently contaminate unrelated contexts.

## UR-CTX-007 — Cross-context reuse — LATER RELEASE

Cross-context evidence reuse may be introduced when multiple-goal/context support exists and provenance/confidence rules are mature enough.

---

# 9. Deadline & Time-Constraint Requirements

Deadlines are important to the complete ARIA product but are not necessary to prove R0 adaptive learning unless the chosen validation scenario specifically requires one.

## UR-DEAD-001 — Optional deadlines — LONG-TERM MUST

A goal may have zero, one, or multiple relevant dates/events.

## UR-DEAD-002 — Deadlines belong to context — LONG-TERM MUST

Dates shall attach to the appropriate goal/event rather than becoming a universal learner deadline.

## UR-DEAD-003 — Deadline modification — LONG-TERM MUST

Learners shall eventually be able to add/edit/remove deadlines.

## UR-DEAD-004 — Time-to-goal awareness — R3+

Planner/recommendation systems may consider remaining time when scheduling is introduced.

## UR-DEAD-005 — Temporary time constraints — R3/R4+

Requests such as "I have 20 minutes" or "my exam starts soon" should eventually influence current recommendations/audio/revision without necessarily becoming permanent preferences.

## UR-DEAD-006 — Conflicting deadlines — R3+

Cross-goal deadline conflict resolution belongs to learning coordination.

---

# 10. Preference Requirements

## UR-PREF-001 — Explicit study preferences — SHOULD

The learner may set supported preferences such as explanation depth or hints before solutions. R0 should expose only preferences that materially affect its validation loop.

Notification, audio, and planner-specific preferences belong with those later systems.

## UR-PREF-002 — Global vs contextual preferences — LONG-TERM MUST

ARIA shall distinguish global and context-specific preferences where necessary.

## UR-PREF-003 — Editable preferences — LONG-TERM MUST

Explicit preferences shall remain editable.

## UR-PREF-004 — Inferred preferences — LATER RELEASE

ARIA may infer interaction preferences from repeated behaviour, but inferred preferences are not immutable facts.

## UR-PREF-005 — Preference correction — LONG-TERM MUST

Important inferred preferences shall be correctable/removable when inference exists.

## UR-PREF-006 — No rigid learning-style labeling — R0 MUST

ARIA shall not permanently classify a learner using simplistic learning-style labels and then constrain teaching to that label.

---

# 11. Returning-User Continuity Requirements

## UR-CONT-001 — Resume R0 learning — R0 MUST

A returning learner shall be able to resume the validation learning context without reconstructing the entire loop manually.

## UR-CONT-002 — Recent context — SHOULD

ARIA may surface recent relevant validation activity. Rich Home/recommendation surfaces belong later.

## UR-CONT-003 — Longitudinal state — PARTIAL R0 / R2+

R0 shall persist the evidence and basic learner_concept_state needed across repeated validation cycles.

Rich revision history, longitudinal mastery modeling, Roadmap progress, and mature learner-model history belong to later releases.

## UR-CONT-004 — Session independence — R0 MUST

Closing a browser/app session shall not erase persisted R0 learning state.

## UR-CONT-005 — Re-entry recommendation — LATER RELEASE

A richer "Where was I?" experience belongs to later Home/coordination capabilities.

---

# 12. Context-Switching Requirements

## UR-SWITCH-001 — Switch active goal — LATER RELEASE

Multiple active-goal switching is not required for R0.

## UR-SWITCH-002 — Preserve per-goal state — LONG-TERM MUST

When multiple goals exist, switching shall preserve relevant state for each.

## UR-SWITCH-003 — Clear active context — R0 MUST

ARIA shall make the active validation context clear when an action could otherwise be attributed incorrectly.

## UR-SWITCH-004 — Cross-goal actions — R3+

Global planning/Home recommendations that intentionally combine goals belong to learning coordination.

## UR-SWITCH-005 — Exploratory context — LATER RELEASE

Temporary study outside formal goals can be introduced after the evidence/context model is stable.

---

# 13. Inference & User-Control Requirements

## UR-INF-001 — Explicit vs inferred data — R0 MUST

Where relevant, ARIA shall distinguish learner-provided information from system inference.

## UR-INF-002 — Confidence/uncertainty — R0 MUST

Important inferred learner-state information shall support a confidence or equivalent uncertainty mechanism.

## UR-INF-003 — Evidence provenance — R0 MUST

Learner-state inferences shall retain links to supporting evidence.

## UR-INF-004 — User correction — R0 MUST

The learner shall be able to correct important inaccurate assumptions where correction is meaningful in the R0 flow.

## UR-INF-005 — No single-signal overreaction — R0 MUST

ARIA shall not make unsupported high-confidence learner-state conclusions from one weak signal alone.

## UR-INF-006 — Temporary context vs persistent memory — LONG-TERM MUST

Temporary instructions shall not automatically become permanent preferences/memory.

## UR-INF-007 — Consequential inference review — PARTIAL R0 / LATER

R0 adaptations shall be explainable/testable. Later Roadmap/Planner changes require stronger learner review/approval controls.

---

# 14. Goal & Context Lifecycle Requirements

Full goal lifecycle is useful product functionality but not required to prove R0.

## UR-STATE-001 — Goal states — LATER RELEASE

Long-term states may include Draft/New, Active, Paused, Completed, and Archived.

## UR-STATE-002 — Pause without data loss — LATER RELEASE

## UR-STATE-003 — Resume paused goal — LATER RELEASE

## UR-STATE-004 — Complete goal — LATER RELEASE

## UR-STATE-005 — Archive goal — LATER RELEASE

## UR-STATE-006 — Delete goal/data — LONG-TERM MUST

Deletion behaviour must be explicitly defined by privacy/data requirements. Basic account/data deletion obligations are not waived merely because richer lifecycle UI is deferred.

---

# 15. R0 Example — One Concrete Context

This is illustrative, not a final selection of the Gate A/Gate B validation context.

```text
Learner
  ↓
Goal/context: University DBMS learning
  ↓
Topic: Transactions
  ↓
Resources: lecturer PDF / notes
  ↓
Study
  ↓
Assessment
  ↓
Evaluation
  ↓
Evidence: concept-level result
  ↓
Basic learner_concept_state
  ↓
Adapted Study: targeted serializability explanation/practice
  ↓
Reassessment
```

R0 does not need GATE + FastAPI + DBMS + AWS contexts running simultaneously to validate this mechanism.

---

# 16. Long-Term Example — One Learner, Multiple Contexts

```text
Learner
│
├── Goal: GATE CSE
│   └── exam-specific resources / assessment / progress
├── Goal: Learn FastAPI
│   └── project-oriented resources / assessment / progress
└── Goal: University DBMS Exam
    └── syllabus / notes / theory assessment / revision
```

The learner remains one person, but context-specific rules are not interchangeable.

This illustrates the eventual product model rather than R0 implementation scope.

---

# 17. Context Precedence

When multiple sources of context conflict, ARIA should generally prioritize:

```text
Current explicit user instruction
            ↓
Explicit active goal/activity configuration
            ↓
Relevant saved context-specific preference
            ↓
Relevant global explicit preference
            ↓
High-confidence inferred context
            ↓
Low-confidence inference / default
```

R0 should implement only the levels it actually supports, while preserving the principle that explicit current instruction outranks weaker inference.

---

# 18. R0 Requirement Summary

R0 user/context requirements are intentionally small:

```text
Persistent learner identity
        ↓
One validation goal/context
        ↓
Selected resources/topic
        ↓
Context preserved through Study + Assessment
        ↓
Evidence attributed correctly
        ↓
Basic learner_concept_state persists
        ↓
Adaptation uses the correct context
        ↓
Second cycle can occur
```

R0 does **not** require multiple simultaneous goals, cross-goal scheduling, full goal lifecycle, universal domain support, rich Roadmaps/Plans, or sophisticated cross-context reuse.

---

# 19. Requirements Summary — Complete Product

Long-term ARIA should support:

- persistent learner identity;
- multiple goals and independent learning contexts;
- open-ended and deadline-driven goals;
- lightweight onboarding;
- progressive context collection;
- global/context-specific preferences;
- persistent continuity;
- safe context switching;
- context propagation across connected systems;
- context isolation;
- careful evidence reuse;
- explicit vs inferred information;
- uncertainty/provenance;
- learner correction;
- goal lifecycle;
- later multi-goal planning/coordination.

These are product-model requirements, not a statement that every capability belongs in R0.

---

# 20. Step 2 Completion

**Step 2 — User & Learning-Context Requirements has been reviewed and realigned.**

The audit changed the old assumption that multiple simultaneous goals and the complete context model must exist in the first release. The long-term model is preserved while R0 now requires only the learner/context capabilities needed to run and repeat the adaptive-learning validation loop.

Next:

# Step 3 — Functional Requirements Audit

Step 3 must preserve the complete ARIA feature requirements while explicitly distinguishing R0 implementation requirements from R1+ and long-term product requirements.
---

## Next

Step 3 — Functional Requirements.
