# ARIA — Phase 1 PRD

## Step 3 — Functional Requirements

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Step 3 — Complete  
**Primary sources:** `VISION.md`, `01-product-overview-goals.md`, `02-user-context-requirements.md`

---

# 1. Purpose

This document defines the functional behaviour required from ARIA's major user-facing product systems.

It answers:

> **What must each ARIA feature allow the learner to do?**

It intentionally avoids premature decisions about frameworks, database schemas, APIs, agent frameworks, page layouts, and implementation details.

Cross-system orchestration is specified more deeply in Step 4. Evidence, Learner Model, memory, misconceptions, AI behaviour, and confidence are specified more deeply in Step 5.

---

# 2. Requirement Language

- **Shall** — required product behaviour.
- **Should** — expected behaviour unless a later design/technical constraint justifies an alternative.
- **May** — permitted or optional behaviour.

Requirement IDs are stable references for later user flows, architecture, APIs, implementation, and testing.

---

# 3. Account & Authentication

## FR-AUTH-001 — Account creation

The system shall allow a learner to create an account.

## FR-AUTH-002 — Sign in

The system shall allow an existing learner to authenticate and access their persistent learning environment.

## FR-AUTH-003 — Email verification

The system shall support email verification where email-based identity is used.

## FR-AUTH-004 — Password recovery

The system shall provide a secure account recovery/reset flow for password-based accounts.

## FR-AUTH-005 — Session persistence

Authenticated sessions should persist appropriately so normal return visits do not require unnecessary repeated authentication.

## FR-AUTH-006 — Sign out

The learner shall be able to end their authenticated session.

## FR-AUTH-007 — Account access protection

Protected learning data shall not be accessible without appropriate authorization.

## FR-AUTH-008 — Account management

The learner shall have access to relevant account controls, including profile and security-related settings.

---

# 4. Onboarding

## FR-ONB-001 — Lightweight onboarding

ARIA shall provide a short initial onboarding experience rather than requiring complete learner profiling before use.

## FR-ONB-002 — Initial intent

The learner should be able to describe what they currently want to learn or prepare for.

## FR-ONB-003 — Custom intent

The learner shall not be restricted to a fixed list of subjects, exams, or learning categories.

## FR-ONB-004 — Optional skipping

Non-essential onboarding questions should be skippable where practical.

## FR-ONB-005 — No universal deadline

ARIA shall not require a single global deadline during onboarding.

## FR-ONB-006 — Progressive guidance

ARIA should introduce capabilities contextually after onboarding instead of explaining every feature upfront.

## FR-ONB-007 — Onboarding persistence

Useful onboarding information shall become part of the learner's persistent context according to its scope.

---

# 5. Goals

## FR-GOAL-001 — Create goal

The learner shall be able to create a learning goal using natural language.

## FR-GOAL-002 — Edit goal

The learner shall be able to edit a goal's relevant details.

## FR-GOAL-003 — Optional deadline

A goal shall support an optional target date/deadline.

## FR-GOAL-004 — Priority

The learner shall be able to assign or modify goal priority.

## FR-GOAL-005 — Multiple goals

The learner shall be able to maintain multiple active goals simultaneously.

## FR-GOAL-006 — Goal status

Goals shall support lifecycle states such as active, paused, completed, and archived.

## FR-GOAL-007 — Resume goal

A paused or previously active goal should be resumable with its relevant context preserved.

## FR-GOAL-008 — Goal overview

The learner shall be able to view a goal's relevant roadmap, progress, resources, upcoming work, and related learning activity where available.

## FR-GOAL-009 — Goal decomposition

ARIA should be able to help decompose a broad goal into milestones, topics, prerequisites, or other actionable structure.

## FR-GOAL-010 — Goal deletion

The learner shall be able to request deletion of a goal subject to later-defined data-dependency and privacy rules.

---

# 6. Home

Home is ARIA's personalized learning command centre.

## FR-HOME-001 — Personalized Home

Home shall be generated from the learner's actual goals and learning state rather than hardcoded subject cards.

## FR-HOME-002 — Active goals

