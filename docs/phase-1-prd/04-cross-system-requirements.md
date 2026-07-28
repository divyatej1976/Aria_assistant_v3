# ARIA — Phase 1 PRD

## Step 4 — Cross-System & Automation Requirements

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Step 4 — Complete  
**Primary sources:** `VISION.md`, `01-product-overview-goals.md`, `02-user-context-requirements.md`, `03-functional-requirements.md`

---

# 1. Purpose

ARIA is not intended to be a collection of disconnected study tools. This document defines how its product systems must cooperate as one learning environment.

It specifies:

- cross-system events;
- context propagation;
- automatic actions;
- suggested actions;
- approval-required actions;
- evidence propagation;
- roadmap and planner adaptation;
- notification triggers;
- conflict handling;
- cascade limits;
- duplicate-event protection;
- auditability;
- failure isolation.

The central principle is:

> **ARIA may automate coordination, but important learning decisions must remain traceable, bounded, and correctable.**

This document defines product behaviour, not the eventual event-bus, queue, workflow engine, agent framework, or database implementation.

---

# 2. Cross-System Model

A typical ARIA learning loop may behave conceptually as follows:

```text
Goal / Context
      ↓
Study / Resources
      ↓
Practice / Assessment
      ↓
Evaluation
      ↓
Evidence
      ↓
Learner Model
      ↓
┌────────────┬────────────┬──────────────┐
│            │            │              │
Progress   Revision     Roadmap     Recommendations
│            │            │              │
└────────────┴──────┬─────┴──────────────┘
                    ↓
                 Planner
                    ↓
                  Home
                    ↓
              Notifications
                    ↓
             Next learning action
                    ↓
                   ↺
```

Not every event must trigger every downstream system.

---

# 3. Requirement Categories

```text
XR-EVT-*       Cross-system events
XR-CTX-*       Context propagation
XR-EVD-*       Evidence propagation
XR-AUTO-*      Automation rules
XR-HITL-*      Human-in-the-loop rules
XR-ROAD-*      Roadmap adaptation
XR-PLAN-*      Planner adaptation
XR-REV-*       Revision propagation
XR-REC-*       Recommendation propagation
XR-HOME-*      Home propagation
XR-NOTIF-*     Notification propagation
XR-CONFLICT-*  Conflict handling
XR-SAFE-*      Cascade safety
XR-IDEMP-*     Duplicate/idempotency behaviour
XR-AUDIT-*     Traceability/auditability
XR-FAIL-*      Failure isolation/recovery
```

---

# 4. Event Requirements

## XR-EVT-001 — Meaningful state changes

ARIA shall be capable of representing meaningful state changes as cross-system events or equivalent workflow signals.

## XR-EVT-002 — Event context

Cross-system signals shall carry enough context to identify the learner, relevant goal/context, originating action, and affected entity where required.

## XR-EVT-003 — Event provenance

ARIA should retain the origin of consequential events so downstream decisions can be traced back to their source.

## XR-EVT-004 — Event timestamps

Meaningful cross-system events shall retain temporal information sufficient for ordering and auditability.

## XR-EVT-005 — Version/change awareness

Where an event refers to mutable state, ARIA should be able to determine whether the underlying state has changed since the event was produced.

## XR-EVT-006 — User vs system origin

ARIA should distinguish whether a meaningful state change originated from the learner, deterministic product logic, or AI-generated reasoning.

---

# 5. Core Product Events

The exact technical names may change later, but ARIA shall support equivalent product-level state transitions.

```text
GoalCreated
GoalUpdated
GoalPaused
GoalResumed
GoalCompleted

ResourceAdded
ResourceReady
ResourceProcessingFailed

StudySessionStarted
StudySessionCompleted
TeachBackCompleted

NoteCreated
NoteUpdated

AssessmentCreated
AssessmentStarted
AssessmentSubmitted
AssessmentEvaluated

EvidenceRecorded
LearnerStateChanged
PossibleMisconceptionDetected
PrerequisiteGapDetected

RoadmapCreated
RoadmapChangeProposed
RoadmapChangeAccepted
RoadmapChangeRejected
RoadmapUpdated

PlanCreated
PlanChanged
PlannedSessionCompleted
PlannedSessionMissed
PlanRecoveryProposed
PlanRecoveryAccepted

RevisionScheduled
RevisionDue
RevisionCompleted

RecommendationCreated
RecommendationDismissed
RecommendationCompleted

DeadlineApproaching
NotificationRequested
```

