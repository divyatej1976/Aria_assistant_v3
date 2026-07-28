# ARIA — Phase 0 Research

## 06 — Build Stages & Scope Sequencing

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 0 — Research  
**Status:** Step 6 — Complete  
**Basis:** Steps 1–5 and the complete ARIA feature scope

---

# 1. Purpose

ARIA's complete product scope is intentionally large. Step 6 does not reduce that vision into a smaller product. It answers a different question:

> **In what order should ARIA's systems be built so that later capabilities depend on stable foundations rather than forcing architectural rewrites?**

The sequencing principle is:

```text
Product behaviour
      ↓
Data contracts
      ↓
Deterministic services
      ↓
AI capabilities
      ↓
Agent boundaries
      ↓
Cross-system orchestration
```

ARIA should not begin by creating many agents and only later deciding how they work together.

---

# 2. Dependency Types

Two dependency types must remain distinct.

## Hard dependency

Feature B cannot meaningfully operate without Feature A.

Example:

```text
Email Reminder
requires
User Account + Email + Notification Delivery
```

## Intelligence dependency

Feature B can exist without Feature A, but becomes substantially smarter once A exists.

Example:

```text
Basic Exam Generation
DOES NOT require Learner Model

Adaptive Exam Recommendation
benefits from Learner Model + Evidence
```

This distinction prevents unnecessary blocking during development.

---

# 3. High-Level Dependency Graph

```text
                   ENGINEERING FOUNDATION
                            ↓
                    AUTH + USER PROFILE
                            ↓
                         GOALS
                            ↓
                 ┌──────────┴──────────┐
                 ↓                     ↓
             RESOURCES              CORE DATA
                 │                     │
        ┌────────┼────────┐            │
        ↓        ↓        ↓            │
      STUDY    NOTES   ASSESSMENTS ←───┘
        │        │        │
        └────────┼────────┘
                 ↓
             EVALUATION
                 ↓
              EVIDENCE
                 ↓
           LEARNER MODEL
        ┌────────┼──────────┐
        ↓        ↓          ↓
   ROADMAPS   REVISION   PROGRESS
        ↓        │          │
     PLANNER     │          │
        └────────┼──────────┘
                 ↓
          RECOMMENDATIONS
                 ↓
                HOME
                 │
                 ↓
               AUDIO
                 ↓
      CROSS-SYSTEM AUTOMATION
                 ↓
       PRODUCTION HARDENING
```

This graph shows the main dependency direction, not every possible interaction.

---

# 4. Dependency Audit

## Authentication

**Hard dependencies:** Engineering foundation, database.

**Used by:** Every persistent personalized feature.

ARIA needs identity before it can reliably associate goals, resources, conversations, notes, assessments, roadmaps, plans, progress, memory, or reminders with a learner.

---

## Goals

**Hard dependencies:** User identity and core data model.

**Used by:** Roadmaps, planner, resources, assessments, progress, recommendations, Home.

Goals provide the context for what the learner is trying to accomplish.

---

## Resources

**Hard dependencies:** User identity, storage, metadata model.

**Used by:** Study, Notes, Exams, Audio, Roadmaps.

**Intelligence dependencies:** Retrieval/search, source parsing, provenance.

Resources should be available early because several later experiences consume them.

---

## Study

**Hard dependencies:** User identity, conversation storage, AI provider layer.

**Optional dependencies:** Goals, Resources.

**Intelligence dependencies:** Learner Model, Memory, Evidence, Recommendations.

Study can exist before sophisticated personalization. It becomes adaptive later.

---

## Notes

**Hard dependencies:** User identity, note storage.

**Optional inputs:** Study, Resources.

**Used by:** Study, Exams, Audio, Search, Revision.

Notes can be implemented after Study/Resources so generated notes immediately have useful source contexts.

---

## Assessment Engine

**Hard dependencies:** User identity, Exam Specification, question-generation capability, assessment storage, appropriate renderer/evaluation contracts.

