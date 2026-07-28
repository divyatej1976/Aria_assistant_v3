# ARIA — Phase 1 PRD

## Step 2 — User & Learning-Context Requirements

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Step 2 — Complete  
**Primary sources:** `VISION.md`, `01-product-overview-goals.md`

---

# 1. Purpose

This document defines what ARIA must know about a learner, how learning contexts should be represented, and how learner identity, goals, deadlines, preferences, and inferred information should behave across the product.

ARIA is intended to support the same person across multiple learning situations without forcing them into one permanent learner category.

The central requirement is:

> **One learner identity may contain many goals and learning contexts, while each context preserves the information relevant to that goal.**

---

# 2. User Model

ARIA should model a person as a persistent learner rather than as a single exam candidate, student type, or subject-specific user.

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
├── Goal C
│   └── Learning Context C
└── Cross-goal learning history where appropriate
```

The product must not permanently classify the learner as only:

- a university student;
- a competitive-exam candidate;
- a coding learner;
- a certification learner;
- an interview candidate;
- a self-directed learner.

Those are situations a learner may enter, leave, or combine.

---

# 3. User Requirement Categories

Requirements in this document use the following identifiers:

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

## UR-ID-001 — Persistent learner identity

ARIA shall associate persistent learning data with an authenticated learner identity.

Relevant persistent data may include goals, learning contexts, resources, conversations, notes, assessments, roadmaps, plans, revision history, progress, learner-model state, and preferences.

## UR-ID-002 — Identity is broader than a learning goal

The learner account shall remain stable when goals are created, completed, paused, archived, or deleted.

## UR-ID-003 — Global and context-specific information

ARIA shall distinguish information that applies globally to the learner from information that applies only to a specific goal or learning context.

Example:

```text
Global:
"Prefer concise explanations first."