These are conceptual events, not final API or code contracts.

---

# 6. Context Propagation

## XR-CTX-001 — Preserve active context

When the learner moves between connected features, relevant goal, topic, resource, and activity context should propagate automatically where appropriate.

## XR-CTX-002 — Explicit override wins

The learner's current explicit context selection shall override inferred propagated context.

## XR-CTX-003 — Context scope

ARIA shall not propagate context beyond the scope where it remains valid.

## XR-CTX-004 — Context provenance

Where consequential, downstream systems should know whether context was explicitly selected, inherited, or inferred.

## XR-CTX-005 — Context correction propagation

When the learner corrects an incorrectly associated goal/topic context, future downstream actions shall use the corrected context.

## XR-CTX-006 — Historical integrity

Correcting current context shall not silently rewrite historical records whose original context remains factually accurate.

## XR-CTX-007 — Multi-goal isolation

Context propagation shall preserve goal boundaries unless an action intentionally operates across goals.

---

# 7. Evidence Propagation

## XR-EVD-001 — Structured evidence

Supported learning activities shall be capable of producing structured evidence rather than only human-readable feedback.

## XR-EVD-002 — Evidence source

Evidence shall retain its source activity, such as assessment, teach-back, revision attempt, or other supported learning interaction.

## XR-EVD-003 — Evidence scope

Evidence shall identify the relevant concept/topic/skill and goal/context where applicable.

## XR-EVD-004 — Evidence strength

Evidence should carry information sufficient for later systems to distinguish stronger from weaker signals.

## XR-EVD-005 — Evidence does not equal state

Recording evidence shall not automatically mean a learner-state conclusion has been proven.

## XR-EVD-006 — Repeated evidence

ARIA shall support accumulating evidence over time rather than replacing all prior evidence with the latest interaction.

## XR-EVD-007 — Contradictory evidence

ARIA shall support conflicting evidence without silently discarding inconvenient signals.

## XR-EVD-008 — Downstream availability

Relevant evidence shall be available to systems responsible for Learner Model updates, progress, revision, recommendations, roadmap adaptation, and planning where appropriate.

---

# 8. Automation Classes

ARIA shall distinguish at least three product-level automation classes.

### Class A — Automatic

Low-risk, reversible coordination actions may occur automatically.

Examples:

```text
Save assessment result
Record evidence
Update a visible progress calculation
Mark a completed planned session
Surface due revision
Refresh Home recommendations
```

### Class B — Automatic + visible

ARIA may perform an action automatically, but the resulting change should be visible and explainable.

Examples may include:

```text
Adjust revision priority
Update a readiness estimate
Refresh recommendation ordering
```

### Class C — Proposal / approval

Consequential changes should normally be proposed rather than silently applied.

Examples:

```text
Major roadmap restructuring
Dropping a roadmap topic
Moving many scheduled sessions
Changing a goal deadline
Changing learner-declared priority
Replacing learner-selected assessment rules
```

The precise classification of individual behaviours will be refined during architecture and UX design.

---

# 9. General Automation Requirements

## XR-AUTO-001 — Automate coordination, not agency

ARIA should automate repetitive coordination while preserving learner control over consequential choices.

## XR-AUTO-002 — Reason requirement

Meaningful adaptive actions shall retain an internal reason that can be surfaced where appropriate.

## XR-AUTO-003 — Evidence requirement

Adaptive actions based on learner understanding should be supported by relevant evidence rather than unsupported model assumptions.

## XR-AUTO-004 — Minimum confidence

ARIA should avoid triggering consequential automatic adaptation from low-confidence conclusions.

## XR-AUTO-005 — Reversibility

Automatically applied non-trivial changes should be reversible where practical.

## XR-AUTO-006 — Bounded scope

An automation should modify only the systems/state necessary for its intended purpose.

## XR-AUTO-007 — No hidden chain reaction

A single event shall not trigger an unbounded chain of opaque AI modifications.

## XR-AUTO-008 — Learner instruction precedence