**Optional inputs:** Goals, Topics, Resources, Notes.

**Intelligence dependencies:** Learner Model, Evidence, Roadmaps.

A learner must be able to configure the assessment format explicitly. Basic assessment generation does not require ARIA to infer the format from the learner profile.

---

## Evaluation Engine

**Hard dependencies:** Completed assessment/response data and format-specific evaluation logic.

**Used by:** Evidence, Progress, Misconception Tracking, Revision, Roadmap adaptation.

Generation and evaluation remain separate responsibilities.

---

## Evidence Engine

**Hard dependencies:** Events or interactions capable of producing learning evidence.

High-quality initial evidence comes from assessments, retrieval, viva, teach-back, and other observable learning behaviours.

**Used by:** Learner Model, Misconception Tracking, Progress, Roadmaps, Revision, Recommendations.

---

## Learner Model

**Hard dependencies:** User identity and structured learner-state schema.

**Intelligence dependency:** Evidence Engine. The model technically can exist earlier, but meaningful knowledge estimates should be grounded in evidence.

**Used by:** Adaptive Study, Living Roadmaps, Revision, Progress, Recommendations, Adaptive Audio, intelligent Home.

---

## Misconception Tracking

**Hard dependencies:** Evidence + Evaluation.

**Used by:** Study, Revision, Assessments, Progress, Recommendations.

A single wrong answer should not automatically create a confirmed misconception. Confidence and repeated/strong evidence are required.

---

## Roadmaps

**Hard dependencies:** User + Goal + roadmap data model.

**Optional dependencies:** Resources.

**Intelligence dependencies:** Learner Model, Evidence, prerequisite detection.

Basic personalized roadmap generation can exist before evidence-driven adaptation. Living roadmaps require learner-state signals.

---

## Planner

**Hard dependencies:** User, goals or actionable learning work, time/schedule model.

**Strong dependency:** Roadmaps for roadmap-driven scheduling.

**Intelligence dependencies:** Learner Model, Revision, priority logic.

**Used by:** Home, Notifications, plan recovery, Recommendations.

---

## Automatic Plan Recovery

**Hard dependencies:** Planner, scheduled work, deadlines/constraints, missed-session detection.

**Intelligence dependencies:** Roadmap priorities, prerequisites, learner state.

---

## Revision Engine

**Hard dependencies:** Concepts/topics plus revision history and scheduling logic.

**Strong intelligence dependencies:** Evidence, Learner Model, assessment history.

**Used by:** Planner, Notifications, Progress, Recommendations, Adaptive Audio.

---

## Progress

**Hard dependencies:** Goals/topics and meaningful activity/progress data.

**Intelligence dependencies:** Evidence, Learner Model, assessments, revision.

Progress should not equate time spent with learning mastery.

---

## Recommendation Engine

**Hard dependencies:** Enough learner/system state to recommend an actionable next step.

**Strong dependencies:** Goals, Learner Model, Roadmaps, Planner, Revision, Assessments.

**Used by:** Home and proactive learning guidance.

---

## Home

A basic Home can exist early, but an **intelligent Home** depends on several systems.

**Inputs:** Goals, Planner, Progress, Revision, Recommendations, upcoming assessments, recent activity.

Therefore sophisticated Home intelligence should not be built before the underlying state exists.

---

## Audio

### Source Audio

**Hard dependencies:** Audio generation capability + source material.

Can be built relatively independently.

### Adaptive Audio

**Strong dependencies:** Learner Model, Evidence, Revision, goals/exams, available-time context.

Adaptive audio should be built after these systems so it can do more than narrate documents.

---

## Notifications

**Hard dependencies:** User identity and notification delivery infrastructure.

### Email reminders additionally require

- verified/usable email;
- user notification preferences;
- triggering event or scheduled reminder.

**Inputs may come from:** Planner, Revision, Assessments, Roadmaps, deadlines, plan recovery.

---

## Cross-System Automation

**Hard dependencies:** Stable feature contracts and events.

