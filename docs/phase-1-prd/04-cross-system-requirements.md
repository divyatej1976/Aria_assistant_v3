# ARIA — Phase 1 PRD

## Step 4 — Cross-System & Automation Requirements

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Reviewed and release-classified  
**Primary sources:** `VISION.md`, Steps 1–3 and 7–8

---

# 1. Purpose

ARIA is not intended to become a collection of disconnected AI study tools. This document defines how product systems cooperate while separating the **small R0 adaptive-learning chain** from later Learning OS orchestration.

Central principle:

> **ARIA may automate coordination, but automation must be evidence-aware, bounded, traceable, retry-safe, failure-isolated, and correctable.**

This is product behaviour, not a decision to use an event bus, agent framework, workflow engine, queue, or any specific architecture.

---

# 2. Release Labels

- **R0 MUST** — required to validate the first adaptive-learning loop.
- **R1+** — Roadmap / learning-path adaptation.
- **R2+** — longitudinal Revision / Progress / richer Learner Model loops.
- **R3+** — Planner, multi-goal coordination, Home, reminders.
- **R4+** — richer learning interfaces such as Notes/Audio.
- **R5+** — mature cross-system orchestration/integrations.
- **LONG-TERM MUST** — product principle whose exact release may be determined later.

---

# 3. R0 Cross-System Chain

R0 needs one bounded closed loop:

```text
Goal / Context
      ↓
Resources + Study
      ↓
AssessmentSubmitted
      ↓
Evaluation
      ↓
EvidenceRecorded
      ↓
Basic Learner State update check
      ↓
Adaptation decision
      ↓
Adapted Study
      ↓
Targeted Reassessment
      ↓
New Evidence
      ↓
Learner State reconsidered
      ↺
```

R0 does **not** require the same event to fan out into Progress + Revision + Roadmap + Planner + Home + Notifications.

---

# 4. Requirement Categories

```text
XR-EVT-*       Cross-system signals/events
XR-CTX-*       Context propagation
XR-EVD-*       Evidence propagation
XR-ADAPT-*     R0 adaptive-study propagation
XR-AUTO-*      Automation rules
XR-HITL-*      Human control
XR-ROAD-*      Roadmap adaptation (R1+)
XR-REV-*       Revision/progress loops (R2+)
XR-PLAN-*      Planner coordination (R3+)
XR-HOME-*      Home synchronization (R3+)
XR-NOTIF-*     Notifications (R3+)
XR-CONFLICT-*  Conflict handling
XR-SAFE-*      Cascade safety
XR-IDEMP-*     Duplicate/idempotency behaviour
XR-AUDIT-*     Traceability
XR-FAIL-*      Failure isolation/recovery
```

---

# 5. Event / Workflow-Signal Requirements

## XR-EVT-001 — Meaningful state transitions — R0 MUST
ARIA shall represent meaningful R0 state transitions using events or an equivalent explicit workflow mechanism.

## XR-EVT-002 — Event context — R0 MUST
A consequential R0 signal shall carry enough information to identify the learner, validation context, originating action, affected entity/concept, and relevant identifiers.

## XR-EVT-003 — Provenance — R0 MUST
Consequential signals shall retain their origin so derived state can be traced backward.

## XR-EVT-004 — Temporal information — R0 MUST
R0 state changes shall retain timestamps/order information sufficient for repeated-cycle validation and auditability.

## XR-EVT-005 — Version/change awareness — R0 MUST WHERE APPLICABLE
ARIA shall avoid applying derived changes against known stale mutable state.

## XR-EVT-006 — Origin type — R0 MUST
Where consequential, ARIA shall distinguish learner-originated, deterministic-system, and AI-derived changes.

---

# 6. Product Events by Release

The names below are conceptual, not final API contracts.

## R0 core

```text
ResourceAdded
ResourceReady
ResourceProcessingFailed
StudySessionStarted
StudySessionCompleted
AssessmentCreated
AssessmentStarted
AssessmentSubmitted
AssessmentEvaluated
EvaluationCorrected
EvidenceRecorded
EvidenceCorrected
LearnerStateUpdated
AdaptationCreated
AdaptedStudyStarted
ReassessmentSubmitted
```

