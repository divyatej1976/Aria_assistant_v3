# ARIA — Phase 2: Product & UX Design

## Step 3 — Detailed User Flows & State Transitions

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 2 — Product & UX Design  
**Status:** Step 3 complete  
**Inputs:** Frozen Phase 1 PRD, Phase 2 Steps 1–2

---

# 1. Purpose

Steps 1–2 defined the R0 journey and the surfaces that support it. Step 3 defines the transitions between those surfaces, including recovery paths and state rules.

The central rule is:

> A learner should always be able to determine what happened, what ARIA is doing now, and what they can do next.

R0 must preserve valid completed work across failures and must not create learning evidence from incomplete or invalid stages.

---

# 2. Flow Vocabulary

This document distinguishes three state families.

## Workflow state
Where the learner currently is in the adaptive cycle.

## Processing state
Whether a system operation is idle, pending, successful or failed.

## learner_concept_state
ARIA's current evidence-backed concept signal:

```text
UNTESTED
DEVELOPING
NEEDS_REVIEW
SUPPORTED
```

These must not be collapsed into one state machine.

---

# 3. Canonical Workflow State Machine

```text
NO_CONTEXT
    ↓
CONTEXT_READY
    ↓
RESOURCE_REQUIRED
    ↓
RESOURCE_READY
    ↓
STUDY_ACTIVE
    ↓
ASSESSMENT_CONFIGURING
    ↓
ASSESSMENT_GENERATING
    ↓
ASSESSMENT_READY
    ↓
ASSESSMENT_ACTIVE
    ↓
ASSESSMENT_SUBMITTED
    ↓
EVALUATION_PENDING
    ↓
RESULT_READY
    ↓
STATE_RECONSIDERED
    ↓
ADAPTATION_READY / MORE_EVIDENCE_NEEDED / NORMAL_STUDY
    ↓
ADAPTED_STUDY_ACTIVE
    ↓
REASSESSMENT_READY
    ↓
REASSESSMENT_ACTIVE
    ↓
REASSESSMENT_SUBMITTED
    ↓
EVALUATION_PENDING
    ↓
NEW_EVIDENCE_READY
    ↓
STATE_RECONSIDERED
    ↓
CYCLE_COMPLETE
```

Failure states branch from the operation that failed rather than destroying the workflow.

---

# 4. Flow A — New Learner Entry

```text
Landing
  ↓ Get Started
Sign Up
  ↓ submit
Validate input
  ├── invalid → show field errors → remain Sign Up
  ├── auth/provider failure → retry → remain Sign Up
  └── success
          ↓
First-Time Setup
          ↓ confirm R0 context
Create learner context
  ├── failure → show retry; identity remains valid
  └── success
          ↓
Home / Workspace
```

## Postcondition

- authenticated learner exists;
- learner owns one R0 validation context;
- workflow state is `RESOURCE_REQUIRED` unless valid material already exists.

---

# 5. Flow B — Returning Learner

```text
Sign In
  ↓
Authenticate
  ├── invalid → error
  ├── expired/revoked → reauthenticate
  └── success
          ↓
Load learner-owned active context
          ↓
Resolve workflow state
          ↓
Home shows correct resume action
```

Home must not always default to Study. It resumes the most consequential unfinished stage.

---

# 6. Resume Decision Flow

```text
Authenticated?
 ├── No → Sign In
 └── Yes
      ↓
Active context?
 ├── No → First-Time Setup
 └── Yes
      ↓
Blocking/retryable consequential failure?
 ├── Yes → resume failed stage
 └── No
      ↓
Unsubmitted active assessment?
 ├── Yes → Continue Assessment
 └── No
      ↓
Submitted attempt not validly evaluated?
 ├── Yes → Evaluation status/retry
 └── No
      ↓
Adaptation ready but not completed?
 ├── Yes → Focused Review
 └── No
      ↓
Targeted reassessment ready/in progress?
 ├── Yes → Reassessment
 └── No
      ↓
Usable resource exists?
 ├── No → Add Material
 └── Yes → Study
```