Examples include:

```text
ExamCompleted
StudySessionCompleted
RevisionCompleted
RoadmapChanged
PlannedSessionMissed
GoalUpdated
```

Full automation should be introduced after individual systems work reliably in isolation.

---

# 5. Validated Build Sequence

The dependency audit supports the following sequence.

## Stage 0 — Engineering Foundation

Build:

- repository/project structure;
- frontend/backend skeleton;
- environments;
- configuration and secrets handling;
- database connection;
- migrations;
- API conventions;
- logging;
- baseline error handling;
- testing infrastructure;
- basic CI;
- AI-provider abstraction where appropriate.

**Checkpoint:** ARIA has a stable engineering skeleton.

---

# 6. Stage 1 — Identity + Core Domain Model

Build:

- Sign up;
- Sign in;
- Email verification;
- Password reset/recovery;
- Session management;
- User/profile;
- Lightweight onboarding;
- Goal model;
- Topic/concept primitives;
- learning-context primitives;
- initial preferences.

**Checkpoint:** ARIA knows who the learner is and can persist what they are trying to achieve.

---

# 7. Stage 2 — Resources + Retrieval

Build:

- resource upload/addition;
- file storage;
- resource metadata;
- parsing/extraction;
- chunking where required;
- retrieval/search;
- source provenance;
- goal/topic/resource relationships;
- URL/resource support as feasible.

**Checkpoint:** ARIA can ingest and retrieve learner material.

---

# 8. Stage 3 — Study

Build:

- conversations;
- conversation history;
- goal/topic context;
- resource-grounded answers;
- source citations/provenance;
- Tutor behaviour;
- Guided Learning;
- Socratic interaction;
- Teach ARIA foundation;
- Rapid Revision behaviour.

**Checkpoint:** A learner can bring a goal/resource to ARIA and meaningfully study from it.

This is the first major end-to-end usable learning experience.

---

# 9. Stage 4 — Notes

Build:

- manual notes;
- editing;
- organization;
- Study → Notes;
- Resource → Notes;
- summaries;
- concise/detailed transformations;
- revision sheets;
- source linking;
- search integration.

**Checkpoint:** Knowledge created during learning becomes reusable rather than disappearing inside chats.

---

# 10. Stage 5 — Assessment + Evaluation

Build the configurable Assessment Engine.

## Assessment foundation

- Exam Specification;
- user-controlled exam configuration;
- natural-language configuration assistance;
- specification preview/editing;
- dynamic exam cards;
- assessment persistence;
- timers;
- scoring rules;
- question-generation contracts.

## Renderers / formats

Introduce formats progressively while preserving an extensible specification:

- MCQ;
- multiple-select;
- numerical answer;
- true/false;
- fill-in-the-blank;
- short answer;
- long answer;
- conceptual/application questions;
- mixed sections;
- viva / oral;
- teach-back;
- coding assessment/contest when execution infrastructure is ready.

## Evaluation

- format-specific evaluation;
- topic-level results;
- reasoning/coverage analysis where appropriate;
- feedback;
- structured evaluation output.

**Checkpoint:** ARIA can test learners in a format they choose and produce structured learning results.

---

# 11. Stage 6 — Evidence + Learner Model

Build:

- evidence schema;
- evidence strength/confidence;
- assessment evidence ingestion;
- retrieval evidence;
- teach-back/viva evidence;
- careful study-signal ingestion;
- learner knowledge state;
- strengths/weaknesses;
- possible misconception detection;
- prerequisite-gap detection;
- learner-state correction controls;
- persistent learning preferences/memory boundaries.

**Checkpoint:** ARIA begins to understand the learner from evidence rather than only remembering conversations.

---

# 12. Stage 7 — Living Roadmaps

Build:

- goal → roadmap generation;
- phases/topics/subtopics;
- prerequisites;
- dependencies;
- milestones;
- resource attachment;
- progress;
- roadmap history;
- evidence-aware adaptation;
- proposed changes;
- reasons/explanations;
- accept/modify/reject controls.