Current explicit learner instructions shall override conflicting automated assumptions unless doing so would violate a hard product/security constraint.

---

# 10. Human-in-the-Loop Requirements

## XR-HITL-001 — Review significant changes

ARIA shall provide a review path for significant proposed roadmap/planner changes where appropriate.

## XR-HITL-002 — Explain proposal

A proposal should explain what will change and why.

## XR-HITL-003 — Accept

The learner shall be able to accept a proposal.

## XR-HITL-004 — Reject

The learner shall be able to reject a proposal.

## XR-HITL-005 — Modify

Where practical, the learner should be able to modify a proposal before accepting it.

## XR-HITL-006 — No punishment for rejection

Rejecting an ARIA recommendation shall not create misleading negative learner-state evidence.

## XR-HITL-007 — Correction

The learner shall be able to correct important inaccurate assumptions that influenced a proposal.

---

# 11. Assessment → Evaluation → Evidence

## XR-EVD-009 — Assessment submission trigger

Submitting an assessment shall make the attempt available for evaluation.

## XR-EVD-010 — Evaluation completion

Successful evaluation shall produce user-facing results and, where appropriate, structured learning evidence.

## XR-EVD-011 — Format-aware evidence

Evidence strength and interpretation shall account for assessment format and evaluation reliability.

## XR-EVD-012 — Partial evaluation

If only part of an assessment can be reliably evaluated, ARIA shall not treat unevaluated portions as known performance.

## XR-EVD-013 — Evaluation correction

If an evaluation is later corrected, dependent evidence and derived learner-state conclusions should be capable of being revised.

---

# 12. Evidence → Learner Model → Progress

## XR-EVD-014 — Learner-state update check

New evidence shall be eligible to trigger a learner-state update evaluation.

## XR-EVD-015 — State transition threshold

ARIA should require sufficient evidence/confidence before making strong learner-state transitions such as "mastered" or "misconception confirmed."

## XR-EVD-016 — Progress refresh

Meaningful learner-state changes should update relevant progress views.

## XR-EVD-017 — Untested preservation

Lack of evidence shall not automatically be converted into weakness.

## XR-EVD-018 — Provenance access

Important learner-state conclusions should remain traceable to supporting evidence.

---

# 13. Learner Model → Revision

## XR-REV-001 — Weakness can influence revision

Evidence-backed weakness may increase revision priority.

## XR-REV-002 — Misconception remediation

A sufficiently supported possible misconception may trigger a targeted remediation/revision recommendation.

## XR-REV-003 — Prerequisite remediation

A detected prerequisite gap may trigger a recommendation to review the prerequisite before continuing dependent material.

## XR-REV-004 — Strong evidence can reduce unnecessary repetition

Strong and repeated evidence may reduce immediate revision priority, subject to forgetting/retrieval considerations.

## XR-REV-005 — Revision completion creates new evidence

Revision activities that test recall/understanding should be capable of generating new evidence.

## XR-REV-006 — Revision loop

ARIA shall support:

```text
Weakness detected
      ↓
Revision recommended
      ↓
Revision performed
      ↓
Retest / retrieval
      ↓
New evidence
      ↓
Learner state reconsidered
```

---

# 14. Learner Model → Roadmap

## XR-ROAD-001 — Adaptation check

Meaningful learner-state changes may trigger a roadmap adaptation check.

## XR-ROAD-002 — Do not rewrite on every result

ARIA shall not restructure the roadmap after every individual assessment result.

## XR-ROAD-003 — Prerequisite insertion proposal

Strong evidence of a prerequisite gap may cause ARIA to propose adding/reordering prerequisite work.

## XR-ROAD-004 — Weak topic reinforcement

Persistent weakness may cause ARIA to propose additional learning or practice before advancing.

## XR-ROAD-005 — Strong mastery acceleration

Strong evidence may allow ARIA to propose reducing redundant work or advancing faster where appropriate.

## XR-ROAD-006 — Explain roadmap change

Roadmap proposals shall state the relevant evidence/context that motivated them in learner-understandable terms.

## XR-ROAD-007 — Significant changes require review

Major roadmap restructuring should normally require learner approval.

## XR-ROAD-008 — Accepted change propagation

Once a roadmap change is accepted, downstream planner/recommendation systems should be able to react to the updated roadmap.