This is conceptual UX priority; architecture may encode it differently.

---

# 7. Flow C — PDF Resource Ingestion

```text
Resources
   ↓ Upload PDF
Client validation
   ├── unsupported/too large/etc. → explain → choose another
   └── accepted
          ↓
Persist resource record
          ↓
Upload
   ├── network failure → retry upload
   └── success
          ↓
PROCESSING
          ↓
Extract/process/index as required
   ├── failure → FAILED
   │             ↓
   │          Retry / replace / remove
   └── success → READY
                  ↓
              Study available
```

## Rules

- processing failure cannot be represented as `READY`;
- one failed resource cannot invalidate unrelated ready resources;
- Study cannot claim grounding in a failed resource;
- retries should update/reuse the intended resource operation rather than create accidental duplicates.

---

# 8. Flow D — Pasted Text

```text
Resources
   ↓ Paste text
Validate non-empty/supported size
   ├── invalid → inline error
   └── valid
         ↓
Persist text resource
         ↓
Process/index if needed
   ├── failure → FAILED → retry/edit/remove
   └── success → READY
```

The UX should treat pasted text and PDF as two resource inputs to the same context, not two separate products.

---

# 9. Flow E — Baseline Study

```text
RESOURCE_READY
    ↓
Open Study
    ↓
Load active context + usable resource references
    ↓
Learner asks / selects concept
    ↓
Generate response
    ├── generation failure → preserve conversation/input → retry
    └── success
          ↓
Display response + grounding indication where expected
          ↓
Continue Study OR Test Me
```

## Guardrail

A normal Study response is not automatically learning evidence. Evidence enters the R0 learner-state pipeline through the defined evaluated assessment path.

---

# 10. Flow F — Assessment Configuration

```text
Study / Assess
    ↓ Test Me
Assessment Setup
    ↓
Choose topic
Choose question count
Choose difficulty
Optional timer
    ↓
Validate configuration
    ├── invalid → explain field issue
    └── valid
          ↓
Generate Assessment
```

The configuration is frozen for the generated assessment attempt so later UI changes do not mutate an in-progress assessment unexpectedly.

---

# 11. Flow G — Assessment Generation

```text
ASSESSMENT_CONFIGURING
      ↓
ASSESSMENT_GENERATING
      ↓
Generate structured MCQs
      ↓
Validate structure + answerability + required fields
      ├── valid → ASSESSMENT_READY
      └── invalid
             ↓
        bounded repair/retry
             ├── valid → READY
             └── still invalid → GENERATION_FAILED
                                      ↓
                                 explicit retry
```

No learner evidence exists at this stage.

---

# 12. Flow H — Assessment Session

```text
ASSESSMENT_READY
     ↓ Start
ASSESSMENT_ACTIVE
     ↓
Answer / navigate
     ↓
Autosave/local/server save as implementation permits
     ↓
Submit
     ↓
Confirmation if unanswered questions exist
     ├── Cancel → continue assessment
     └── Confirm
           ↓
Persist final attempt
           ↓
ASSESSMENT_SUBMITTED
```

## Rules

- double-clicking Submit cannot create two attempts;
- once final submission is accepted, answers cannot silently change;
- if timer expires, the resulting submission behaviour must be explicit and deterministic.

---

# 13. Flow I — Submission Network Failure

```text
Submit
  ↓
Request uncertain/failed
  ↓
Do NOT immediately create a new attempt
  ↓
Check/reconcile submission state
  ├── server already accepted → show submitted state
  └── not accepted → allow retry using same idempotent operation
```

Learner-facing message should avoid encouraging repeated uncontrolled submissions.

---

# 14. Flow J — Deterministic Evaluation

```text
ASSESSMENT_SUBMITTED
      ↓
EVALUATION_PENDING
      ↓
Load frozen question/answer key + submitted answers
      ↓
Score deterministically
      ↓
Validate evaluation result
      ├── invalid/failure → EVALUATION_FAILED
      │                    ↓
      │                 no learning evidence
      │                    ↓
      │                 retry evaluation
      └── valid
            ↓
Persist evaluation
            ↓
Create evidence
```