Home shall surface relevant active goals.

## FR-HOME-003 — Today's work

Where planning data exists, Home should surface scheduled learning work for the current day.

## FR-HOME-004 — Due revision

Where revision data exists, Home should surface due or high-priority revision.

## FR-HOME-005 — Upcoming events

Home should surface relevant upcoming exams, assessments, milestones, and deadlines.

## FR-HOME-006 — Progress summary

Home should surface meaningful progress summaries where sufficient data exists.

## FR-HOME-007 — Recommended next action

ARIA should be capable of presenting one or more context-aware next actions with a reason.

## FR-HOME-008 — Continue learning

The learner should be able to resume recent relevant learning activity directly from Home.

## FR-HOME-009 — Proposed changes

Important ARIA-proposed roadmap or plan changes should be visible from an appropriate high-attention surface such as Home.

## FR-HOME-010 — Empty-state usefulness

For new learners without sufficient data, Home shall provide useful starting actions rather than fabricated personalized insights.

---

# 7. Study

## FR-STUDY-001 — Start study conversation

The learner shall be able to start a conversational study session.

## FR-STUDY-002 — Goal association

A study session may be associated with a goal, topic, or exploratory context.

## FR-STUDY-003 — Resource-grounded study

The learner shall be able to study using selected resources as context.

## FR-STUDY-004 — Follow-up questions

ARIA shall support multi-turn follow-up questions while retaining relevant session context.

## FR-STUDY-005 — Explanation depth

The learner shall be able to request different explanation depths or styles during a session.

## FR-STUDY-006 — Guided learning

ARIA should support guided explanation that progressively develops understanding rather than always providing a complete answer immediately.

## FR-STUDY-007 — Socratic mode

ARIA should support question-led learning where appropriate.

## FR-STUDY-008 — Hinting

ARIA should support hints before full solutions when requested or configured.

## FR-STUDY-009 — Teach-back

ARIA should support asking the learner to explain a concept back and provide feedback.

## FR-STUDY-010 — Rapid revision

The learner shall be able to request concise, time-constrained revision.

## FR-STUDY-011 — Source visibility

When an answer is grounded in learner-provided or retrieved resources, ARIA should make relevant source provenance accessible.

## FR-STUDY-012 — Conversation persistence

Study conversations shall be persistable and retrievable by the learner.

## FR-STUDY-013 — Conversation organization

The learner should be able to identify and revisit study conversations through title, goal, topic, date, search, or other appropriate organization.

## FR-STUDY-014 — Create downstream learning material

The learner shall be able to use relevant study content as input to connected features such as Notes, Assessment, or Audio.

## FR-STUDY-015 — Correct active context

The learner shall be able to correct the goal/topic/resource context associated with a study session.

---

# 8. Resources & Retrieval

## FR-RES-001 — Add resources

The learner shall be able to add supported learning resources to ARIA.

## FR-RES-002 — File resources

ARIA shall support common document/resource file types selected during technical design.

## FR-RES-003 — Link resources

ARIA should support adding web-based learning resources by URL where technically and legally feasible.

## FR-RES-004 — Resource metadata

Resources shall store useful metadata such as title, type, source, associated goal/topic, and creation/addition time where available.

## FR-RES-005 — Goal association

A resource may be associated with one or more goals/topics where relevant.

## FR-RES-006 — Resource organization

The learner shall be able to browse and organize their learning resources.

## FR-RES-007 — Resource search

The learner shall be able to search available resources.

## FR-RES-008 — Content retrieval

ARIA shall be capable of retrieving relevant content from supported indexed resources for learning tasks.

## FR-RES-009 — Provenance

Retrieved content used by AI features should retain source provenance.

## FR-RES-010 — Resource selection

The learner shall be able to explicitly choose which resources should constrain or inform a study/assessment/notes/audio activity.

## FR-RES-011 — Resource removal

The learner shall be able to remove resources subject to dependency/data-retention rules.

## FR-RES-012 — Processing status

The learner should be able to understand whether an uploaded resource is ready, processing, unsupported, or failed.

## FR-RES-013 — Failure recovery

