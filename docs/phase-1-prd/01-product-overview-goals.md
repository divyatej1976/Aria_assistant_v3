# ARIA — Phase 1 PRD

## Step 1 — Product Overview, Goals & Non-Goals

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Step 1 — Complete  
**Primary source:** `VISION.md`

---

# 1. Purpose of This Document

This document translates ARIA's Phase 0 product vision into PRD-level product goals and boundaries.

It establishes what ARIA must ultimately accomplish before later Phase 1 steps define detailed functional, AI, cross-system, reliability, and acceptance requirements.

This document intentionally does **not** choose frameworks, databases, APIs, agent frameworks, page layouts, or visual designs.

---

# 2. Product Overview

ARIA is an AI-powered learning operating system for goal-driven learners.

It brings studying, resources, notes, assessments, evaluation, revision, roadmaps, planning, progress, audio, reminders, search, and recommendations into one connected learning environment.

ARIA is designed around a persistent learner context rather than isolated feature sessions.

Its central product behaviour is:

```text
Goal
 ↓
Roadmap
 ↓
Plan
 ↓
Study
 ↓
Practice / Assessment
 ↓
Evaluation
 ↓
Evidence
 ↓
Learner Model
 ↓
Adaptation
 ↓
Revision / Next Action
 ↓
New Evidence
 ↓
↺
```

The product should reduce the learner's need to manually coordinate every part of this loop.

---

# 3. Problem Statement

Learners currently use many independent systems for different parts of learning.

Even when those systems are individually effective, context is fragmented across conversations, notes, documents, calendars, quizzes, roadmaps, course platforms, practice systems, and reminders.

The learner remains responsible for manually answering questions such as:

- What should I study next?
- What resources belong to this goal?
- What have I already covered?
- What have I actually understood?
- What am I weak at?
- Am I repeatedly misunderstanding a concept?
- What should I revise now?
- When should I revise again?
- Should my learning path change after this assessment?
- What happens to my plan if I miss today's work?
- How should I balance multiple goals?

ARIA's product problem is therefore not simply lack of AI-generated educational content.

> **The learning workflow itself is fragmented and requires excessive manual coordination.**

---

# 4. Product Objective

ARIA's primary objective is:

> **Reduce manual learning coordination while helping learners make meaningful progress toward their goals through a connected, adaptive, evidence-aware learning environment.**

ARIA should automate organizational work surrounding learning without removing the intellectual effort required to learn.

---

# 5. Primary Product Goals

## G-01 — Unify the learning workflow

ARIA shall provide one connected environment in which the major stages of a learner's journey can share context.

The learner should not need to manually reconstruct the same goal, topic, resource, weakness, or progress context across every feature.

---

## G-02 — Reduce manual coordination

ARIA should reduce repetitive work involved in coordinating:

- learning goals;
- resources;
- roadmaps;
- study activities;
- assessments;
- revision;
- schedules;
- reminders;
- progress;
- next actions.

Automation should reduce management overhead rather than automate away learning itself.

---

## G-03 — Support goal-driven learning across domains

ARIA shall support learners preparing for different goals without hardcoding the core product around a particular subject or exam.

The same product foundation should be capable of supporting university study, competitive exams, certifications, technical learning, interview preparation, professional skills, and independent learning.

---

## G-04 — Build persistent learning context

ARIA shall preserve relevant context across sessions and product systems.

This may include goals, topics, resources, study history, assessment history, revision history, roadmaps, plans, relevant preferences, and evidence-backed learning state.

---

## G-05 — Personalize from evidence

ARIA should increasingly adapt learning experiences based on meaningful evidence rather than superficial activity alone.

Assessment responses, retrieval attempts, teach-back, problem solving, revision results, and other appropriate signals may contribute to learner-state estimates.

ARIA should distinguish evidence strength and uncertainty where necessary.

---

## G-06 — Identify more than right and wrong answers

Where sufficient evidence exists, ARIA should help distinguish among:

- unknown knowledge;
- developing or weak understanding;
- strong understanding;
- possible misconceptions;
- prerequisite gaps.

ARIA should avoid making confident conclusions from weak evidence.

---

## G-07 — Create living learning paths

Roadmaps and plans should not be treated as one-time generated documents.

They should be capable of responding to meaningful changes such as:

- new goals;
- changed deadlines;
- assessment evidence;
- prerequisite gaps;
- missed work;
- changing availability;
- learner corrections.

---

## G-08 — Preserve learner control

ARIA should automate low-risk coordination while keeping consequential learning decisions inspectable and correctable.