---

# 15. Roadmap → Planner

## XR-PLAN-001 — Schedule roadmap work

The planner shall be capable of scheduling actionable roadmap items.

## XR-PLAN-002 — Accepted roadmap changes

Accepted roadmap changes should trigger a planning impact check.

## XR-PLAN-003 — Avoid immediate destructive rescheduling

A roadmap update shall not automatically destroy the learner's existing plan without evaluating impact.

## XR-PLAN-004 — Minor vs major impact

Small scheduling adjustments may be automated where reversible; substantial rescheduling should be proposed.

## XR-PLAN-005 — Preserve completed work

Planner adaptation shall not reschedule work already completed unless explicitly required for revision.

---

# 16. Missed Work → Plan Recovery

## XR-PLAN-006 — Missed session event

A missed planned session shall be eligible to trigger a recovery check.

## XR-PLAN-007 — No endless overdue pile

ARIA should prefer feasible replanning over simply accumulating overdue tasks indefinitely.

## XR-PLAN-008 — Recovery factors

Plan recovery may consider:

- remaining time;
- deadlines;
- goal priority;
- roadmap dependencies;
- revision needs;
- available time;
- already completed work.

## XR-PLAN-009 — Significant recovery proposal

When recovery requires substantial changes, ARIA should present a proposed plan change.

## XR-PLAN-010 — Explain movement

The learner should be able to understand what was moved, removed, shortened, or reprioritized and why.

---

# 17. Recommendations

## XR-REC-001 — Recommendation refresh

Meaningful changes in goal state, plan state, learner state, deadlines, or revision priority may trigger recommendation refresh.

## XR-REC-002 — Recommendation ranking

ARIA should prioritize recommendations using relevant context rather than presenting all possible actions equally.

## XR-REC-003 — Recommendation provenance

A recommendation should retain the factors that caused it to be surfaced.

## XR-REC-004 — No false personalization

When learner evidence is insufficient, ARIA shall avoid presenting generic recommendations as highly personalized conclusions.

## XR-REC-005 — Dismissal

The learner shall be able to dismiss recommendations where appropriate.

## XR-REC-006 — Dismissal is not failure

Dismissal alone shall not be treated as evidence that the learner cannot perform the recommended topic.

---

# 18. Home Synchronization

## XR-HOME-001 — Aggregated state

Home shall reflect relevant current state from Goals, Planner, Revision, Progress, Recommendations, and deadlines.

## XR-HOME-002 — Eventual refresh

Meaningful state changes should be reflected on Home within an appropriate product timeframe.

## XR-HOME-003 — No stale high-priority action

Completed or invalidated high-priority actions should not remain prominently recommended after the system has processed the change.

## XR-HOME-004 — Explain recommendation

Home recommendations should provide a concise reason where useful.

## XR-HOME-005 — Multi-goal awareness

Home shall be capable of presenting prioritized work across multiple goals without merging their learning state incorrectly.

---

# 19. Notifications

## XR-NOTIF-001 — Event-driven reminder eligibility

Relevant planner, revision, deadline, assessment, and proposal events may create notification requests.

## XR-NOTIF-002 — Preference gate

A notification shall respect learner channel/category preferences before delivery.

## XR-NOTIF-003 — Deduplication

ARIA should avoid sending duplicate notifications for the same meaningful event.

## XR-NOTIF-004 — Stale notification prevention

If the underlying action is completed, cancelled, or materially changed before delivery, ARIA should suppress or update the notification where feasible.

## XR-NOTIF-005 — Action context

Actionable notifications should preserve enough context to take the learner to the relevant item.

## XR-NOTIF-006 — No notification cascade

One learner action should not cause multiple redundant notifications from several downstream systems.

---

# 20. Conflict Handling

## XR-CONFLICT-001 — Explicit user change wins

When a recent learner edit conflicts with an older automated proposal, the learner's explicit change shall normally take precedence.

## XR-CONFLICT-002 — Concurrent change detection

ARIA should detect when a proposal was generated from stale state before applying it.

## XR-CONFLICT-003 — Multi-goal scheduling conflicts

Planner automation shall account for competing commitments across active goals.

## XR-CONFLICT-004 — Contradictory evidence