A failed resource-processing operation shall not crash unrelated learning functionality.

## FR-RES-014 — External specialist resources

ARIA may link to external learning platforms/resources without attempting to recreate the external platform.

---

# 9. Notes

## FR-NOTE-001 — Create note

The learner shall be able to create a note manually.

## FR-NOTE-002 — Generate from study

The learner shall be able to create notes from relevant study-session content.

## FR-NOTE-003 — Generate from resources

The learner shall be able to generate notes from selected resources.

## FR-NOTE-004 — Edit notes

Generated and manual notes shall be editable.

## FR-NOTE-005 — Note organization

Notes should support association with goals, topics, resources, or other useful organizational context.

## FR-NOTE-006 — Note formats

ARIA should support transformations such as concise notes, detailed notes, summaries, key points, and revision sheets.

## FR-NOTE-007 — Source references

Generated notes should retain source references where they are derived from specific resources.

## FR-NOTE-008 — Search notes

Notes shall be discoverable through search.

## FR-NOTE-009 — Notes to assessment

The learner shall be able to use selected notes as assessment source material.

## FR-NOTE-010 — Notes to audio

The learner shall be able to use selected notes as source material for audio learning.

## FR-NOTE-011 — Delete/archive notes

The learner shall be able to remove or archive notes according to later-defined data rules.

---

# 10. Assessment Engine

ARIA's assessment system shall be specification-driven rather than built around one universal quiz format.

## FR-ASSESS-001 — Create assessment

The learner shall be able to create an assessment for a selected learning context.

## FR-ASSESS-002 — Assessment specification

An assessment shall be generated from an explicit specification.

## FR-ASSESS-003 — Topic selection

The learner shall be able to specify topics/scope.

## FR-ASSESS-004 — Resource selection

The learner shall be able to choose source resources, notes, syllabus material, or other supported context.

## FR-ASSESS-005 — Question-format selection

The learner shall be able to select one or more supported question formats.

Potential formats include:

- MCQ;
- multiple-select;
- true/false;
- fill-in-the-blank;
- numerical answer;
- short answer;
- long answer;
- conceptual/application questions;
- problem solving;
- viva/oral;
- teach-back;
- coding assessment;
- mixed/custom sections.

## FR-ASSESS-006 — Question count / marks

The learner shall be able to specify relevant size parameters such as question count and/or marks.

## FR-ASSESS-007 — Difficulty

The learner shall be able to specify desired difficulty or accept an ARIA recommendation/default.

## FR-ASSESS-008 — Duration

The learner shall be able to configure a duration for timed assessments or choose an untimed format.

## FR-ASSESS-009 — Sections

ARIA should support assessments containing multiple sections with different formats or rules.

## FR-ASSESS-010 — Scoring configuration

Where applicable, the assessment specification shall support scoring rules such as marks, partial credit, or negative marking.

## FR-ASSESS-011 — Feedback behaviour

The learner should be able to choose whether feedback is immediate, after each section, or after completion where appropriate.

## FR-ASSESS-012 — Natural-language configuration

The learner should be able to describe an assessment in natural language and have ARIA translate it into an editable specification.

## FR-ASSESS-013 — Specification preview

Before generation/start, the learner shall be able to inspect and modify the assessment specification.

## FR-ASSESS-014 — ARIA recommendations

ARIA may recommend assessment settings based on goal/context, but shall not remove the learner's control over the final configuration.

## FR-ASSESS-015 — Dynamic rendering

The assessment experience shall render according to the specification rather than assuming all assessments use the same interface.

## FR-ASSESS-016 — Timed assessment

Timed assessments shall display and enforce timing behaviour according to the assessment specification.

## FR-ASSESS-017 — Save attempt

Assessment attempts shall be persisted appropriately.

## FR-ASSESS-018 — Submit assessment

The learner shall be able to submit a completed or partially completed assessment according to assessment rules.

## FR-ASSESS-019 — Attempt history

The learner shall be able to revisit relevant assessment history and results.

## FR-ASSESS-020 — Regenerate / create another

