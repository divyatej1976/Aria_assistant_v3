# ARIA — Phase 1 PRD

## Step 1 — Product Overview, Goals & Non-Goals

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Reviewed and aligned with amended `VISION.md`  
**Primary source:** `VISION.md`

---

# 1. Purpose

This document translates ARIA's reviewed Phase 0 vision into PRD-level goals and boundaries.

It deliberately separates three levels that must not be confused:

1. **Vision** — what ARIA can ultimately become.
2. **Architecture direction** — how the product should remain extensible without premature universal abstraction.
3. **Validation releases** — the deliberately constrained slices used to prove product hypotheses.

The complete product vision is **not** the feature list for R0.

---

# 2. Product Overview

ARIA is an AI-powered learning operating system intended initially for **college students, recent graduates, and early-career learners** pursuing academic, placement, competitive-exam, certification, interview, technical/professional skill, or upskilling goals.

Its long-term purpose is to connect studying, resources, assessment, evidence, learner_concept_state, revision, roadmaps, planning, progress, notes, audio, reminders, and recommendations around persistent learner context.

The product thesis is not merely that these features exist in one interface. It is that they can increasingly **share learning state and adapt what happens next**.

---

# 3. Problem Statement

Learning workflows are fragmented across tutoring, resources, notes, assessments, planning, revision, progress tracking, and specialist platforms.

The learner is therefore often responsible for repeatedly coordinating:

- what to learn next;
- which resources matter;
- what has been understood;
- what needs more work;
- what should be tested or revised;
- how learning plans should respond to new evidence.

> **ARIA's problem is excessive manual coordination across a fragmented learning journey.**

ARIA should reduce that coordination burden without automating away the intellectual effort required to learn.

---

# 4. Initial Audience Boundary

ARIA initially serves:

> **College students, recent graduates, and early-career learners working toward concrete learning or preparation goals.**

Representative contexts include university learning/exams, placements, interviews, certifications, competitive/government exams, technical/professional skills, and post-college upskilling.

ARIA is not initially optimized for primary-school/children's education, institutional LMS administration, teacher/classroom management, or corporate training administration.

This audience boundary does not mean every listed context must be proven in R0.

---

# 5. Domain Principle

ARIA's long-term product model is goal-driven and domain-independent.

However:

> **Domain independence is a long-term product and architecture direction, not an R0 acceptance criterion.**

Early validation releases may deliberately use one or a small number of representative learning contexts.

The architecture should avoid **unnecessary domain-specific coupling** that would prevent later generalization, but it should not attempt to invent universal abstractions before concrete cases have been validated.

The intended method is:

```text
Specific case
    ↓
Validate
    ↓
Add structurally different case
    ↓
Observe broken assumptions
    ↓
Generalize
    ↓
Repeat
```

---

# 6. Primary Product Goals

## G-01 — Connect the learning workflow

Major learning systems should eventually share relevant learner and goal context rather than behaving as unrelated mini-products.

## G-02 — Reduce manual coordination

ARIA should reduce repetitive organizational work around goals, resources, learning activities, assessment, revision, planning, and next actions.

## G-03 — Adapt from evidence

ARIA should increasingly use meaningful learning evidence to influence future learning behaviour.

## G-04 — Preserve persistent learning context

Relevant goals, resources, activity, evidence, preferences, and learning state should survive across sessions where appropriate.

## G-05 — Preserve learner control

Consequential personalized changes should remain understandable, correctable, and reviewable where appropriate.

## G-06 — Support flexible assessment

ARIA should not assume one universal assessment format. The learner controls the final assessment specification within supported capabilities.

## G-07 — Make progress meaningful

Learning evidence and goal progress should matter more than vanity activity metrics.

## G-08 — Become progressively intelligent

ARIA should remain useful before advanced learner modeling, misconception detection, planning, audio, or multi-agent orchestration exist.

## G-09 — Integrate rather than unnecessarily recreate