Evaluation service/system failure is never converted into an incorrect learner answer.

---

# 15. Flow K — Evidence Creation

For each usable evaluated MCQ:

```text
Valid evaluation result
       ↓
Identify learner
Identify context
Identify concept
Identify question/attempt
       ↓
Create evidence record
       ↓
Validate provenance
       ├── invalid → do not feed learner_concept_state
       └── valid → eligible for state reconsideration
```

Evidence creation must be idempotent relative to the source evaluation/question.

---

# 16. Flow L — Learner-State Reconsideration

```text
New valid concept evidence
       ↓
Load relevant prior valid evidence
       ↓
Apply conservative R0 policy
       ↓
0 sufficient observations?
       → UNTESTED

1 usable observation?
       → DEVELOPING

≥2 aligned weak observations?
       → candidate NEEDS_REVIEW

≥2 aligned correct observations including independent/later evidence?
       → candidate SUPPORTED

Mixed/contradictory?
       → DEVELOPING / conservative lower-confidence prior
       ↓
Persist state + reason + evidence refs + confidence + time
```

A state transition is a derived conclusion, not raw evidence.

---

# 17. Flow M — Insufficient Evidence

```text
First usable observation
       ↓
State = DEVELOPING
       ↓
Strong adaptation justified?
       └── No
             ↓
Offer normal Study or another targeted evidence opportunity
```

The learner sees uncertainty explicitly rather than a fake confident label.

---

# 18. Flow N — Repeated Weak Evidence

```text
Weak evidence #1
     ↓
DEVELOPING
     ↓
Weak evidence #2 from distinct opportunity
     ↓
Policy conditions satisfied?
     ├── No → remain conservative
     └── Yes → NEEDS_REVIEW
                    ↓
             adaptation decision
```

`NEEDS_REVIEW` does not equal a permanent misconception diagnosis.

---

# 19. Flow O — Repeated Supported Evidence

```text
Correct evidence #1
      ↓
DEVELOPING
      ↓
Independent/later correct evidence #2
      ↓
Policy conditions satisfied?
      ├── No → remain conservative
      └── Yes → SUPPORTED
                    ↓
             reduce unnecessary remediation
```

`SUPPORTED` is current evidence support, not permanent mastery.

---

# 20. Flow P — Contradictory Evidence

```text
Prior evidence suggests difficulty
       +
New evidence suggests support
       ↓
Detect contradiction/mixed evidence
       ↓
Reduce confidence / retain conservative state
       ↓
Avoid strong adaptation
       ↓
Offer targeted diagnostic/reassessment
```

No evidence is discarded merely because it conflicts with the current state.

---

# 21. Flow Q — Adaptation Decision

```text
State reconsidered
      ↓
Does evidence justify adaptation?
 ├── No → normal Study / gather more evidence
 └── Yes
       ↓
Select bounded adaptation action
       ↓
Attach concept + reason + evidence provenance
       ↓
ADAPTATION_READY
```

Possible actions:

- prioritize concept;
- alternate explanation;
- simpler decomposition;
- worked example;
- prerequisite recap;
- more/less scaffolding;
- targeted practice;
- diagnostic check;
- reduce unnecessary repetition.

---

# 22. Flow R — Adaptation Explanation

Before or alongside adapted Study:

```text
ADAPTATION_READY
      ↓
Show learner:
  what ARIA observed
  current signal
  what will change
  why / next step
      ↓
Learner may:
  Start focused review
  Review evidence
  Challenge result
```

The adaptation cannot be a silent unexplained content mutation.

---

# 23. Flow S — Adapted Study

```text
Start focused review
      ↓
ADAPTED_STUDY_ACTIVE
      ↓
Load adaptation instruction + context + relevant resources
      ↓
Generate adapted learning experience
      ├── failure → ADAPTED_STUDY_FAILED
      │             preserve evidence/state/adaptation decision
      │             retry generation
      └── success
             ↓
        learner studies/practices
             ↓
        REASSESSMENT_READY
```