The learner shall be able to create another assessment from the same or modified specification without being forced to rebuild all configuration manually.

## FR-ASSESS-021 — Coding assessments

When coding assessment support exists, the assessment system shall support coding-specific interaction and evaluation requirements rather than treating code as ordinary text answers.

## FR-ASSESS-022 — Viva / oral assessment

When oral assessment support exists, ARIA should support question-response progression appropriate to viva-style testing.

## FR-ASSESS-023 — Teach-back assessment

ARIA should support assessments in which the learner explains a concept and receives evaluation of conceptual coverage and errors.

---

# 11. Evaluation

## FR-EVAL-001 — Evaluate submitted responses

ARIA shall evaluate supported assessment responses according to the relevant assessment format and scoring rules.

## FR-EVAL-002 — Separate generation and evaluation

Assessment generation and evaluation shall remain logically separable product responsibilities.

## FR-EVAL-003 — Score where appropriate

ARIA shall calculate scores where the assessment format supports objective or rubric-based scoring.

## FR-EVAL-004 — Feedback

The learner shall receive useful feedback after evaluation according to configured feedback behaviour.

## FR-EVAL-005 — Topic-level results

ARIA should provide topic/concept-level performance information when the assessment structure supports it.

## FR-EVAL-006 — Explanation

For incorrect or incomplete responses, ARIA should provide an explanation appropriate to the assessment context.

## FR-EVAL-007 — Rubric-based evaluation

Open-ended formats should support rubric/criteria-based evaluation where appropriate.

## FR-EVAL-008 — Uncertainty

ARIA should avoid presenting subjective or uncertain evaluation as perfectly objective.

## FR-EVAL-009 — Evidence output

Evaluation shall be capable of producing structured outputs usable by the Evidence system.

## FR-EVAL-010 — Review answers

The learner shall be able to review their submitted answers and corresponding evaluation where assessment rules permit.

## FR-EVAL-011 — Re-evaluation/correction path

Where an evaluation is incorrect or disputed, the product should provide an appropriate correction/review path.

---

# 12. Roadmaps

## FR-ROAD-001 — Generate roadmap

ARIA shall be able to generate a learning roadmap for a goal.

## FR-ROAD-002 — Roadmap structure

A roadmap should support phases, milestones, topics, subtopics, prerequisites, dependencies, resources, activities, and assessments where relevant.

## FR-ROAD-003 — User editing

The learner shall be able to modify an ARIA-generated roadmap.

## FR-ROAD-004 — Resource attachment

Resources may be attached to roadmap elements.

## FR-ROAD-005 — Progress

Roadmap elements shall be capable of storing progress/state.

## FR-ROAD-006 — Dependencies

Roadmaps should represent meaningful prerequisite/dependency relationships where applicable.

## FR-ROAD-007 — Adaptive proposal

ARIA should be able to propose roadmap changes based on new learner evidence or changed circumstances.

## FR-ROAD-008 — Explain adaptation

A proposed significant roadmap change should include an understandable reason.

## FR-ROAD-009 — Accept/modify/reject

The learner should be able to accept, modify, or reject significant proposed roadmap changes.

## FR-ROAD-010 — Roadmap history

ARIA should retain sufficient roadmap history to explain meaningful changes and support auditability.

## FR-ROAD-011 — Multiple roadmaps

The learner may maintain roadmaps for multiple goals.

## FR-ROAD-012 — Roadmap without deadline

Roadmap generation shall not require a deadline.

---

# 13. Planner

## FR-PLAN-001 — Create plan

ARIA shall be able to convert learning work into a time-based plan.

## FR-PLAN-002 — Availability

The learner shall be able to provide or modify available learning time.

## FR-PLAN-003 — Multiple goals

Planning shall be capable of considering multiple active goals.

## FR-PLAN-004 — Deadlines

The planner shall consider relevant deadlines when available.

## FR-PLAN-005 — Roadmap scheduling

Roadmap activities should be schedulable into study sessions.

## FR-PLAN-006 — Revision scheduling

Revision work should be schedulable alongside new learning.

## FR-PLAN-007 — Assessment scheduling