Context-specific:
"For this university exam, answers should follow the uploaded syllabus."
```

## UR-ID-004 — Cross-context leakage prevention

ARIA shall avoid applying context-specific information to unrelated goals unless the information is intentionally shared or reasonably global.

Example:

A preferred GATE assessment format should not automatically become the format for a university theory exam.

---

# 5. Onboarding Requirements

## UR-ONB-001 — Lightweight onboarding

Initial onboarding shall request only information necessary to begin using ARIA effectively.

ARIA shall not require the learner to provide every subject, deadline, exam, schedule, preference, or future goal before entering the product.

## UR-ONB-002 — No mandatory universal deadline

Onboarding shall not assume every learner has one deadline or examination date.

Deadlines belong to goals/events where relevant.

## UR-ONB-003 — Broad starting intent

ARIA may ask the learner what they currently want help with or allow them to create an initial goal.

Examples may include learning a topic, preparing for an exam, preparing for an interview, completing a certification, or creating another custom goal.

These examples must not constrain the domain model.

## UR-ONB-004 — Optional initial preferences

ARIA may collect a small set of immediately useful preferences, but preferences should remain editable and should continue to evolve through explicit user choices and later evidence.

## UR-ONB-005 — Progressive discovery

Information not required during onboarding should be collected later when it becomes relevant to a feature or goal.

Example:

A deadline can be requested when a learner creates a time-bound goal or asks ARIA to build a schedule.

## UR-ONB-006 — Product guidance

ARIA should introduce major capabilities progressively through contextual guidance rather than forcing the learner through a long feature questionnaire during signup.

---

# 6. Goal Requirements

## UR-GOAL-001 — Create goals

The learner shall be able to create learning goals.

A goal represents an outcome the learner is trying to achieve.

Examples:

```text
Prepare for GATE CSE
Learn FastAPI
Pass a DBMS semester exam
Prepare for a Java interview
Complete an AWS certification
Learn linear algebra
```

These examples are illustrative and must not be hardcoded categories.

## UR-GOAL-002 — Custom goal language

Learners shall be able to describe goals in their own words rather than selecting only from predefined categories.

## UR-GOAL-003 — Goal metadata

A goal may contain relevant metadata such as:

- title;
- description;
- desired outcome;
- target/deadline if applicable;
- priority;
- status;
- related resources;
- roadmap;
- plan;
- assessment context.

Not every field shall be mandatory.

## UR-GOAL-004 — Goals without deadlines

ARIA shall support open-ended goals with no deadline.

## UR-GOAL-005 — Goal refinement

A learner shall be able to modify a goal as their intention changes.

## UR-GOAL-006 — Goal hierarchy / decomposition

ARIA should support decomposition of broad goals into phases, milestones, topics, or subgoals without requiring the learner to manually create every component.

## UR-GOAL-007 — Goal source

A goal may originate from explicit user creation or from an ARIA suggestion that the learner confirms.

ARIA shall not silently create consequential long-term goals from casual conversation without appropriate confirmation.

---

# 7. Multiple-Goal Requirements

## UR-MULTI-001 — Multiple simultaneous goals

ARIA shall support multiple active learning goals for one learner.

## UR-MULTI-002 — Independent contexts

Each goal shall be capable of maintaining its own resources, roadmap, assessment configuration, progress, deadlines, and relevant learning state.

## UR-MULTI-003 — Shared learner identity

Multiple goals shall remain connected to the same learner identity so appropriate global preferences and reusable learning information can persist.

## UR-MULTI-004 — Priority

The learner shall be able to indicate or modify goal priority.

ARIA may recommend priority changes based on deadlines, workload, or learner state, but meaningful reprioritization should remain visible to the learner.

## UR-MULTI-005 — Scheduling conflicts

When multiple goals compete for limited learner time, ARIA should be capable of identifying conflicts and proposing a feasible allocation rather than independently over-scheduling each goal.

## UR-MULTI-006 — Goal-specific progress

Progress for one goal shall not be incorrectly interpreted as progress toward another goal merely because topics overlap.

Where concepts genuinely overlap, ARIA may reuse evidence carefully while preserving provenance and context.

---

# 8. Learning Context Requirements

A **Learning Context** represents the active information surrounding a learning activity.

A context may include:

```text
Learning Context
│
├── Learner
├── Goal
├── Topic / Concept
├── Resources
├── Current activity
├── Relevant conversation/history
├── Assessment context
├── Roadmap state
├── Plan state
├── Learner-state evidence
├── Relevant preferences
└── Time / deadline constraints
```

## UR-CTX-001 — Context association

Study sessions, assessments, notes, resources, roadmap activities, and revision sessions should be capable of being associated with a goal and/or topic where relevant.

## UR-CTX-002 — Context is not always mandatory

ARIA shall still support exploratory learning that is not yet attached to a formal goal.

The learner may later attach useful content to a goal.

## UR-CTX-003 — Context propagation

When the learner moves between connected features, relevant context should be carried forward where appropriate.

Example:

```text
Study DBMS Transactions
        ↓
Generate Notes
        ↓