The valid assessment/evidence chain must survive adapted-content generation failure.

---

# 24. Flow T — Targeted Reassessment

```text
REASSESSMENT_READY
      ↓
Start targeted check
      ↓
Generate/select independent MCQs for affected concept
      ↓
REASSESSMENT_ACTIVE
      ↓
Submit
      ↓
REASSESSMENT_SUBMITTED
      ↓
Deterministic evaluation
      ↓
New evidence
      ↓
State reconsideration
```

Questions should not merely repeat already revealed answers.

---

# 25. Flow U — Improvement Signal

Example:

```text
Prior state: NEEDS_REVIEW
      ↓
Adapted Study
      ↓
New independent correct evidence
      ↓
Reconsider all relevant evidence
      ↓
Possible outcome:
  DEVELOPING with stronger confidence
  or SUPPORTED if policy threshold is actually satisfied
```

ARIA does not force a jump to `SUPPORTED` merely because the first post-adaptation answer is correct.

---

# 26. Flow V — Continued Difficulty

```text
Prior NEEDS_REVIEW
      ↓
Adapted Study
      ↓
New weak evidence
      ↓
State remains/strengthens NEEDS_REVIEW
      ↓
ARIA may choose another bounded supported adaptation
```

R0 may continue the loop, but it must not silently expand into an unlimited autonomous tutoring workflow.

---

# 27. Flow W — Cycle Completion

A validation cycle becomes complete when:

```text
Baseline/initial evidence exists
       ↓
learner_concept_state was reconsidered
       ↓
Adaptation/gather-more-evidence action occurred
       ↓
A later independent assessment opportunity occurred
       ↓
New evidence was recorded
       ↓
learner_concept_state was reconsidered again
```

Then:

```text
CYCLE_COMPLETE
     ↓
Show summary
     ↓
Continue Study / Review details
```

---

# 28. Flow X — Review Answers

```text
Results
   ↓ Review Answers
Question detail
   ↓
Show:
 learner answer
 correct answer
 evaluation
 concept attribution
 explanation
 evidence effect where appropriate
```

The learner can navigate between question details without changing the submitted attempt.

---

# 29. Flow Y — Challenge Evaluation

```text
Question detail
      ↓ This result looks wrong
Create challenge/recheck request
      ↓
Re-evaluate source result using permitted mechanism
      ↓
Was original evaluation wrong?
 ├── No
 │    ↓
 │  retain evaluation/evidence
 │  explain outcome
 │
 └── Yes
      ↓
   correct evaluation
      ↓
   invalidate/replace dependent evidence as required
      ↓
   recompute learner_concept_state
      ↓
   invalidate/recompute pending adaptation
      ↓
   show corrected outcome
```

A correction is not a manual arbitrary learner-state override.

---

# 30. Flow Z — Learner Disagrees With State But Evaluation Is Correct

```text
Learner: "I know this concept"
      ↓
Review evidence
      ↓
Evaluation is correct
      ↓
Do not delete valid evidence automatically
      ↓
Offer explanation + another evidence opportunity
      ↓
New assessment can change state legitimately
```

This preserves learner agency without making evidence meaningless.

---

# 31. Evaluation Failure Recovery

```text
Attempt persisted
      ↓
Evaluation fails
      ↓
EVALUATION_FAILED
      ↓
UI: answers safely saved
      ↓
Retry evaluation
      ↓
Same attempt
      ↓
Valid evaluation
      ↓
Evidence pipeline continues
```

Never ask the learner to retake the assessment solely because evaluation infrastructure failed.

---

# 32. Adapted Generation Failure Recovery

```text
Valid state + adaptation decision
      ↓
Adapted Study generation fails
      ↓
ADAPTED_STUDY_FAILED
      ↓
Preserve:
 attempt
 evaluation
 evidence
 learner_concept_state
 adaptation decision
      ↓
Retry only failed generation stage
```

---

# 33. Session Expiry Flow