Planned assessments should be schedulable.

## FR-PLAN-008 — Day view

The learner should be able to view planned work for a day.

## FR-PLAN-009 — Week/calendar view

The learner should be able to inspect planned work across a broader time range.

## FR-PLAN-010 — Manual changes

The learner shall be able to move, reschedule, add, or remove planned sessions.

## FR-PLAN-011 — Missed-session detection

ARIA should be able to detect when planned learning work was not completed where completion state is available.

## FR-PLAN-012 — Plan recovery

When work is missed, ARIA should be able to propose a revised feasible plan rather than only marking work overdue.

## FR-PLAN-013 — Explain recovery

Significant recovery changes should explain what moved and why.

## FR-PLAN-014 — Conflict detection

ARIA should detect obvious scheduling conflicts or unrealistic workload where possible.

## FR-PLAN-015 — Temporary availability changes

The learner shall be able to communicate temporary constraints such as reduced time today without permanently changing their normal availability.

## FR-PLAN-016 — Plan approval

Substantial automatic rescheduling should support learner review/approval where appropriate.

---

# 14. Revision

## FR-REV-001 — Revision items

ARIA shall be able to create or identify concepts/material that require revision.

## FR-REV-002 — Revision scheduling

ARIA shall support scheduling future revision.

## FR-REV-003 — Due revision

The learner shall be able to see revision that is due or prioritized.

## FR-REV-004 — Retrieval-based revision

ARIA should support active retrieval rather than relying only on rereading.

## FR-REV-005 — Multiple revision formats

Revision may use formats such as questions, short answers, flashcards, teach-back, oral questioning, mini-assessments, summaries, or audio.

## FR-REV-006 — Evidence-informed priority

Revision priority should be capable of using learner evidence when available.

## FR-REV-007 — Revision history

ARIA shall retain relevant revision history.

## FR-REV-008 — Revision completion

The learner shall be able to mark/complete revision activities, with results recorded where appropriate.

## FR-REV-009 — Retest after weakness/misconception

ARIA should support targeted follow-up testing after remediation.

## FR-REV-010 — Time-constrained revision

The learner shall be able to request revision designed for a specified amount of available time.

---

# 15. Progress

## FR-PROG-001 — Goal progress

ARIA shall provide progress information for active learning goals where sufficient data exists.

## FR-PROG-002 — Roadmap progress

ARIA shall provide progress across roadmap elements.

## FR-PROG-003 — Assessment history

Progress views should incorporate relevant assessment history.

## FR-PROG-004 — Concept state

Where sufficient evidence exists, ARIA should display concept-level learning state rather than only completion percentages.

## FR-PROG-005 — Revision health

Progress should surface relevant revision state/history where useful.

## FR-PROG-006 — Improvement over time

ARIA should support showing meaningful change in performance or learner state over time.

## FR-PROG-007 — Misconceptions / gaps

Where supported by sufficient evidence, progress views may surface possible misconceptions or prerequisite gaps.

## FR-PROG-008 — Untested state

ARIA should distinguish "not yet sufficiently tested" from "weak" where possible.

## FR-PROG-009 — Activity vs mastery

ARIA shall not automatically equate time spent or content consumed with mastery.

## FR-PROG-010 — Readiness

ARIA may provide readiness estimates when sufficient evidence exists, but uncertainty should be communicated appropriately.

---

# 16. Recommendations

## FR-REC-001 — Next action

ARIA should be capable of recommending an appropriate next learning action.

## FR-REC-002 — Recommendation types

Recommendations may include studying a topic, revising, taking an assessment, reviewing a prerequisite, continuing a roadmap, adjusting a plan, or reviewing a proposed change.

## FR-REC-003 — Recommendation reason

Meaningful recommendations should include an understandable reason.

## FR-REC-004 — Context awareness

Recommendations should consider the relevant active goal/context and available learner state.

## FR-REC-005 — Time awareness

Recommendations should consider immediate available time or deadlines when known.

## FR-REC-006 — User override

The learner shall remain free to ignore a recommendation and choose another learning action.

## FR-REC-007 — No fabricated certainty