## R1+

```text
RoadmapCreated
RoadmapChangeProposed
RoadmapChangeAccepted
RoadmapChangeRejected
RoadmapUpdated
```

## R2+

```text
PossibleMisconceptionDetected
PrerequisiteGapDetected
RevisionScheduled
RevisionDue
RevisionCompleted
ProgressUpdated
```

## R3+

```text
GoalPriorityChanged
PlanCreated
PlanChanged
PlannedSessionCompleted
PlannedSessionMissed
PlanRecoveryProposed
PlanRecoveryAccepted
RecommendationCreated
RecommendationDismissed
DeadlineApproaching
NotificationRequested
```

## R4/R5+

Notes, Audio and integration-specific workflow signals are introduced when those systems enter scope.

---

# 7. Context Propagation

## XR-CTX-001 — Preserve R0 context — R0 MUST
Relevant goal/context, topic/concept, selected resources and activity context shall propagate through Study → Assessment → Evaluation → Evidence → Learner State → Adapted Study.

## XR-CTX-002 — Explicit override wins — R0 MUST
Current explicit learner context selection shall override conflicting inferred/inherited context.

## XR-CTX-003 — Scope boundaries — R0 MUST
Context shall not propagate beyond the scope where it remains valid.

## XR-CTX-004 — Context provenance — R0 MUST
Consequential downstream state should identify whether context was explicit, inherited, or inferred.

## XR-CTX-005 — Correction propagation — R0 MUST
Future dependent R0 actions shall use corrected context.

## XR-CTX-006 — Historical integrity — R0 MUST
A current correction shall not silently rewrite factually valid historical records.

## XR-CTX-007 — Multi-goal isolation — LONG-TERM MUST
When multi-goal support exists, goal boundaries shall be preserved unless an operation intentionally spans goals.

---

# 8. Assessment → Evaluation → Evidence

## XR-EVD-001 — Assessment submission trigger — R0 MUST
A valid submission shall make exactly one logical attempt available for evaluation despite safe retries.

## XR-EVD-002 — Evaluation output — R0 MUST
Successful evaluation shall produce learner-facing results and structured machine-usable output where reliable.

## XR-EVD-003 — Evidence source — R0 MUST
Evidence shall retain the source attempt/response/evaluation from which it originated.

## XR-EVD-004 — Evidence scope — R0 MUST
Evidence shall identify relevant concept/topic/skill and validation context.

## XR-EVD-005 — Evidence strength/reliability — R0 MUST
Evidence shall carry enough information to avoid treating every signal as equally strong.

## XR-EVD-006 — Evidence does not equal learner state — R0 MUST
Recording one evidence item shall not automatically prove a mastery, weakness, or misconception conclusion.

## XR-EVD-007 — Partial evaluation — R0 MUST
Unevaluated or unreliable portions shall remain unknown rather than becoming false negative evidence.

## XR-EVD-008 — Evaluation correction — R0 MUST
If an evaluation is corrected, dependent evidence and derived state shall be capable of recomputation/correction.

## XR-EVD-009 — Repeated evidence — R0 MUST
ARIA shall accumulate evidence across validation cycles rather than replacing history with the latest result.

## XR-EVD-010 — Contradictory evidence — R0 MUST
Conflicting evidence shall be preserved and should reduce certainty or motivate further testing rather than being silently discarded.

---

# 9. Evidence → Basic Learner State

## XR-EVD-011 — State update check — R0 MUST
New valid evidence shall be eligible to trigger a learner-state update evaluation.

## XR-EVD-012 — Conservative state transition — R0 MUST
Strong learner-state claims shall require sufficient supporting evidence/confidence under Step 5 rules.

## XR-EVD-013 — Unknown preservation — R0 MUST
Lack of evidence shall remain unknown/insufficiently tested rather than automatically becoming weakness.

## XR-EVD-014 — Provenance access — R0 MUST
Important state conclusions shall remain traceable to supporting evidence.

## XR-EVD-015 — State is revisable — R0 MUST
New or corrected evidence may strengthen, weaken, or overturn an earlier learner-state estimate.

## XR-EVD-016 — No activity-as-mastery shortcut — R0 MUST
Completing Study or spending time in ARIA shall not itself become proof of understanding.