Generate Assessment
```

The learner should not need to reselect DBMS Transactions and the same resources at every step unless they want to change them.

## UR-CTX-004 — Context visibility

The interface should make the active goal/topic/context understandable where confusion could cause incorrect actions.

## UR-CTX-005 — Context modification

The learner shall be able to change the active goal/topic/resources when ARIA's assumed context is incorrect.

## UR-CTX-006 — Context isolation

Information specific to one learning context shall not silently contaminate unrelated contexts.

## UR-CTX-007 — Cross-context reuse

ARIA may reuse relevant knowledge across contexts when there is a justified relationship.

Example:

A learner's demonstrated understanding of SQL joins may be relevant to multiple database-related goals.

The reused evidence should retain its original provenance.

---

# 9. Deadline & Time-Constraint Requirements

## UR-DEAD-001 — Optional deadlines

A goal may have zero, one, or multiple relevant dates/events depending on its structure.

## UR-DEAD-002 — Deadlines belong to context

ARIA shall associate deadlines with the appropriate goal, exam, milestone, assessment, or learning event rather than treating one date as the learner's universal deadline.

## UR-DEAD-003 — Deadline modification

Learners shall be able to add, edit, or remove deadlines.

## UR-DEAD-004 — Time-to-goal awareness

Planner and recommendation systems should be capable of considering remaining time when a deadline exists.

## UR-DEAD-005 — Short-time learning requests

ARIA shall support immediate constraints such as:

> "I have 20 minutes."

or

> "My exam starts soon."

These temporary constraints should influence the current recommendation without necessarily becoming permanent learner preferences.

## UR-DEAD-006 — Conflicting deadlines

When multiple active goals have conflicting time demands, ARIA should surface the conflict and propose a prioritization or schedule adjustment.

---

# 10. Preference Requirements

## UR-PREF-001 — Explicit preferences

The learner shall be able to explicitly set relevant learning and product preferences.

Potential examples include:

- explanation depth;
- hints before solutions;
- concise vs detailed revision;
- notification preferences;
- preferred assessment defaults;
- audio preferences;
- accessibility preferences.

## UR-PREF-002 — Global vs contextual preferences

ARIA shall distinguish global preferences from context-specific preferences where necessary.

## UR-PREF-003 — Editable preferences

Learners shall be able to modify explicit preferences.

## UR-PREF-004 — Inferred preferences

ARIA may infer useful interaction preferences from repeated behaviour, but inferred preferences should not be treated as immutable facts.

## UR-PREF-005 — Preference correction

Learners should be able to correct or remove important inferred preferences.

## UR-PREF-006 — No rigid learning-style labeling

ARIA should not permanently classify a learner using simplistic learning-style categories and then constrain future teaching to that label.

Personalization should respond to actual behaviour, explicit preferences, context, and evidence.

---

# 11. Returning-User Continuity Requirements

## UR-CONT-001 — Resume learning

A returning learner should be able to resume relevant active learning without reconstructing the entire context manually.

## UR-CONT-002 — Recent context

ARIA should be capable of surfacing recent goals, sessions, resources, notes, assessments, and planned work where relevant.

## UR-CONT-003 — Longitudinal state

Learning evidence, revision history, roadmap progress, and learner-model state should persist across sessions according to data-retention and privacy rules.

## UR-CONT-004 — Session independence

Closing a browser/app session shall not erase persistent learning state.

## UR-CONT-005 — Re-entry recommendation

ARIA should eventually be able to answer:

> "Where was I?"

with a useful summary of recent learning state and next actions.

---

# 12. Context-Switching Requirements

## UR-SWITCH-001 — Switch active goal

The learner shall be able to switch between active goals without losing state.

## UR-SWITCH-002 — Preserve per-goal state

Switching goals shall preserve each goal's relevant roadmap position, resources, assessments, notes, progress, and plan state.

## UR-SWITCH-003 — Clear active context

ARIA should make the current goal/context visible when an action could otherwise be applied to the wrong goal.

## UR-SWITCH-004 — Cross-goal actions

Some actions, such as global planning or Home recommendations, may intentionally consider multiple goals at once.

The system shall distinguish these from single-goal actions.

## UR-SWITCH-005 — Exploratory context

The learner may temporarily study something outside an active goal without being forced to create a new goal immediately.

---

# 13. Inference & User-Control Requirements

ARIA will sometimes infer information. This must be controlled carefully.

## UR-INF-001 — Explicit vs inferred data

Where relevant, ARIA should internally distinguish information explicitly provided by the learner from information inferred by the system.

## UR-INF-002 — Confidence

Important inferred learner information should support a confidence representation or equivalent uncertainty mechanism.

## UR-INF-003 — Evidence provenance

Learning-state inferences should retain links to the evidence that influenced them where practical.

## UR-INF-004 — User correction

The learner shall be able to correct important inaccurate assumptions.

## UR-INF-005 — No single-signal overreaction

ARIA should not make major learner-state or roadmap conclusions from one weak signal alone.

## UR-INF-006 — Temporary context vs persistent memory

ARIA shall distinguish temporary statements from persistent preferences.

Example:

> "Explain this one quickly because I'm late."

should not necessarily become:

> "This learner always prefers short explanations."

## UR-INF-007 — Consequential inference review

When an inference would cause a significant roadmap, plan, or learning-state change, ARIA should support explanation and correction/review where appropriate.

---

# 14. Goal & Context Lifecycle Requirements

## UR-STATE-001 — Goal states

Goals should support lifecycle states such as:

```text
Draft / New
Active
Paused
Completed
Archived
```

Exact UI terminology may be decided later.

## UR-STATE-002 — Pause without data loss

Pausing a goal shall preserve its relevant learning state.

## UR-STATE-003 — Resume

A paused goal shall be resumable with prior context available.

## UR-STATE-004 — Complete

Completing a goal should preserve historical learning records unless the learner chooses deletion according to product data controls.

## UR-STATE-005 — Archive

The learner should be able to remove inactive goals from normal active views without necessarily deleting their history.

## UR-STATE-006 — Delete

Deletion behaviour must be explicitly defined in later privacy/data requirements, including what dependent data is deleted, detached, or retained.

---

# 15. Example: One Learner, Multiple Contexts

```text
Learner
│
├── Goal: GATE CSE
│   ├── Deadline: Exam date
│   ├── Roadmap
│   ├── OS / DBMS / CN resources
│   ├── MCQ + MSQ + NAT assessment preferences
│   ├── Progress
│   └── Revision schedule
│
├── Goal: Learn FastAPI
│   ├── No hard deadline
│   ├── Documentation + course resources
│   ├── Project-based roadmap
│   ├── Conceptual + coding assessment
│   └── Progress
│
└── Goal: University DBMS Exam
    ├── Deadline: Semester exam
    ├── Uploaded syllabus
    ├── Class notes
    ├── Theory-answer assessment format
    ├── Revision plan
    └── Progress