Specialist external learning platforms may remain part of the learner's ecosystem.

## G-10 — Earn complexity through validation

New systems should be introduced because they are required to validate the next product hypothesis, not merely because they exist in the long-term feature map.

---

# 7. R0 Product Hypothesis

R0 is an **experimental validation release**, not a compressed version of the entire ARIA Learning OS.

Its first product question is:

> **Can ARIA observe meaningful learning evidence, update a basic learner_concept_state, and use that state to appropriately change the learner's next study experience?**

The minimum conceptual loop is:

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
 Basic learner_concept_state
          ↓
Adapt Next Study Experience
          ↓
          ↺
```

A proposed R0 feature should face this elimination test:

> **If we remove this feature, can we still test whether ARIA's learner_concept_state changes future learning appropriately?**

If yes, it is probably not required for R0.

---

# 8. R0 Is Not the Full Vision

The following remain important ARIA capabilities but are **not automatically R0 requirements**:

- Notes;
- Audio;
- Planner;
- reminders;
- full Roadmap generation/adaptation;
- sophisticated Progress dashboards;
- full Revision engine;
- full misconception detection;
- external-platform tracking;
- advanced multi-agent orchestration;
- broad domain validation.

Their detailed requirements may remain documented in Phase 1 because the PRD also describes the product direction. Release boundaries determine when they become implementation requirements.

---

# 9. Validation Principle

R0 success has two levels.

## Gate A — Engineering Validation

Gate A must rigorously demonstrate, through controlled and reproducible scenarios, that the adaptive machinery correctly closes the loop from learning activity to evidence to learner-state change to adapted future behaviour.

## Gate B — Real-User Signal

Gate B should collect small-scale before/after observations and qualitative feedback from available target users.

At solo-capstone scale, Gate B provides **directional evidence**, not statistically rigorous causal proof of improved learning outcomes.

Exact acceptance criteria and evaluation methods are defined in the Phase 1 validation/closure document.

---

# 10. Non-Goals

ARIA is not intended to become:

- a replacement for learner effort;
- a general-purpose chatbot;
- a full coding-practice ecosystem;
- a course marketplace;
- a video-hosting platform;
- a general-purpose productivity workspace;
- an institutional LMS;
- a primary-school/children's learning platform in the initial product scope;
- a corporate training administration platform;
- a general-purpose search engine.

ARIA should also not:

- treat one mistake as confirmed weakness or misconception;
- treat one correct answer as mastery;
- silently make high-impact learning decisions from weak evidence;
- hardcode permanent DSA/AWS/GATE/etc. branches into the core product;
- make every subsystem an AI agent;
- optimize primarily for engagement or screen time.

---

# 11. Constraints Carried Forward

The remainder of the PRD must preserve these constraints:

1. Initial audience: college students, recent graduates, and early-career learners.
2. Long-term domain independence; early validation may be domain-constrained.
3. Avoid unnecessary domain-specific coupling, not all domain-specific implementation.
4. Lightweight onboarding; no universal mandatory deadline.
5. Learner-controlled assessment specification within supported capabilities.
6. Evidence-backed learning state is distinct from ordinary conversational memory.
7. Meaningful adaptation should be explainable/correctable where appropriate.
8. External learning resources remain valid.
9. Full product feature scope does not equal R0 scope.
10. R0 validates the smallest adaptive-learning loop.
11. Gate A is rigorous engineering validation.
12. Gate B is directional real-user evidence at capstone scale and must not be overclaimed.

---

# 12. Step 1 Exit Condition

Step 1 is complete when later PRD documents can distinguish:

- the long-term ARIA vision;
- the initial audience;
- architecture extensibility;
- R0's constrained hypothesis;
- later-release capabilities;
- engineering validation from real-user product evidence.

**Step 1 is aligned with the reviewed Phase 0 vision.**
---

## Next

Step 2 — User & Learning-Context Requirements.