---

# 10. Learner State → Adapted Study

This is the most important R0 cross-system boundary.

## XR-ADAPT-001 — Adaptation eligibility — R0 MUST
A supported learner-state signal may trigger consideration of a changed next Study experience.

## XR-ADAPT-002 — Adaptation must use evidence/state — R0 MUST
An adaptive Study decision shall reference relevant learner-state/evidence rather than being an untraceable generic LLM variation.

## XR-ADAPT-003 — Material adaptation — R0 MUST
The adapted Study experience shall be meaningfully different when the evidence warrants it.

Possible adaptations include:

```text
change explanation depth
change example/scaffolding
focus on a weak concept
revisit a prerequisite
add targeted practice
ask a diagnostic question
reduce unnecessary repetition where evidence is strong
```

## XR-ADAPT-004 — Bounded adaptation — R0 MUST
An R0 adaptation shall affect only the next supported learning action(s) necessary to test the hypothesis. It shall not silently restructure future Roadmaps/Plans that do not exist in R0.

## XR-ADAPT-005 — Reason — R0 MUST
The actual factors behind an adaptation shall be stored in a form that can be inspected/tested and translated into a learner-facing explanation where appropriate.

## XR-ADAPT-006 — Uncertain state behaviour — R0 MUST
When evidence is weak or contradictory, ARIA should prefer diagnostic/reassessment behaviour over pretending it knows the learner's weakness with high certainty.

## XR-ADAPT-007 — User override — R0 MUST
The learner may choose another supported action without that override becoming negative learning evidence.

---

# 11. Adapted Study → Reassessment → New Evidence

## XR-ADAPT-008 — Reassessment path — R0 MUST
ARIA shall support a subsequent assessment/reassessment capable of testing the concept affected by the adaptation.

## XR-ADAPT-009 — Comparable attribution — R0 MUST
The system shall preserve enough concept/context information to compare evidence before and after the adaptive intervention without claiming causality from comparison alone.

## XR-ADAPT-010 — New evidence independence — R0 MUST
Reassessment results shall be recorded as new evidence, not overwrite the earlier attempt.

## XR-ADAPT-011 — Reconsider state — R0 MUST
New evidence shall cause the relevant learner-state estimate to be reconsidered under the same evidence/confidence rules.

## XR-ADAPT-012 — Loop closure observable — R0 MUST
Gate A tests shall be able to demonstrate that:

```text
Evidence A
   ↓
Learner State A
   ↓
Adaptation chosen because of A
   ↓
Adapted Study
   ↓
Evidence B
   ↓
Learner State reconsidered
```

The system must make this chain observable enough to verify mechanically or through controlled inspection.

---

# 12. R0 Automation Classes

R0 distinguishes three product-level classes.

### Class A — Automatic

Low-risk state bookkeeping may occur automatically:

```text
save assessment attempt
persist evaluation
record valid structured evidence
run learner-state update check
persist adaptation provenance
```

### Class B — Automatic + visible/inspectable

```text
update basic learner-state estimate
select/re-rank an adapted next Study action
```

These changes may happen automatically because R0 is specifically testing adaptation, but they must remain traceable and correctable.

### Class C — Learner confirmation / explicit action

```text
change learner-declared context
replace learner-selected assessment specification
make consequential account/data changes
```

Later Roadmap/Planner approval classes remain part of R1/R3 requirements.

---

# 13. General Automation Rules

## XR-AUTO-001 — Automate coordination, not unlimited agency — R0 MUST
## XR-AUTO-002 — Real reason — R0 MUST
Meaningful adaptive actions shall retain the real reason that caused them.

## XR-AUTO-003 — Evidence requirement — R0 MUST
Understanding-based adaptations shall use relevant evidence/state.

## XR-AUTO-004 — Confidence awareness — R0 MUST
Low-confidence conclusions shall not trigger unsupported high-confidence adaptations.

## XR-AUTO-005 — Reversibility/correction — R0 MUST WHERE PRACTICAL
## XR-AUTO-006 — Bounded scope — R0 MUST
## XR-AUTO-007 — No hidden chain reaction — R0 MUST
## XR-AUTO-008 — Explicit learner instruction precedence — R0 MUST