ARIA should not pretend a recommendation is strongly personalized when insufficient learner data exists.

---

# 17. Audio Learning

## FR-AUDIO-001 — Generate audio from notes

The learner shall be able to generate audio learning material from selected notes.

## FR-AUDIO-002 — Generate audio from resources

The learner shall be able to generate audio from supported learning resources.

## FR-AUDIO-003 — Generate audio from study material

Relevant study content should be usable as audio source material.

## FR-AUDIO-004 — Audio purpose

The learner should be able to specify an audio purpose such as explanation, summary, or revision where supported.

## FR-AUDIO-005 — Length/time constraint

The learner should be able to request audio suited to a desired duration where technically feasible.

## FR-AUDIO-006 — Adaptive revision audio

ARIA should eventually be able to generate audio revision using goal context, learner state, weaknesses, revision history, upcoming assessments, and available time.

## FR-AUDIO-007 — Playback

The learner shall be able to play generated audio within an appropriate product experience.

## FR-AUDIO-008 — Regeneration

The learner should be able to regenerate audio with changed scope/style/length.

## FR-AUDIO-009 — Interactive audio

Later versions may support spoken question-and-answer revision where the learner responds and ARIA adapts the session.

## FR-AUDIO-010 — Source traceability

Where audio is generated from specific learner resources, the source context should remain identifiable.

---

# 18. Search

## FR-SEARCH-001 — Unified learning search

The learner shall be able to search across supported ARIA learning content.

## FR-SEARCH-002 — Searchable content

Search should eventually cover relevant chats, notes, resources, roadmaps, assessments, and other learning history.

## FR-SEARCH-003 — Context filters

The learner should be able to narrow search by relevant dimensions such as goal, content type, topic, or date where useful.

## FR-SEARCH-004 — Search result navigation

Selecting a result shall navigate the learner to the underlying item or appropriate context.

## FR-SEARCH-005 — Semantic retrieval

ARIA may support meaning-based retrieval in addition to exact keyword matching.

## FR-SEARCH-006 — Permission boundaries

Search results shall respect learner authorization and data-access boundaries.

---

# 19. Notifications & Reminders

## FR-NOTIF-001 — In-app notifications

ARIA shall support in-app notifications for relevant learning events.

## FR-NOTIF-002 — Email reminders

ARIA shall support email reminders for enabled notification types when the learner has a usable email address.

## FR-NOTIF-003 — Notification preferences

The learner shall be able to control notification channels and relevant categories.

## FR-NOTIF-004 — Planner reminders

Notifications may be triggered by upcoming planned learning sessions.

## FR-NOTIF-005 — Revision reminders

Notifications may be triggered by due/high-priority revision.

## FR-NOTIF-006 — Assessment reminders

Notifications may be triggered by scheduled assessments or relevant exam events.

## FR-NOTIF-007 — Deadline reminders

Notifications may be triggered by approaching deadlines where configured.

## FR-NOTIF-008 — Proposed-change notifications

ARIA may notify the learner when an important roadmap or plan change requires review.

## FR-NOTIF-009 — Frequency control

The learner shall have reasonable control over reminder frequency and unnecessary notification volume.

## FR-NOTIF-010 — Disable notifications

The learner shall be able to disable optional notification categories/channels.

## FR-NOTIF-011 — Actionable notification

Where appropriate, a notification should lead directly to the relevant learning action/context.

---

# 20. Settings & Learner Controls

## FR-SET-001 — Profile settings

The learner shall be able to view and edit relevant profile information.

## FR-SET-002 — Learning preferences

The learner shall be able to manage supported explicit learning preferences.

## FR-SET-003 — Notification settings

The learner shall be able to manage notification preferences.

## FR-SET-004 — Memory controls

The learner shall eventually be able to inspect/manage supported persistent memory information.

## FR-SET-005 — Learner-state correction

The learner should be able to correct important inaccurate learner-state assumptions through appropriate product surfaces.

## FR-SET-006 — Privacy/data controls

The learner shall have access to privacy and data-management controls defined in Step 6.

## FR-SET-007 — Integrations