**Checkpoint:** ARIA can guide a learning journey and adapt the path when evidence justifies it.

---

# 13. Stage 8 — Planner + Revision + Notifications

Build:

## Planner

- availability;
- multiple goals;
- roadmap scheduling;
- deadlines;
- study sessions;
- revision sessions;
- assessment scheduling;
- day/week/calendar views;
- rescheduling;
- missed-session detection;
- automatic recovery proposals.

## Revision

- deterministic revision scheduling;
- retrieval sessions;
- targeted revision from evidence;
- revision history;
- multiple retrieval formats.

## Notifications

- in-app notifications;
- email reminder delivery;
- user notification preferences;
- reminder timing/frequency;
- planner/revision/exam/deadline triggers.

**Checkpoint:** ARIA can turn a roadmap into a realistic learning schedule and help the learner stay on course.

---

# 14. Stage 9 — Progress + Recommendations + Intelligent Home

Build:

## Progress

- goal progress;
- roadmap progress;
- knowledge map;
- assessment history;
- misconception state;
- revision health;
- improvement over time;
- readiness estimates with uncertainty.

## Recommendations

- next-best learning action;
- reason for recommendation;
- review prerequisite;
- take assessment;
- revise concept;
- continue roadmap;
- review plan change.

## Intelligent Home

Surface:

- what to do now;
- today's plan;
- due revision;
- active goals;
- upcoming assessments;
- deadlines;
- progress;
- weak areas;
- recommendations;
- important proposed changes.

**Checkpoint:** ARIA can answer, "What should I do next, and why?"

---

# 15. Stage 10 — Audio Learning

Build:

## Source Audio

- resource → audio;
- notes → audio;
- study content → audio;
- selectable style/length where supported.

## Adaptive Audio

Use:

- goal/exam context;
- learner state;
- weak concepts;
- misconceptions;
- revision history;
- available time;
- topic priority.

Example:

> "I have 15 minutes before my exam. Revise me."

## Later interactive audio

- spoken questions;
- learner responses;
- retrieval evaluation;
- adaptive continuation.

**Checkpoint:** Audio becomes part of ARIA's learning loop rather than a standalone media generator.

---

# 16. Stage 11 — Full Cross-System Automation

Once feature contracts are stable, connect them through structured events/workflows.

Example:

```text
ExamCompleted
      ↓
Evaluation
      ↓
Evidence
      ↓
Learner Model
      ↓
Misconceptions / prerequisites
      ↓
Progress
      ↓
Revision
      ↓
Roadmap adaptation check
      ↓
Planner adaptation check
      ↓
Recommendations
      ↓
Home
```

Build:

- event contracts;
- orchestration workflows;
- idempotency;
- workflow state;
- human approvals;
- retries/fallbacks;
- cross-system validation;
- auditability.

**Checkpoint:** ARIA behaves as one connected Learning OS rather than a set of adjacent features.

---

# 17. Stage 12 — Production Hardening

Production hardening happens throughout development, but this stage performs the full-system pass.

Focus on:

- hallucination mitigation;
- structured-output validation;
- document parsing failures;
- workflow failures;
- conflicting updates;
- duplicate events;
- retries;
- fallback behaviour;
- security;
- privacy;
- authorization;
- data deletion/export;
- performance;
- latency;
- AI cost management;
- caching;
- concurrency;
- accessibility;
- observability;
- integration testing;
- agent/workflow testing;
- user testing;
- load and failure testing.

**Checkpoint:** ARIA is reliable enough to operate as an interconnected production system.

---

# 18. Build Checkpoints

The sequence intentionally produces useful checkpoints rather than waiting for the complete system before ARIA works.