```text
Learner performs action
      ↓
Session invalid/expired
      ↓
Preserve safe local/non-sensitive in-progress state where appropriate
      ↓
Reauthenticate
      ↓
Reconcile server state
      ↓
Return to correct workflow point
```

Sensitive content must not be exposed simply to preserve convenience.

---

# 34. Authorization Failure Flow

```text
Request resource/context/attempt
      ↓
Server authorization check
      ↓
Not owner / not permitted
      ↓
Reject
      ↓
Do not reveal private object details
      ↓
Safe error / return to learner-owned context
```

Authorization failure must never degrade into a frontend-only warning while data is still returned.

---

# 35. Duplicate Action / Idempotency Flow

For consequential operations such as submission/evidence creation:

```text
User action
   ↓
Operation identity/idempotency boundary
   ↓
First request succeeds
   ↓
Duplicate/retry arrives
   ↓
Return/reconcile existing result
   ↓
Do not create duplicate consequential state
```

This applies especially to:

- assessment submission;
- evaluation trigger;
- evidence creation;
- state transition processing;
- adaptation creation.

---

# 36. Resource Removal Flow

```text
Learner requests removal
      ↓
Would removal affect active/in-progress grounded operation?
      ├── Yes → explain/confirm or block until safe
      └── No
            ↓
         remove/deactivate resource
            ↓
         future Study cannot claim grounding in it
```

Historical evidence/attempt integrity should not be silently destroyed merely because a source resource is later removed; exact retention/deletion semantics belong to architecture/privacy design.

---

# 37. Processing-State Pattern

Async operations should generally expose:

```text
IDLE
 ↓
PENDING
 ├── SUCCESS
 └── FAILED_RETRYABLE
       ↓ retry
     PENDING
```

Use `FAILED_BLOCKING` only when the learner cannot proceed without changing input or taking another action.

Avoid endless `PENDING` states without timeout/status/recovery behaviour.

---

# 38. Navigation Guard Rules

## Leaving an active assessment

If answers could be lost, warn or persist before navigation.

## Opening Study during pending evaluation

Allowed only if the UI does not pretend the pending attempt has already changed learner_concept_state.

## Starting another assessment

R0 should avoid ambiguous concurrent attempts for the same active adaptive step unless deliberately supported.

## Opening another user's URL/object ID

Server rejects access regardless of client navigation.

---

# 39. Back-Button Behaviour

Browser/app back navigation must not:

- unsubmit a submitted assessment;
- duplicate submission;
- revert evidence;
- create a second adaptation;
- display stale editable answers as though the attempt were active.

Historical views may be revisited in read-only form.

---

# 40. Refresh Behaviour

Refresh should restore server-backed workflow state.

Examples:

- processing PDF → still processing/status;
- active assessment → restore safely if supported;
- submitted assessment → submitted, not editable;
- evaluation pending → pending;
- adaptation ready → adaptation ready;
- cycle complete → summary available.

---

# 41. Multi-Tab Behaviour

R0 does not need sophisticated collaborative synchronization, but consequential operations must remain safe if two tabs are open.

At minimum:

- duplicate submissions remain idempotent;
- stale tabs cannot overwrite final submitted state;
- refreshed state reflects the authoritative server state.

---

# 42. Learner-State Transition Table

| Current | Evidence event | Typical next state | Strong adaptation? |
|---|---|---|---|
| UNTESTED | no usable evidence | UNTESTED | No |
| UNTESTED | first usable weak/correct | DEVELOPING | No |
| DEVELOPING | aligned second weak | NEEDS_REVIEW candidate | Yes, if policy satisfied |
| DEVELOPING | aligned independent correct | SUPPORTED candidate | Usually reduce remediation |
| DEVELOPING | contradictory | DEVELOPING | No/diagnostic |
| NEEDS_REVIEW | another weak | NEEDS_REVIEW | Yes |
| NEEDS_REVIEW | one new correct | NEEDS_REVIEW or DEVELOPING | Conservative |
| NEEDS_REVIEW | sufficient later supported evidence | DEVELOPING/SUPPORTED per policy | Reconsider |
| SUPPORTED | one weak | SUPPORTED or DEVELOPING | Conservative |
| SUPPORTED | repeated weak evidence | DEVELOPING/NEEDS_REVIEW per policy | Reconsider |