---

# 14. Human-in-the-Loop

## XR-HITL-001 — Correction path — R0 MUST
The learner/tester shall have an appropriate path to correct consequential inaccurate context/evaluation/state assumptions.

## XR-HITL-002 — Explain adaptation — R0 MUST
ARIA shall be capable of explaining why an adaptive Study action was chosen.

## XR-HITL-003 — Override — R0 MUST
A learner may ignore/override a recommended next action.

## XR-HITL-004 — Override is not failure — R0 MUST
Rejecting an ARIA recommendation shall not become evidence of inability.

## XR-HITL-005 — Later proposal workflow — R1/R3+
Roadmap/Planner proposals shall eventually support accept/reject/modify and explanation.

---

# 15. Roadmap Adaptation — R1+

R1 extends the proven R0 learner-state mechanism into learning-path adaptation.

Preserved requirements:

- **XR-ROAD-001** meaningful learner-state change may trigger adaptation check;
- **XR-ROAD-002** do not rewrite after every result;
- **XR-ROAD-003** prerequisite insertion/reordering proposal;
- **XR-ROAD-004** persistent weakness reinforcement;
- **XR-ROAD-005** strong-evidence acceleration;
- **XR-ROAD-006** explain proposal using real evidence/context;
- **XR-ROAD-007** significant restructuring normally requires review;
- **XR-ROAD-008** accepted changes can propagate downstream later.

---

# 16. Revision & Longitudinal Learning — R2+

R2 turns immediate R0 adaptation into learning across time.

Preserved requirements:

- evidence-backed weakness may influence Revision priority;
- supported misconception/prerequisite signals may trigger remediation;
- strong repeated evidence may reduce unnecessary immediate repetition;
- retrieval/revision activities can generate new evidence;
- new evidence reconsiders learner state;
- Progress distinguishes unknown, weak, improving and supported states according to Step 5 rules.

R0's immediate `Adapted Study → Reassessment` loop is not the full Revision product.

---

# 17. Planner / Missed-Work Recovery — R3+

Preserved long-term requirements include:

- schedule actionable Roadmap work;
- impact-check accepted Roadmap changes;
- preserve completed work;
- distinguish minor from major rescheduling;
- detect missed work;
- create feasible recovery rather than endless overdue backlog;
- consider deadlines, priorities, dependencies, Revision needs and availability;
- explain substantial schedule movement;
- require review for consequential rescheduling.

None are R0 acceptance criteria.

---

# 18. Recommendations / Home / Notifications — R3+

The mature Learning OS will coordinate recommendations, Home and notifications using relevant Goal, Planner, Revision, Progress, deadline and learner-state changes.

Preserved principles:

- recommendation provenance;
- no false personalization;
- dismissal is not failure;
- Home should not show stale high-priority actions;
- multi-goal state must not be merged incorrectly;
- notification preferences are respected;
- duplicate/stale reminders are suppressed;
- one action should not create notification spam.

R0's `Adapted Study` selection is intentionally much narrower than the mature recommendation engine.

---

# 19. Conflict Handling

## XR-CONFLICT-001 — Explicit user change wins — R0 MUST
A recent explicit learner correction normally outranks an older automated/inferred assumption.

## XR-CONFLICT-002 — Stale-state detection — R0 MUST WHERE APPLICABLE
## XR-CONFLICT-003 — Contradictory evidence — R0 MUST
Conflicting evidence should reduce confidence or motivate further testing rather than force an arbitrary conclusion.

## XR-CONFLICT-004 — Correction propagation — R0 MUST
Future dependent decisions shall use corrected information.

## XR-CONFLICT-005 — Multi-goal scheduling conflicts — R3+
## XR-CONFLICT-006 — Preference conflicts — LATER
Context-specific explicit preferences shall eventually outrank conflicting global defaults for that context.

---

# 20. Cascade Safety

## XR-SAFE-001 — Defined stopping condition — R0 MUST
The R0 chain shall stop after its intended bounded adaptation/reassessment work rather than recursively generating unlimited actions.

## XR-SAFE-002 — No recursive self-triggering — R0 MUST
A state update shall not repeatedly trigger equivalent work without new meaningful state.

