# ARIA — Progress, Consistency & Motivation Requirements

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — PRD Supplemental Requirements  
**Status:** Approved  
**Extends:** `03-functional-requirements.md` — Progress

---

# 1. Purpose

ARIA should help learners see not only what they know, but also the consistency of the work that produced that progress.

The product shall therefore include a motivational progress layer inspired by familiar contribution/activity systems while preserving ARIA's core rule:

> **Activity and consistency can be celebrated, but they must never be confused with mastery.**

---

# 2. Daily Learning Activity

## FR-PROG-011 — Meaningful learning day

ARIA shall be capable of identifying whether a learner completed at least one qualifying meaningful learning activity during a calendar day.

A qualifying activity may include supported actions such as:

- completing a study session that meets the product's meaningful-activity rules;
- completing an assessment;
- completing a revision activity;
- completing a planned learning task;
- completing a teach-back or diagnostic activity;
- completing supported externally tracked learning activity where a legitimate integration exists;
- other future learning actions that produce a valid completion event.

Simply opening ARIA, signing in, viewing a page, or sending a trivial message shall not automatically qualify as a meaningful learning day.

## FR-PROG-012 — Learner timezone

Daily activity boundaries shall use the learner's relevant timezone rather than an arbitrary server timezone.

---

# 3. Contribution / Activity Heatmap

## FR-PROG-013 — Learning activity heatmap

ARIA shall provide a calendar-style activity heatmap that allows the learner to see learning consistency over time.

The heatmap should support daily activity intensity rather than only a binary active/inactive state where meaningful activity data is available.

Potential intensity inputs may include the number of completed meaningful learning activities or another validated activity measure.

## FR-PROG-014 — Heatmap explanation

The learner should be able to understand what caused a day to appear active and what the intensity represents.

## FR-PROG-015 — Activity is not mastery

Heatmap intensity shall represent learning activity/consistency and shall not be presented as concept mastery, readiness, or learning quality.

---

# 4. Streaks

## FR-PROG-016 — Current streak

ARIA should display the learner's current streak of consecutive meaningful learning days.

## FR-PROG-017 — Longest streak

ARIA should retain and display the learner's longest meaningful-learning streak.

## FR-PROG-018 — Active days

ARIA should show useful consistency measures such as active learning days during the current week/month or another selected period.

## FR-PROG-019 — Streak integrity

Trivial product activity shall not be sufficient to preserve a learning streak.

## FR-PROG-020 — Streak failure does not erase history

Missing a day may reset the current consecutive-day streak, but shall not erase the learner's historical activity heatmap, longest streak, completed work, or learning progress.

---

# 5. Motivational Milestones

## FR-PROG-021 — Consistency milestones

ARIA may celebrate meaningful consistency milestones such as a 3-day, 7-day, 30-day, or other appropriate streak/milestone.

Exact milestone values are a UX/product-tuning decision rather than hardcoded PRD requirements.

## FR-PROG-022 — Learning milestones

ARIA should prioritize learning-outcome milestones in addition to activity milestones.

Examples include:

- a previously weak concept becoming strong after new evidence;
- completing a roadmap milestone;
- completing an important revision cycle;
- improving assessment performance;
- recovering successfully after missed planned work;
- completing a learner-defined goal.

## FR-PROG-023 — Specific motivation

Motivational feedback should reference the actual achievement rather than relying primarily on generic praise.

---

# 6. Healthy Motivation

## FR-PROG-024 — No punitive streak design

ARIA should avoid making a missed day appear to erase the value of previous learning effort.

## FR-PROG-025 — Multiple consistency views

The product should combine current streak with broader measures such as longest streak, active days, and the activity heatmap so one missed day does not make long-term consistency invisible.

## FR-PROG-026 — Rest and schedule awareness

Future versions may distinguish planned rest days or learner-defined schedules from unintended inactivity where useful, rather than assuming every learner must study seven days per week.

## FR-PROG-027 — No deceptive gamification

ARIA shall not inflate streaks, progress, mastery, or achievement indicators merely to increase engagement.

---

# 7. Home Integration

## FR-HOME-011 — Consistency summary

Home may surface a compact consistency summary such as current streak, today's meaningful-learning status, or recent active days.

## FR-HOME-012 — Motivation without clutter

Consistency indicators should support the learner's next action rather than overwhelm Home with gamification.

---

# 8. Progress Page Model

ARIA's Progress experience should conceptually separate three dimensions:

```text
PROGRESS
│
├── Consistency
│   ├── Current streak
│   ├── Longest streak
│   ├── Active days
│   └── Activity heatmap
│
├── Learning progress
│   ├── Goal / roadmap progress
│   ├── Assessment history
│   ├── Concept state
│   ├── Improvement over time
│   └── Readiness where supported
│
└── Learning health
    ├── Revision state
    ├── Weak concepts
    ├── Possible misconceptions
    └── Prerequisite gaps
```

This separation is intentional.

A learner may have excellent consistency while still struggling with a concept, or may demonstrate strong knowledge despite not using ARIA every day.

---

# 9. Example

```text
🔥 Current streak: 12 days
🏆 Longest streak: 24 days
📅 Active this month: 21 days

Activity
Mon Tue Wed Thu Fri Sat Sun
 ░   ▓   █   ░   █   ▓   █
 █   █   ▓   █   ░   ▓   █

Learning progress
DBMS: improving
Normalization: WEAK → STRONG
Revision completed: 7
Assessments completed: 4
```

The final visual design is a UX decision; this example defines product intent only.

---

# 10. Acceptance Criteria

## AC-PROG-MOT-001

Completing a qualifying meaningful learning activity can mark the appropriate learner-local calendar day as active.

## AC-PROG-MOT-002

Signing in without meaningful learning activity does not by itself preserve the learning streak.

## AC-PROG-MOT-003

The contribution heatmap accurately reflects recorded qualifying activity for tested dates.

## AC-PROG-MOT-004

Current and longest streak calculations behave correctly across learner-local day boundaries.

## AC-PROG-MOT-005

Missing a day does not erase historical activity or learning progress.

## AC-PROG-MOT-006

Activity/streak indicators are visually and semantically distinct from mastery/readiness indicators.

## AC-PROG-MOT-007

A learner can understand what qualified a displayed active day through an appropriate detail interaction or explanation.

---

# 11. Product Decision

ARIA will include a motivational consistency system consisting of:

**meaningful learning days + contribution/activity heatmap + current streak + longest streak + active-day summaries + learning milestones.**

The system exists to make effort and consistency visible, while ARIA's evidence-backed Learner Model remains responsible for claims about understanding and mastery.