Conflicting learning evidence should reduce confidence or trigger further assessment rather than forcing an arbitrary conclusion.

## XR-CONFLICT-005 — Preference conflicts

Context-specific explicit preferences shall take precedence over conflicting global defaults for that context.

## XR-CONFLICT-006 — User correction propagation

When the learner corrects an assumption, dependent future decisions should use the corrected information.

---

# 21. Cascade Safety

## XR-SAFE-001 — Bounded propagation

Each automation chain shall have defined stopping conditions.

## XR-SAFE-002 — No recursive self-triggering loops

A system update shall not repeatedly trigger itself or equivalent downstream actions without new meaningful state.

## XR-SAFE-003 — Consequential action boundary

Automation shall stop at an approval boundary when a consequential learner decision requires review.

## XR-SAFE-004 — Confidence degradation

Uncertain upstream outputs shall not become more certain merely because they passed through multiple downstream systems.

## XR-SAFE-005 — Derived-state distinction

ARIA should distinguish source evidence from derived conclusions and recommendations.

## XR-SAFE-006 — Maximum adaptation scope

A single weak signal shall not be allowed to rewrite large portions of a learner's roadmap and planner.

## XR-SAFE-007 — No agent authority escalation

An AI component shall not gain permission to perform a higher-impact action merely because another AI component recommended it.

---

# 22. Duplicate Processing / Idempotency Requirements

## XR-IDEMP-001 — Duplicate event safety

Repeated processing of the same logical event shall not create duplicate consequential state where avoidable.

## XR-IDEMP-002 — Assessment submission

The same assessment submission shall not accidentally create multiple attempts/evidence records because of retries.

## XR-IDEMP-003 — Notification request

Retrying notification processing shall not produce duplicate user notifications.

## XR-IDEMP-004 — Proposal generation

ARIA should avoid generating multiple equivalent pending roadmap/planner proposals from the same unchanged evidence state.

## XR-IDEMP-005 — Safe retries

Cross-system operations should be designed so transient failures can be retried safely.

---

# 23. Auditability & Explainability

## XR-AUDIT-001 — Consequential change record

Significant system-generated changes/proposals should retain:

```text
what changed
when
why
originating event/context
supporting evidence where relevant
whether it was automatic or approved
```

## XR-AUDIT-002 — Proposal decision

ARIA should retain whether a significant proposal was accepted, rejected, modified, or expired where useful.

## XR-AUDIT-003 — Learner-facing explanation

Internal technical traces need not be exposed directly, but ARIA should be able to translate relevant reasoning into concise learner-facing explanations.

## XR-AUDIT-004 — Evidence trace

Important learner-state conclusions should be traceable to their supporting evidence.

## XR-AUDIT-005 — No fabricated explanation

ARIA shall not generate a plausible-sounding reason that is disconnected from the actual factors used by the system.

---

# 24. Failure Isolation & Recovery

## XR-FAIL-001 — Failure isolation

Failure of one downstream system shall not unnecessarily invalidate successful upstream work.

Example:

If an assessment is successfully submitted and evaluated but recommendation generation fails, the assessment result shall remain preserved.

## XR-FAIL-002 — Partial workflow status

ARIA should be capable of representing partially completed workflows rather than treating them as entirely failed.

## XR-FAIL-003 — Retryable operations

Transient downstream failures should be retryable where safe.

## XR-FAIL-004 — No fabricated success

ARIA shall not present a downstream update as completed when the operation actually failed.

## XR-FAIL-005 — User-facing degradation

Where a non-critical automation fails, the learner should still be able to use unaffected core functionality.

## XR-FAIL-006 — Recovery from stale proposals

A proposal generated from obsolete state should be invalidated or recomputed before application.

## XR-FAIL-007 — Preserve source data

Derived-system failure shall not delete the original learner action/evidence that caused the workflow.

---

# 25. Example Workflow — Assessment Adaptation