## XR-SAFE-003 — Consequential boundary — LONG-TERM MUST
Automation shall stop at approval boundaries for consequential learner decisions.

## XR-SAFE-004 — Confidence cannot inflate through propagation — R0 MUST
Uncertain upstream output shall not become more certain merely because multiple systems consumed it.

## XR-SAFE-005 — Evidence vs derived state — R0 MUST
Source evidence, learner-state conclusions and recommendations/adaptations shall remain distinguishable.

## XR-SAFE-006 — Maximum adaptation scope — R0 MUST
One weak signal shall not trigger broad learner-state or learning-path changes.

## XR-SAFE-007 — No AI authority escalation — R0 MUST
One AI component recommending an action shall not automatically grant another component permission for a higher-impact action.

---

# 21. Duplicate Processing / Idempotency

## XR-IDEMP-001 — Duplicate signal safety — R0 MUST
Retrying the same logical R0 operation shall not create duplicate consequential state.

## XR-IDEMP-002 — Assessment submission — R0 MUST
One logical submission shall not accidentally create multiple attempts/evidence records because of retries.

## XR-IDEMP-003 — Evidence recording — R0 MUST
The same evaluated response shall not silently create duplicate evidence.

## XR-IDEMP-004 — Learner-state update — R0 MUST
Reprocessing unchanged evidence shall not produce meaningless repeated state transitions/adaptations.

## XR-IDEMP-005 — Safe retries — R0 MUST
Transient failures shall be retryable where safe.

Notification/proposal-specific idempotency is added with those later systems.

---

# 22. Auditability & Explainability

## XR-AUDIT-001 — Consequential R0 change record — R0 MUST
For an adaptive state/action, ARIA shall retain enough information to answer:

```text
what changed?
when?
for which learner/context/concept?
what evidence triggered it?
what state was derived?
why was this adaptation selected?
was it automatic, user-selected or corrected?
```

## XR-AUDIT-002 — Learner-facing explanation — R0 MUST
Technical traces need not be exposed directly, but actual reasoning factors shall be translatable into concise explanations.

## XR-AUDIT-003 — Evidence trace — R0 MUST
Important state conclusions shall trace back to supporting evidence.

## XR-AUDIT-004 — No fabricated explanation — R0 MUST
ARIA shall not generate a plausible-sounding explanation disconnected from the factors actually used.

## XR-AUDIT-005 — Proposal decisions — R1/R3+
Accepted/rejected/modified/expired proposal audit enters scope with Roadmap/Planner automation.

---

# 23. Failure Isolation & Recovery

## XR-FAIL-001 — Failure isolation — R0 MUST
Failure of a downstream R0 operation shall not unnecessarily invalidate successful upstream work.

Example: if evaluation/evidence are safely persisted but adaptation generation fails, the valid attempt/evidence remains preserved.

## XR-FAIL-002 — Partial workflow status — R0 MUST
ARIA shall be able to represent partially completed R0 workflows rather than pretending the whole workflow succeeded/failed atomically when it did not.

## XR-FAIL-003 — Retryable operations — R0 MUST
## XR-FAIL-004 — No fabricated success — R0 MUST
## XR-FAIL-005 — Graceful degradation — R0 MUST
Unaffected core functionality should remain usable when a non-critical downstream action fails.

## XR-FAIL-006 — Stale derived action — R0 MUST
An adaptation generated from obsolete/corrected state shall be invalidated or recomputed before consequential use.

## XR-FAIL-007 — Preserve source data — R0 MUST
Derived-system failure shall not delete original learner actions/evidence.

## XR-FAIL-008 — Invalid evaluation protection — R0 MUST
Failed/invalid evaluation shall not silently become evidence of learner weakness.

---

# 24. R0 Example — Successful Adaptive Cycle

```text
Learner studies DBMS Transactions
              ↓
Takes supported assessment
              ↓
AssessmentSubmitted [attempt A]
              ↓
Evaluation
              ↓
Evidence:
  Transactions basics → supported
  Conflict serializability → difficulty signal
              ↓
Basic Learner State update
  serializability → uncertain/weak candidate
              ↓
ARIA chooses bounded adaptation
  targeted serializability explanation
  + worked example / diagnostic practice
              ↓
Reason stored:
  selected because of attempt A evidence
              ↓
Learner completes adapted Study
              ↓
Targeted reassessment [attempt B]
              ↓
New evidence stored separately
              ↓
Learner state reconsidered
```