Exact confidence math is not frozen in UX design; conservative behaviour is.

---

# 43. Workflow Transition Invariants

The following must always hold:

1. no valid evaluation → no assessment-derived learning evidence;
2. no valid evidence → no evidence-backed learner-state change;
3. no justified state/evidence signal → no strong evidence-driven adaptation;
4. failed downstream generation does not invalidate upstream valid state;
5. correction propagates forward;
6. retries do not duplicate consequential state;
7. context/user provenance survives every transition;
8. second-cycle evidence is independent/new enough to reconsider state meaningfully;
9. workflow status is recoverable after refresh/sign-in;
10. UI never claims completion of a stage the system has not validly completed.

---

# 44. Gate A Flow Coverage

| Gate A scenario | Covered flow |
|---|---|
| Weak evidence → adaptation | N → Q → R → S |
| Supported evidence differs | O → Q |
| Insufficient evidence | M |
| Evaluation failure | J + recovery |
| Contradictory evidence | P |
| Context isolation | K + authorization rules |
| Correction propagation | Y |
| Retry/idempotency | I + §35 |
| Downstream AI failure | S + §32 |
| Repeated adaptive cycle | T → U/V → W |
| Cross-user isolation | §34 |

The UX/state design therefore exposes every mandatory Gate A path defined by the frozen PRD.

---

# 45. Step 2 → Step 3 Surface Mapping

| Surface | Major transitions |
|---|---|
| Landing/Auth | A, B |
| Home | Resume decision flow |
| Resources | C, D, resource removal |
| Study | E, R, S |
| Assessment Setup | F, G |
| Assessment | H, I |
| Results/Evidence | J, K, L, M–P |
| Adaptation | Q, R |
| Reassessment | T |
| Cycle Summary | U–W |
| Review/Correction | X–Z |
| Global shell | session, authorization, refresh, multi-tab |

---

# 46. Scope Guardrail

Step 3 intentionally does **not** define:

- final database tables;
- queue/event-bus technology;
- framework-specific route guards;
- exact API endpoints;
- exact confidence formula;
- LLM/provider selection;
- vector database choice;
- auth vendor;
- final visual styling.

Those are architecture/implementation decisions unless a later UX step requires a user-facing contract.

---

# 47. Step 3 Completion Checklist

- [x] canonical workflow state machine defined;
- [x] first-time flow defined;
- [x] returning/resume flow defined;
- [x] PDF/text ingestion flows defined;
- [x] baseline Study flow defined;
- [x] assessment configuration/generation defined;
- [x] assessment/submission flow defined;
- [x] deterministic evaluation flow defined;
- [x] evidence creation defined;
- [x] learner-state reconsideration defined;
- [x] insufficient/weak/supported/contradictory evidence paths defined;
- [x] adaptation decision/explanation defined;
- [x] adapted Study defined;
- [x] targeted reassessment defined;
- [x] second-cycle completion defined;
- [x] challenge/correction defined;
- [x] failure recovery defined;
- [x] idempotency/retry behaviour defined;
- [x] session/authorization behaviour defined;
- [x] refresh/back/multi-tab expectations defined;
- [x] Gate A coverage checked;
- [x] architecture-specific decisions kept out.

---

# 48. Step 3 Completion

**Phase 2 — Step 3 is complete.**

ARIA R0 now has an explicit UX state-transition contract for the complete adaptive loop and its critical failure/recovery paths.

Next:

# Step 4 — Study Experience & Adaptation UX

Step 4 will design the learning interaction itself: Study layout and behaviour, grounding visibility, conversation structure, concept focus, how adaptation changes the experience, how ARIA explains its reasoning without overwhelming the learner, and the exact boundary between useful personalization and unjustified learner-model claims.
---

## Next

Step 4 — Study Experience & Adaptation UX.