```

The learner is still one person.

But ARIA must not assume that the GATE assessment configuration, FastAPI roadmap, and university DBMS exam rules are interchangeable.

---

# 16. Example: Context Propagation

A learner opens their university DBMS goal and selects Unit 4 plus two uploaded resources.

```text
Goal: DBMS Semester Exam
Topic: Transactions
Resources: Unit 4 Notes + Lecturer PDF
            ↓
          Study
            ↓
       Generate Notes
            ↓
      Generate Exam
            ↓
         Evaluate
            ↓
          Evidence
```

The connected workflow should preserve the relevant context.

The learner may still override it at any point.

---

# 17. Example: Context Correction

Suppose ARIA assumes a conversation belongs to GATE CSE because the learner was previously studying operating systems.

The learner says:

> "No, this is for my university exam."

ARIA should be able to switch the active context and avoid storing subsequent context under the wrong goal.

This correction should not require recreating the conversation.

---

# 18. Example: Temporary Constraint

A learner normally prefers detailed explanations.

Before an exam they say:

> "I have 15 minutes. Only revise the important points."

ARIA should treat the 15-minute constraint and concise style as part of the current activity unless the learner explicitly chooses to make that a persistent preference.

---

# 19. Context Precedence

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

This precedence principle should guide later AI and orchestration requirements.

The exact implementation belongs to architecture phases.

---

# 20. Requirements Summary

Step 2 establishes that ARIA must support:

- one persistent learner identity;
- multiple simultaneous goals;
- open-ended and deadline-driven goals;
- goal-specific learning contexts;
- exploratory learning outside formal goals;
- lightweight onboarding;
- progressive context collection;
- global and context-specific preferences;
- persistent continuity across sessions;
- safe switching between goals;
- shared context across connected features;
- context isolation where required;
- careful cross-goal evidence reuse;
- explicit vs inferred information;
- uncertainty and provenance for important inferences;
- user correction of ARIA assumptions;
- temporary constraints that do not automatically become permanent preferences;
- goal pause/resume/completion/archive lifecycle;
- multiple-goal scheduling awareness.

---

# 21. Step 2 Completion

**Step 2 — User & Learning-Context Requirements is complete.**

Next:

# Step 3 — Functional Requirements

Step 3 will define detailed, numbered functional requirements for the major ARIA product systems:

```text
Authentication
Onboarding
Goals
Home
Study
Resources & Retrieval
Notes
Assessment
Evaluation
Roadmaps
Planner
Revision
Progress
Audio
Search
Notifications
Settings & User Controls
```

Evidence, Learner Model, Memory, misconceptions, prerequisite detection, AI behaviour, and related intelligence constraints will receive deeper treatment in Step 5, while Step 4 will specify how these product systems communicate and automate across feature boundaries.