If attempt B improves, Gate A proves that the machinery successfully closed the adaptive loop. It does **not** by itself prove that ARIA caused human learning improvement; Gate B handles directional real-user evidence without causal overclaiming.

---

# 25. R0 Example — Correction Path

```text
Assessment evaluated
       ↓
One response incorrectly marked wrong
       ↓
Learner/test harness corrects evaluation
       ↓
Original dependent evidence invalidated/revised
       ↓
Learner-state estimate recomputed
       ↓
Any stale adaptation based on the bad evidence
is invalidated/recomputed
```

The correction must not leave contradictory hidden derived state behind.

---

# 26. R0 Example — Failure Path

```text
AssessmentSubmitted
       ↓
Evaluation succeeds
       ↓
Evidence recorded
       ↓
Learner-state update succeeds
       ↓
Adaptation generation fails
       ↓
Attempt + evaluation + evidence + state remain preserved
       ↓
Adaptation can be retried safely
```

ARIA must never display "adapted successfully" when that final operation failed.

---

# 27. R0 Automation Decision Matrix

| Change | R0 Default Behaviour |
|---|---|
| Save assessment attempt | Automatic |
| Persist reliable evaluation | Automatic |
| Record valid evidence | Automatic |
| Run learner-state update check | Automatic |
| Update basic learner-state estimate | Automatic + inspectable/correctable |
| Choose bounded next-study adaptation | Automatic + visible/inspectable |
| Override adapted action | Learner-controlled |
| Replace learner-selected assessment rules | Confirmation / explicit learner action |
| Correct evaluation/context/state assumption | Learner/tester correction path |
| Major Roadmap restructuring | Not in R0 |
| Planner rescheduling | Not in R0 |
| Notification delivery | Not in R0 |

---

# 28. Later Mature Cross-System Model

The complete product may eventually coordinate:

```text
Goal / Context
      ↓
Study / Resources
      ↓
Assessment
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
                    ↺
```

This diagram is the **Learning OS destination**, not the R0 implementation plan.

---

# 29. Step 4 Decisions

1. R0 cross-system scope is one adaptive learning loop, not full Learning OS orchestration.
2. Evidence remains separate from learner-state conclusions.
3. R0 adaptation must be causally traceable in the software sense: the stored evidence/state must actually be what selected the adaptation.
4. This software traceability does not imply causal proof of human learning improvement.
5. Unknown and contradictory evidence are first-class states.
6. R0 adaptation is bounded to immediate Study/reassessment behaviour.
7. Roadmap, Revision, Planner, Home and Notifications remain preserved for later releases.
8. Explicit learner corrections outrank stale/inferred assumptions.
9. Cross-system operations are retry-safe, idempotent, bounded, auditable and failure-isolated.
10. AI components cannot escalate each other's authority through recommendation chains.
11. R0 must expose enough traceability for Gate A to verify that the loop actually closed.

---

# 30. Step 4 Completion

**Step 4 — Cross-System & Automation Requirements has been audited and realigned.**

The previous version correctly contained strong orchestration safety principles, but described the complete Learning OS event graph as if it were one immediate system. The reviewed version preserves those principles while making the R0 automation chain explicit and small.

Next:

# Step 5 — AI, Learner Model, Memory & Evidence Requirements Audit

Step 5 must now answer the hardest R0 intelligence questions precisely:

```text
What counts as evidence?
        ↓
How strong/reliable is it?
        ↓
How is learner state represented?
        ↓
How does uncertainty behave?
        ↓
What may ARIA infer from one result?
        ↓
How does evidence accumulate/contradict?
        ↓
How does a state produce an adaptation?
        ↓
How are incorrect AI/evaluation outputs corrected?
```

It must distinguish the **basic R0 learner state needed to close the loop** from the much richer longitudinal Learner Model, memory, misconception detection, prerequisite reasoning and agentic intelligence planned for later releases.