The learner should be able to review significant proposed changes where appropriate.

Examples include major roadmap changes, substantial planner changes, or corrections to important learner-state assumptions.

---

## G-09 — Support flexible assessment

ARIA shall not assume one universal exam format.

Learners should be able to define the assessment experience appropriate to their goal, including question formats, topics, resources, difficulty, duration, scoring, sections, and other relevant parameters.

ARIA may recommend or prefill an assessment configuration, but the learner controls the final assessment specification.

---

## G-10 — Make progress meaningful

ARIA should prioritize learning evidence and goal progress over vanity engagement metrics.

Time spent, messages sent, or notes generated may provide activity context but should not automatically be interpreted as mastery.

---

## G-11 — Support learning under real-world constraints

ARIA should support learners who have limited time, changing schedules, multiple goals, upcoming exams, missed sessions, and different preferred ways of reviewing material.

The system should help the learner recover and reprioritize rather than merely accumulate overdue work.

---

## G-12 — Enable multiple learning modalities

ARIA should support learning through appropriate combinations of:

- conversation;
- reading/resources;
- notes;
- problem solving;
- assessments;
- retrieval/revision;
- teach-back;
- audio.

These modalities should share context where useful.

---

## G-13 — Make adaptation explainable

When ARIA makes or proposes a meaningful personalized decision, the learner should be able to understand the reason where practical.

Examples:

> "This topic was added because your last two assessments showed difficulty with its prerequisite."

or

> "This revision was prioritized because recall performance has declined and the exam is approaching."

---

## G-14 — Work with the wider learning ecosystem

ARIA should allow external resources and specialist platforms to remain part of the learner's workflow.

ARIA may link, organize, recommend, or integrate with external systems where technically and legally appropriate rather than recreating every specialist platform.

---

## G-15 — Become progressively intelligent

ARIA should remain useful before every advanced AI capability exists.

Basic product systems should work reliably first. Evidence, learner modeling, recommendations, adaptive roadmaps, adaptive planning, and cross-system orchestration should progressively increase intelligence as the required foundations become available.

---

# 6. Desired User Outcomes

A successful ARIA experience should help a learner reach outcomes such as:

### Orientation

The learner can quickly understand what they are working toward and what should happen next.

### Continuity

The learner can return later without manually reconstructing their learning context.

### Understanding

The learner can study concepts interactively and use their own resources where appropriate.

### Practice

The learner can test themselves in a format suitable for their actual goal.

### Awareness

The learner can see what appears strong, weak, untested, forgotten, or potentially misunderstood.

### Adaptation

New evidence can influence future revision, recommendations, roadmaps, and planning.

### Recovery

Falling behind does not require manually rebuilding the entire learning plan.

### Revision

ARIA can surface what deserves review rather than requiring the learner to manually remember everything that needs revisiting.

### Portability

Learning can continue in different contexts, including audio-based revision when reading or typing is inconvenient.

### Control

The learner can inspect and correct important ARIA assumptions and proposed changes.

---

# 7. Non-Goals

Non-goals prevent ARIA from becoming an undefined "everything app."

## NG-01 — ARIA is not a replacement for learning effort

ARIA should not complete the intellectual work the learner is supposed to practice merely to create the appearance of progress.

It may explain, guide, hint, evaluate, and support—but productive struggle remains part of learning.

---

## NG-02 — ARIA is not a general-purpose chatbot

ARIA may provide rich conversation, but its product identity is centered on longitudinal learning rather than unrestricted general assistant functionality.

---

## NG-03 — ARIA is not a full coding-practice ecosystem

ARIA may support coding assessment and connect to specialist coding platforms, but rebuilding the entire functionality and community ecosystem of dedicated coding-practice products is not a primary product goal.

---

## NG-04 — ARIA is not a course marketplace

ARIA may organize or recommend courses and learning resources, but it is not intended to become a marketplace or replace major course platforms.

---

## NG-05 — ARIA is not a video platform

Videos may be resources inside a learning journey. Hosting and recreating a complete video ecosystem is outside the primary product purpose.

---

## NG-06 — ARIA is not a general-purpose productivity workspace

ARIA may contain notes, planning, organization, and reminders, but those systems exist specifically to support learning goals.

It is not intended to replace every use case of general workspace/project-management products.

---

## NG-07 — ARIA is not an institutional LMS

ARIA is learner-centered rather than primarily designed around institutional administration, attendance, grading administration, classroom management, or school-wide course delivery.

Institutional functionality may be considered separately in the future but does not define the current product vision.