```text
Foundation
    ↓
ARIA can identify and persist learners
    ↓
ARIA can understand learner resources
    ↓
ARIA can teach
    ↓
ARIA can preserve learning as notes
    ↓
ARIA can test
    ↓
ARIA can interpret learning evidence
    ↓
ARIA can adapt learning roadmaps
    ↓
ARIA can schedule and revise
    ↓
ARIA can show progress and recommend next actions
    ↓
ARIA can provide adaptive audio revision
    ↓
ARIA can coordinate the entire learning workflow
```

---

# 19. What Should NOT Be Built First

## Do not build every agent first

Agent names are not architecture.

The product workflows and data contracts should determine which capabilities later deserve agent boundaries.

## Do not build an intelligent dashboard before the intelligence exists

Hardcoded progress cards create the appearance of personalization without underlying evidence.

## Do not build a sophisticated Learner Model without evidence

Assessment and observable learning behaviour should feed it.

## Do not tightly couple features

Exam completion should emit a structured event rather than directly modifying every downstream subsystem.

## Do not make every operation an LLM call

Authentication, database operations, deterministic scheduling, calculations, permissions, notification delivery, and other reliable operations belong in normal software services.

## Do not hardcode learning domains

The architecture must not assume DSA, AWS, GATE, university subjects, or any particular goal.

---

# 20. Architecture Implications Discovered During Step 6

The dependency audit reveals several requirements for later phases.

### Shared domain entities must be designed carefully

Goal, Topic/Concept, Resource, Evidence, Assessment, Roadmap, Plan, Revision, and Learner State become shared contracts across many systems.

### Assessment must remain renderer-driven

The Exam Specification should determine the assessment experience so ARIA can support very different formats without creating separate products.

### Evidence should be append-oriented and traceable

Downstream learner-state conclusions should retain links to the evidence that produced them.

### Adaptation should usually be proposal-based

Significant roadmap or planner changes should support human review.

### Events should connect mature systems

Cross-feature automation should not require each subsystem to know every other subsystem directly.

### Memory and Learner Model must remain distinct

Conversational/personal preferences and evidence-backed learning state have different semantics and confidence requirements.

### Deterministic logic and AI must coexist

ARIA is an AI-first product, not an LLM-only product.

---

# 21. Final Dependency Validation

The sequence passes the dependency audit:

```text
Stage 0  Foundation
          ↓
Stage 1  Identity + Core Domain
          ↓
Stage 2  Resources + Retrieval
          ↓
Stage 3  Study
          ↓
Stage 4  Notes
          ↓
Stage 5  Assessment + Evaluation
          ↓
Stage 6  Evidence + Learner Model
          ↓
Stage 7  Living Roadmaps
          ↓
Stage 8  Planner + Revision + Notifications
          ↓
Stage 9  Progress + Recommendations + Home
          ↓
Stage 10 Audio
          ↓
Stage 11 Cross-System Automation
          ↓
Stage 12 Production Hardening
```

No major system in this sequence requires a later stage in order to provide its basic functionality.

Several systems become progressively more intelligent as later dependencies become available. This is intentional.

---

# 22. Step 6 Conclusion

ARIA should be built **foundation-first and intelligence progressively**.

The sequence begins with identity, goals, resources, and basic learning experiences. It then introduces assessment, which provides stronger learning evidence. Evidence enables the Learner Model. The Learner Model makes roadmaps, revision, planning, progress, recommendations, and adaptive audio increasingly intelligent. Only after these systems have stable contracts should ARIA connect them through full cross-system orchestration.

This preserves the complete ARIA vision while making implementation understandable, testable, and maintainable.

---

# 23. Next Phase 0 Step

**Step 7 — Final `VISION.md`**

Step 7 should consolidate the decisions from all Phase 0 research documents into ARIA's canonical product vision.

It should capture:

- what ARIA is;
- the problem it solves;
- target users;
- product philosophy;
- complete product systems;
- differentiation;
- core learning loop;
- product boundaries;
- high-level build direction;
- success definition;
- principles that later PRD and architecture work must preserve.

After `VISION.md` is finalized, **Phase 0 — Product Vision is complete**, and ARIA can move into **Phase 1 — PRD**.