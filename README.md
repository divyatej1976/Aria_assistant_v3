# ARIA — AI Learning Operating System

ARIA is a learner-controlled, context-aware AI learning system designed to coordinate the parts of studying that are usually fragmented across multiple tools.

Instead of forcing every learner into the same subjects, exam formats, resources, or roadmap, ARIA builds the learning environment around **what the learner is actually preparing for**.

## Product Vision

```text
Learner goal
    ↓
Personalized roadmap
    ↓
Resources + Study
    ↓
Notes + Revision
    ↓
Learner-configured Assessments
    ↓
Evaluation + Evidence
    ↓
Learner Model
    ↓
Progress + Recommendations
    ↓
Adaptive Roadmap + Planner
    ↓
Next Learning Action
    ↺
```

ARIA is intended to eventually coordinate learning in one place without trying to replace every specialized learning platform.

## Core Product Areas

- flexible learner-defined goals;
- personalized Home;
- resource ingestion and retrieval;
- AI study conversations;
- notes and revision material;
- learner-configured assessments;
- evaluation and structured learning evidence;
- evidence-backed Learner Model;
- misconception and prerequisite-gap detection;
- adaptive roadmaps;
- planning and missed-work recovery;
- progress and learning analytics;
- recommendations;
- notes/resources-to-audio learning;
- reminders and notifications;
- future external learning integrations.

## Progress, Consistency & Motivation

ARIA's Progress system includes both **learning progress** and **learning consistency**.

Consistency features include:

- meaningful learning days;
- calendar/contribution-style activity heatmap;
- current learning streak;
- longest streak;
- active-day summaries;
- consistency milestones;
- learning-achievement milestones.

A learner does **not** maintain a streak simply by opening ARIA or sending a trivial message. A day must contain a qualifying meaningful learning activity.

ARIA deliberately separates:

```text
Consistency → "Did I keep learning?"
Progress    → "Am I moving through my goal?"
Evidence    → "What did I demonstrate?"
Mastery     → "What does the evidence suggest I understand?"
```

Missing one day may reset a current streak, but it does not erase the learner's historical activity, longest streak, completed work, or learning progress.

Detailed requirements: `docs/phase-1-prd/progress-motivation-requirements.md`

## Product Principles

1. Learner goals and content are dynamic, not hardcoded around DSA, GATE, AWS, placements, or any single domain.
2. Assessment format is selected/configured according to the learner's need.
3. Memory is not mastery.
4. Exposure is not understanding.
5. One mistake is not automatically a misconception.
6. One correct answer is not automatically mastery.
7. No evidence is not weakness.
8. Activity is not mastery.
9. Important AI-driven adaptations remain explainable and learner-controlled.
10. Deterministic systems should handle deterministic work; AI is used where reasoning genuinely adds value.

## Development Phases

### Phase 0 — Product & Competitive Research

Research into learner problems, existing products, workflows, reviews, gaps, and ARIA's differentiation.

**Status: Complete**

### Phase 1 — Product Requirements Document

The Phase 1 PRD defines ARIA before implementation architecture is selected.

```text
01 — Product Overview & Goals
02 — User & Learning Context Requirements
03 — Functional Requirements
04 — Cross-System & Automation Requirements
05 — AI, Learner Model, Memory & Evidence Requirements
06 — Non-Functional, Privacy, Security, Reliability & Accessibility
07 — Scope, Prioritization & Release Boundaries
08 — Acceptance Criteria, Success Metrics & PRD Closure
```

**Status: Complete**

Additional approved Phase 1 requirement:

- `progress-motivation-requirements.md` — meaningful learning days, streaks, contribution heatmap, active-day summaries, milestones, and healthy gamification boundaries.

### Phase 2 — System Architecture & Technical Design

Planned sequence:

```text
01 — Architecture Drivers & Constraints
02 — System Context & Major Components
03 — Domain Model & Data Architecture
04 — AI / RAG / Memory / Learner Model Architecture
05 — Workflow / Event / Automation Architecture
06 — API & Integration Architecture
07 — Security / Privacy / Authorization Architecture
08 — Deployment / Observability / Reliability / Cost Architecture
09 — Architecture Decision Records
10 — R1 Implementation Blueprint
```

**Status: Next**

## Release Direction

ARIA's full vision will be built as increasingly complete learning loops rather than as disconnected features.

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

The first usable learning loop is:

```text
Create goal
   ↓
Add learning material
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

## Current Status

**Phase 0: Complete**  
**Phase 1: Complete**  
**Phase 2: Next — System Architecture & Technical Design**

ARIA's next major question is no longer what features the product should contain, but how to architect those requirements with the least unnecessary complexity while preserving the path toward the full product vision.