---

## NG-08 — ARIA is not a general-purpose search engine

Search exists to retrieve and connect relevant learning history, learner resources, and appropriate external learning information—not to recreate a web-scale search product.

---

## NG-09 — ARIA should not infer certainty where none exists

ARIA should not present uncertain learner-state conclusions as objective facts.

One mistake should not automatically mean "weak topic," and one correct answer should not automatically mean "mastered."

---

## NG-10 — ARIA should not silently control consequential learning decisions

Automation should not mean removing learner agency.

Significant roadmap or plan changes should be visible and reviewable where appropriate.

---

## NG-11 — ARIA should not hardcode one learner type

The product should not assume every user is a university student, competitive-exam candidate, coder, certification learner, or any other single category.

---

## NG-12 — ARIA should not hardcode one assessment model

MCQs are not appropriate for every learner. Neither are coding contests, essays, viva, or flashcards.

The assessment system must remain configurable.

---

## NG-13 — ARIA should not make every subsystem an AI agent

Agent architecture must be justified by product and technical needs.

Reliable deterministic software should be preferred where AI reasoning is unnecessary.

---

## NG-14 — ARIA should not optimize primarily for engagement

The product should not intentionally maximize screen time, message count, streak anxiety, or notification volume at the expense of effective learning.

---

# 8. Product Constraints Established by Phase 0

The following decisions are treated as constraints for the remainder of the PRD.

### Domain independence

Core content, goals, roadmaps, resources, and Home experiences must be generated from learner context rather than hardcoded subject categories.

### Lightweight onboarding

ARIA should not require every deadline, examination, learning preference, or future goal during initial onboarding.

### Multiple goals

The product model must permit a learner to pursue multiple goals and deadlines over time.

### Assessment control

The learner controls the final exam/assessment configuration.

### Evidence-backed learning state

ARIA's learner-state confidence should improve from meaningful evidence rather than conversation memory alone.

### Memory ≠ Learner Model

Persistent preferences/context and evidence-backed learning state are related but conceptually distinct.

### Explainable adaptation

Meaningful automated changes should retain a reason that can be surfaced to the learner where appropriate.

### External resources remain valid

ARIA should not require all learning to occur inside ARIA in order to be useful.

### Notifications are user-controlled

In-app and email reminders should respect learner preferences and avoid unnecessary notification volume.

---

# 9. Product Scope at PRD Level

The complete PRD will define requirements for:

```text
Account & Authentication
Onboarding
Goals & Learning Contexts
Home
Study
Resources & Retrieval
Notes
Assessment
Evaluation
Evidence
Learner Model
Memory
Misconception Tracking
Prerequisite Detection
Roadmaps
Planner
Revision
Progress
Recommendations
Audio
Search
Notifications
Settings & User Controls
Cross-System Automation
Reliability / Validation
Privacy / Security
Accessibility
```

Detailed functional requirements belong to later Phase 1 steps.

---

# 10. Product Decision Framework

When later requirements conflict or scope questions arise, evaluate them in this order:

```text
1. Does it help meaningful learning progress?
                ↓
2. Does it support the learner's goal?
                ↓
3. Does it reduce unnecessary coordination?
                ↓
4. Can it use/share learning context responsibly?
                ↓
5. Does the learner retain appropriate control?
                ↓
6. Can the behaviour be made reliable enough?
                ↓
7. Does ARIA need to build it, or can it integrate it?
```

A feature being technically possible is not sufficient reason to add it.

---

# 11. Step 1 Decisions

Phase 1 Step 1 establishes the following:

> **ARIA's job is not to generate more learning content. Its job is to coordinate a learner's journey and make each learning interaction more useful because the system understands the surrounding context.**

The product should aim for:

```text
Less manual coordination
        +
More learning continuity
        +
Better evidence of understanding
        +
Adaptive next actions
        +
Learner control
```

The complete feature set remains part of the product vision, but every feature must serve the learning journey rather than existing merely to increase feature count.

---

# 12. Step 1 Completion

**Step 1 — Product Overview, Goals & Non-Goals is complete.**

Next:

# Step 2 — User & Learning-Context Requirements

Step 2 will define requirements for:

- goal-driven learners;
- different learning situations;
- multiple simultaneous goals;
- learning contexts;
- onboarding;
- deadlines and exam contexts;
- learner preferences;
- personalization boundaries;
- returning-user continuity;
- context switching between goals;
- user control over inferred information.

These requirements will establish what ARIA must know about a learner and how that context should behave before the detailed feature requirements are written.