```text
Learner completes DBMS assessment
             ↓
AssessmentSubmitted
             ↓
Evaluation succeeds
             ↓
AssessmentEvaluated
             ↓
Evidence recorded:
  Transactions: strong
  Serializability: weak
             ↓
Learner Model update check
             ↓
Existing evidence also shows repeated
Serializability difficulty
             ↓
Confidence becomes sufficient to mark
Serializability as weak
             ↓
Progress refreshes
             ↓
Revision priority increases
             ↓
Roadmap adaptation check
             ↓
ARIA proposes:
"Add one targeted Serializability practice
session before the next Transactions unit."
             ↓
Learner reviews proposal
       ↙            ↘
    Accept          Reject
      ↓               ↓
Roadmap updates    Roadmap unchanged
      ↓
Planner impact check
      ↓
Minor schedule change OR proposal
      ↓
Home recommendation refreshes
```

One assessment answer alone does not necessarily cause this entire chain. Evidence thresholds and confidence matter.

---

# 26. Example Workflow — Missed Study Session

```text
Planned DBMS session missed
          ↓
Plan recovery check
          ↓
ARIA checks:
- exam date
- remaining roadmap work
- tomorrow's availability
- other active goals
- revision due
          ↓
ARIA creates recovery proposal
          ↓
"Move Transactions to tomorrow,
shorten review from 60 to 40 minutes,
and keep Friday's mock exam unchanged."
          ↓
Learner accepts / modifies / rejects
          ↓
Plan updates
          ↓
Home + reminders synchronize
```

ARIA should not simply create another overdue task and leave the learner to reorganize everything manually.

---

# 27. Example Workflow — Resource Failure

```text
Learner uploads notes.pdf
          ↓
ResourceAdded
          ↓
Processing fails
          ↓
ResourceProcessingFailed
          ↓
Resource UI shows failure + retry path
```

Unrelated goals, chats, notes, assessments, and planner functions remain available.

No learner-state conclusion is generated from the failed resource.

---

# 28. Example Workflow — User Correction

```text
ARIA infers:
"Operating Systems question belongs to GATE goal"
          ↓
Learner says:
"No, this is for my university exam."
          ↓
Active context corrected
          ↓
Future notes/assessment/evidence from this
session use University Exam context
          ↓
Old valid GATE history remains unchanged
```

---

# 29. Automation Decision Matrix

| Change | Default Product Behaviour |
|---|---|
| Save assessment attempt | Automatic |
| Record evaluation evidence | Automatic |
| Refresh progress calculation | Automatic |
| Surface due revision | Automatic |
| Re-rank recommendation | Automatic + visible |
| Adjust revision priority | Automatic + visible |
| Suggest prerequisite review | Recommendation |
| Add minor optional practice | Recommendation / proposal |
| Major roadmap restructuring | Approval required |
| Drop roadmap topic | Approval required |
| Large planner reschedule | Approval required |
| Change learner-declared deadline | Explicit learner action / approval |
| Change learner-declared goal priority | Explicit learner action / approval |
| Replace assessment specification | Learner confirmation required |

This matrix is a PRD default, not a final implementation contract.

---

# 30. Step 4 Decisions

This step establishes several critical ARIA principles:

1. **Events connect systems; they do not give every system unlimited authority.**
2. **Evidence is preserved separately from conclusions.**
3. **Low-risk coordination may be automatic.**
4. **Consequential learning-path changes require visibility and often approval.**
5. **One weak signal must not cascade into major roadmap/planner changes.**
6. **Explicit learner instructions outrank stale or inferred context.**
7. **Automation must be bounded, retry-safe, traceable, and failure-isolated.**
8. **ARIA should recover from missed work instead of creating an endless overdue backlog.**
9. **Notifications are downstream communication, not a reason to spam the learner.**
10. **The system must be able to explain meaningful adaptive behaviour using the real factors that caused it.**

---

# 31. Step 4 Completion

**Step 4 — Cross-System & Automation Requirements is complete.**

Next:

# Step 5 — AI, Learner Model, Memory & Evidence Requirements

Step 5 will define the intelligence layer in depth:

```text
AI behaviour boundaries
        ↓
Task decomposition
        ↓
Tool use
        ↓
Context management
        ↓
Memory
        ↓
Evidence model
        ↓
Learner Model
        ↓
Mastery / weakness / unknown state
        ↓
Misconception detection
        ↓
Prerequisite gaps
        ↓
Confidence / uncertainty
        ↓
Generate–Validate–Fix patterns
        ↓
Human correction
        ↓
AI failure behaviour
```

This is where ARIA's learning intelligence is specified before any agent architecture is chosen.