Where external integrations exist, the learner shall be able to view/manage their connection state.

## FR-SET-008 — Accessibility preferences

Relevant accessibility preferences shall be configurable where required.

## FR-SET-009 — Account deletion

The learner shall be able to initiate account deletion according to later-defined privacy/security requirements.

---

# 21. Global Functional Requirements

## FR-GLOBAL-001 — Domain independence

ARIA's core experience shall not hardcode specific learning domains into the product model.

## FR-GLOBAL-002 — Multiple goals

Major systems shall be designed to operate correctly when a learner has multiple goals.

## FR-GLOBAL-003 — Context preservation

Connected features should preserve relevant learning context when moving between them.

## FR-GLOBAL-004 — Context correction

The learner shall be able to correct incorrectly assumed goal/topic/resource context.

## FR-GLOBAL-005 — User override

AI-generated structures and recommendations that are not inherently fixed system rules should remain editable/overridable where appropriate.

## FR-GLOBAL-006 — Empty states

ARIA shall not fabricate personalized information when insufficient data exists.

## FR-GLOBAL-007 — Graceful partial intelligence

Core features should remain useful even when advanced learner modeling or cross-system automation is unavailable.

## FR-GLOBAL-008 — Provenance

Where AI output materially depends on learner-provided resources or evidence, provenance should be preserved where appropriate.

## FR-GLOBAL-009 — Explainability

Significant adaptive decisions should have a reason that can be surfaced to the learner.

## FR-GLOBAL-010 — External ecosystem

ARIA may integrate or link to specialist external platforms instead of rebuilding them when that better serves the learner.

---

# 22. Functional Product Map

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

Later requirements will define the intelligence and event layer connecting these systems.

---

# 23. Example End-to-End Functional Scenario

A learner creates:

```text
Goal: Prepare for a university DBMS exam
Deadline: Friday
```

They upload their syllabus and class notes.

ARIA can then support:

```text
Create Goal
    ↓
Add Resources
    ↓
Generate / Edit Roadmap
    ↓
Create Plan
    ↓
Study Transactions
    ↓
Generate Revision Notes
    ↓
Create Assessment
    ↓
Learner chooses:
  - theory questions
  - 5 questions
  - 40 minutes
  - syllabus + class notes
    ↓
Take Assessment
    ↓
Receive Evaluation
    ↓
View Progress
    ↓
Revision / next action
    ↓
Receive relevant reminder
    ↓
Generate 15-minute audio revision before exam
```

This scenario uses several systems but does not yet define how automatic updates propagate between them. That belongs to Step 4.

---

# 24. Functional Scope Validation

The requirements in this document preserve the major Phase 0 decisions:

- ARIA remains goal-driven rather than domain-hardcoded;
- onboarding remains lightweight;
- deadlines are contextual and optional;
- multiple goals are supported;
- resources are learner-specific;
- Study is connected to resources and downstream learning material;
- Notes are editable and reusable;
- assessments are user-configurable rather than fixed-format;
- evaluation is separate from generation;
- roadmaps can evolve;
- planner supports recovery from missed work;
- revision is more than rereading;
- progress does not equal time spent;
- recommendations remain overridable;
- audio includes resource-to-audio and adaptive revision ambitions;
- reminders include email and in-app delivery;
- external specialist platforms can remain part of the learning ecosystem;
- learner control remains a core requirement.

---

# 25. Step 3 Completion

**Step 3 — Functional Requirements is complete.**

Next:

# Step 4 — Cross-System & Automation Requirements

Step 4 will define how these systems behave as one connected Learning OS.

It will specify requirements for interactions such as:

```text
AssessmentCompleted
        ↓
Evaluation
        ↓
Evidence
        ↓
Learner Model
        ↓
Progress
        ↓
Revision priority
        ↓
Roadmap adaptation check
        ↓
Planner adaptation check
        ↓
Recommendations
        ↓
Home
```

It will also define event boundaries, automatic vs approval-required actions, conflict handling, idempotency expectations, propagation rules, and how ARIA avoids turning cross-system automation into uncontrolled cascading AI changes.