# ARIA — Phase 2: Product & UX Design

## Step 6 — Error, Empty, Loading & Recovery UX

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 2 — Product & UX Design  
**Status:** Step 6 complete  
**Inputs:** Frozen Phase 1 PRD + Phase 2 Steps 1–5

---

# 1. Purpose

ARIA R0 contains multiple asynchronous and AI-assisted stages. A credible adaptive-learning product therefore cannot design only the happy path.

This document defines the cross-product UX contract for:

- loading and processing;
- empty states;
- network/offline states;
- authentication/session failures;
- resource failures;
- Study/retrieval failures;
- assessment generation/submission failures;
- evaluation failures;
- evidence/state processing failures;
- adaptation failures;
- stale/conflicting client state;
- retries, refresh and safe resume.

Core principle:

> **Failure should interrupt only the stage that failed, preserve every valid completed stage before it, and tell the learner what happened and what they can do next.**

---

# 2. Global State Vocabulary

Applicable screens should use a consistent conceptual state model:

```text
IDLE
LOADING
PROCESSING
READY
EMPTY
SUCCESS
FAILED_RETRYABLE
FAILED_INPUT
FAILED_BLOCKING
OFFLINE
UNAUTHORIZED
SESSION_EXPIRED
STALE
```

Not every screen needs every state.

---

# 3. Error Message Anatomy

Useful errors answer four questions:

```text
WHAT HAPPENED?
WHAT WAS PRESERVED?
WHAT DID NOT HAPPEN?
WHAT CAN I DO NEXT?
```

Example:

> **We couldn't evaluate this assessment.**  
> Your submitted answers are safely saved. No learning signal was changed.  
> **Try evaluation again**

This is better than:

> Error 500.

---

# 4. Error Language Rules

Messages should be:

- specific enough to guide action;
- non-accusatory;
- honest about uncertainty;
- explicit when work is preserved;
- explicit when a consequential operation did not complete;
- free of internal stack traces/provider details.

Avoid:

> Something went wrong.

when the product actually knows which stage failed.

---

# 5. Loading vs Processing

## Loading

Fetching already-existing state/content.

Examples:

- opening Home;
- loading assessment results;
- restoring an active attempt.

## Processing

Creating or transforming something.

Examples:

- processing PDF;
- generating assessment;
- evaluating attempt;
- generating adapted Study.

The UI should distinguish these where it helps set expectations.

---

# 6. Short Loading State

For brief fetches, use compact indicators/skeletons without blocking more of the interface than necessary.

Examples:

```text
Loading your learning context…
```

```text
Loading assessment…
```

Avoid flashing full-page spinners for every small request.

---

# 7. Long Processing State

Longer operations should explain what is happening.

Example:

```text
Processing DBMS Unit 4.pdf

Preparing the material so ARIA can use it in Study.
```

Where useful, show stage/status rather than fake percentage progress.

Do not show `87%` unless the system genuinely knows meaningful progress.

---

# 8. Processing Timeout / Delayed State

If an operation takes materially longer than expected:

> **This is taking longer than usual.**  
> You can stay here, or return to Home. We'll keep the current processing state.

Actions may include:

- `Keep waiting`;
- `Return to Home`;
- `Check status`;
- `Retry` only when safe.

Do not leave the learner staring at an endless spinner.

---

# 9. Global Empty-State Pattern

Empty states should explain:

```text
WHAT IS MISSING
WHY IT MATTERS
WHAT ACTION STARTS THE FLOW
```

Example:

> **No study material yet**  
> Add a PDF or paste text so ARIA has material to use in this learning context.  
> **Add material**

---

# 10. Home Empty State

If the learner has a context but no resource:

> **Start with your learning material**  
> Add a PDF or paste text for the DBMS validation context.  
> `[Add material]`

If the learner somehow has no context:

> **Set up your learning context**  
> `[Continue setup]`

Home should not display fake progress cards simply to fill space.

---

# 11. Resources Empty State

> **No resources yet**  
> Upload a PDF or paste your study material to begin grounded Study.  
> `[Upload PDF]` `[Paste text]`

---

# 12. Study Empty State

When material is ready but no conversation exists:

> **What would you like to understand?**  
> Ask about your DBMS material or choose a concept to start.

When no usable material exists:

> **Add study material first**  
> ARIA doesn't currently have a ready resource for grounded Study.  
> `[Add material]`

If general explanations are permitted, they must be clearly distinguished from grounded responses.

---

# 13. Assessment Empty State

If no assessment exists:

> **No assessment yet**  
> When you're ready, create an MCQ check for the concept you're studying.  
> `[Create assessment]`

---

# 14. Evidence Empty State

> **No learning signal yet**  
> ARIA needs formal evaluated assessment evidence before it can show a learning signal.  
> `[Take assessment]`

No evidence must never appear as `0% mastery`.

---

# 15. Adaptation Empty State

> **No focused adaptation right now**  
> ARIA will change Study when the evidence supports a useful next action.

This should not be framed as an error.

---

# 16. Offline Detection

When the client detects loss of connectivity:

```text
You're offline

Some actions may be unavailable until your connection returns.
```

The UI should distinguish locally safe interactions from operations that require server confirmation.

R0 does not promise full offline Study.

---

# 17. Offline During Study

If the learner has already-loaded content, the interface may preserve it for reading where safe.

New AI requests should show:

> **Connection needed**  
> Reconnect to ask ARIA another question.

Do not discard the learner's unsent input unnecessarily.

---

# 18. Offline During Assessment

If answers can be locally preserved, make that status explicit.

Example:

> **Connection lost**  
> Your current selections are kept on this device, but final submission requires a connection.

If local preservation is not guaranteed, the UX must not falsely claim it is.

---

# 19. Offline During Submission

```text
Submit clicked
      ↓
Connection lost / outcome uncertain
      ↓
Do not create a new attempt automatically
      ↓
Reconnect
      ↓
Reconcile server submission state
      ↓
Accepted? → show submitted
Not accepted? → allow same-operation retry
```

Learner-facing message:

> **Checking your submission**  
> The connection dropped while submitting. We'll verify whether your answers were received before asking you to try again.

---

# 20. Authentication Failure

Invalid sign-in:

> **We couldn't sign you in with those details.**  
> Check them and try again.

Provider/network failure:

> **Sign-in service is temporarily unavailable.**  
> Your account hasn't been changed. Try again shortly.

Avoid exposing whether a private account exists when that would create unnecessary enumeration risk.

---

# 21. Session Expiry

If the session expires during normal browsing:

> **Your session expired**  
> Sign in again to continue.

If the learner has in-progress work:

> We'll restore the latest safely saved state after you sign in again.

Only make preservation claims the implementation can guarantee.

---

# 22. Reauthentication Return

After successful reauthentication:

```text
Reload authoritative server state
      ↓
Reconcile any safe local state
      ↓
Return learner to correct workflow point
```

Do not blindly return to the previous URL if the workflow has already advanced elsewhere.

---

# 23. Authorization Failure

If a learner attempts to access another user's context/resource/attempt:

> **You don't have access to this item.**  
> `[Return to your learning workspace]`

Do not reveal private metadata such as the other learner's name, resource title or assessment content.

---

# 24. PDF Validation Failure

Examples:

### Unsupported type

> **This file type isn't supported in R0.**  
> Upload a PDF instead.

### File too large

> **This PDF is larger than the current upload limit.**  
> Choose a smaller file.

### Empty/corrupt file

> **ARIA couldn't read this PDF.**  
> Try another copy of the file.

The exact limits are implementation decisions and should be displayed dynamically/configurably where possible.

---

# 25. PDF Upload Failure

> **Upload interrupted**  
> The PDF wasn't fully uploaded.  
> `[Try upload again]`

Do not show the resource as ready.

---

# 26. PDF Processing Failure

> **We couldn't prepare this PDF for Study.**  
> The file is still listed, but ARIA won't use it as a ready source.  
> `[Try processing again]` `[Replace file]` `[Remove]`

A failed resource must never display the same visual status as a ready resource.

---

# 27. Pasted-Text Failure

Invalid/empty:

> **Add some study text first.**

Too large:

> **This text is longer than the current R0 limit.**  
> Shorten it or add a smaller section.

Processing failure:

> **We couldn't prepare this text for Study.**  
> Your original text is preserved if the system has safely saved it.  
> `[Try again]`

---

# 28. Retrieval / Grounding Failure

If Study expected to use a resource but retrieval fails:

> **I couldn't retrieve the relevant part of your material right now.**  
> I can retry, or explain the concept generally without claiming the answer comes from your PDF.

Actions:

- `Retry with material`;
- `Explain generally`;
- `Check resources`.

This prevents grounding theater.

---

# 29. Study Generation Failure

> **I couldn't generate that explanation.**  
> Your conversation and learning context are still here.  
> `[Try again]`

If the learner's prompt/input is preserved, keep it available rather than requiring retyping.

---

# 30. Partial / Interrupted Streaming Response

If a streamed Study response stops unexpectedly:

> **Response interrupted**  
> The explanation didn't finish.  
> `[Continue / retry]`

The incomplete response should not be presented as confidently complete.

---

# 31. Assessment Configuration Error

Use field-level validation where possible.

Examples:

- unsupported question count;
- missing topic;
- unsupported difficulty;
- invalid timer configuration.

Keep valid selections rather than resetting the entire form.

---

# 32. Assessment Generation Failure

> **We couldn't create a valid assessment.**  
> Your Study progress and resources are unchanged. No learning evidence was created.  
> `[Try again]` `[Change settings]`

If bounded repair attempts already failed, do not silently loop forever.

---

# 33. Active Assessment Load Failure

If an existing assessment cannot be loaded:

> **We couldn't load this assessment right now.**  
> Your saved attempt state hasn't been changed.  
> `[Try again]` `[Return Home]`

If the assessment no longer exists or is invalidated, explain that separately rather than using a retry loop that can never succeed.

---

# 34. Answer Save Failure

If autosave/server persistence fails:

> **Your latest answer may not be saved yet.**  
> Keep this page open while we retry.

The UI must not show a false `Saved` state.

If local preservation exists, distinguish:

```text
Saved on this device
Waiting to sync
```

from:

```text
Saved to ARIA
```

---

# 35. Submission Failure — Known Not Accepted

> **Submission didn't go through.**  
> Your answers are still here.  
> `[Try submission again]`

Use the same logical submission/idempotency boundary.

---

# 36. Submission Failure — Unknown Outcome

> **We're checking whether your assessment was submitted.**  
> Please don't submit a second copy yet.

Then reconcile server state.

This state is distinct from a known failed submission.

---

# 37. Evaluation Failure

This is a critical R0 safety state.

> **Your answers are safe, but evaluation couldn't finish.**  
> No learning evidence or learner-state change has been created from this attempt yet.  
> `[Try evaluation again]`

Never convert this failure into incorrect answers.

---

# 38. Evidence-Creation Failure

If evaluation succeeded but evidence persistence/creation fails:

```text
Evaluation remains valid
      ↓
Evidence stage fails
      ↓
Do not pretend learner_concept_state updated
      ↓
Retry evidence stage idempotently
```

Learner-facing wording:

> **Your assessment was scored, but ARIA hasn't finished updating your learning signal.**  
> Your score is safe. We'll retry the learning-signal update.

This is different from evaluation failure.

---

# 39. Learner-State Recalculation Failure

If valid evidence exists but derived state calculation fails:

> **Your new evidence is saved.**  
> ARIA couldn't update the current learning signal yet.  
> `[Try update again]`

Do not show a stale state as though it already includes the new evidence.

Possible label:

```text
Learning signal update pending
```

---

# 40. Adaptation Decision Failure

If state is valid but adaptation selection fails:

> **Your learning signal is up to date, but ARIA couldn't choose the next focused Study action right now.**  
> `[Try again]` `[Continue normal Study]`

The learner_concept_state remains valid.

---

# 41. Adapted Study Generation Failure

> **Focused review couldn't be generated.**  
> Your assessment, evidence and current learning signal are safely preserved.  
> `[Try focused review again]` `[Review evidence]` `[Continue Study]`

Never force a retake because this downstream generation failed.

---

# 42. Targeted Reassessment Generation Failure

> **We couldn't create the targeted check.**  
> Your focused review and current learning signal are unchanged.  
> `[Try again]` `[Keep studying]`

No new evidence is created until a valid reassessment is completed and evaluated.

---

# 43. Correction/Recheck Failure

If the learner challenges an evaluation and the recheck fails:

> **We couldn't complete the recheck yet.**  
> The original result remains unchanged for now.  
> `[Try recheck again]`

If the original result is under active dispute, the UX may mark it as such rather than implying the challenge was rejected.

---

# 44. Correction Propagation State

After a correction succeeds:

```text
Evaluation corrected
      ↓
Updating evidence…
      ↓
Updating learning signal…
      ↓
Updating/invalidation adaptation…
      ↓
Ready
```

During this window, avoid showing contradictory old/new state as final.

Possible banner:

> **Updating your learning signal after the correction…**

---

# 45. Stale Client State

A stale page may disagree with authoritative server state because of:

- another tab;
- refresh timing;
- completed async processing;
- prior retry;
- correction propagation.

When detected:

> **This page has newer information available.**  
> `[Refresh status]`

For consequential state, the product may refresh automatically if doing so will not destroy unsaved input.

---

# 46. Stale Assessment Tab

If one tab submits the assessment while another remains open:

> **This assessment has already been submitted.**  
> Your submitted answers are now read-only.  
> `[View results]`

The stale tab must not overwrite the final attempt.

---

# 47. Refresh Recovery

On refresh, ARIA reloads authoritative workflow state.

Examples:

| Before refresh | After refresh |
|---|---|
| PDF processing | processing / ready / failed based on server |
| active saved assessment | resume assessment |
| submitted assessment | read-only submitted state |
| evaluation pending | pending/results/failure |
| adaptation ready | focused review CTA |
| cycle complete | cycle summary |

Refresh should not restart completed consequential operations blindly.

---

# 48. Back Navigation Recovery

Back navigation must never:

- unsubmit an assessment;
- make submitted answers editable;
- revert evidence/state;
- recreate a resource;
- duplicate adaptation.

If the learner navigates back to an old workflow stage, show it as historical/read-only or redirect to current state where appropriate.

---

# 49. Retry Design

Every retryable failure should specify **what** is being retried.

Prefer:

- `Retry upload`;
- `Retry processing`;
- `Try evaluation again`;
- `Retry focused review`.

Avoid a generic `Retry` when the learner cannot tell which stage failed.

---

# 50. Retry Invariants

Retry must:

1. target the failed stage where possible;
2. preserve valid upstream work;
3. use idempotent handling for consequential operations;
4. not duplicate attempts/evidence/adaptations;
5. update status clearly;
6. stop after bounded automatic retries where appropriate and return control to the learner.

---

# 51. Automatic Retry

Automatic retry is appropriate for some transient operations, but it should be bounded.

Possible pattern:

```text
Operation fails transiently
      ↓
automatic retry with bounded attempts
      ↓
success → continue
or
still fails → learner-visible failure + manual action
```

Do not create invisible infinite retry loops.

---

# 52. Home Recovery Card

When the learner returns later with a failed/pending consequential stage, Home should surface it as the primary next action.

Example:

```text
Assessment evaluation needs attention

Your answers are saved, but the evaluation didn't finish.
No learning signal was changed.

[Try evaluation again]
```

This is more useful than silently sending the learner into unrelated Study.

---

# 53. Safe Resume Messaging

Returning learner examples:

### Active assessment

> Continue your Serializability assessment — 3 of 5 answered.

### Evaluation pending

> Your assessment is submitted. Evaluation is still processing.

### Adaptation ready

> ARIA has a focused review ready for Conflict Detection.

### Reassessment ready

> Your focused review is complete. Take the targeted check when you're ready.

---

# 54. Data-Preservation Claims

UX copy must match actual persistence guarantees.

Do not say:

> Your work is safely saved.

unless the system has confirmed persistence.

Use more precise language when uncertain:

> Your answers are still visible on this device, but we haven't confirmed they reached ARIA yet.

This rule is critical for trust.

---

# 55. Error Severity Levels

Conceptual levels:

## Inline

Small input/local problem; learner remains in flow.

## Section-level

One component failed; rest of screen usable.

## Page-level

Primary screen purpose cannot proceed.

## Global/blocking

Authentication/authorization or system condition prevents app use.

Use the smallest severity that accurately represents the problem.

---

# 56. Error Placement

| Failure | Placement |
|---|---|
| invalid assessment setting | field/section |
| one resource processing failure | resource item |
| Study response failure | conversation message area |
| submission failure | assessment action area/page banner |
| evaluation failure | Results/evaluation state |
| learner-state update failure | concept result/state area |
| session expired | global auth boundary |
| unauthorized object | page/global safe error |

Do not turn every error into a global toast.

---

# 57. Toast Usage

Toasts may confirm non-critical transient events such as:

- settings saved;
- resource removed;
- copied text.

Consequential failures should not exist only as disappearing toasts.

A learner must be able to understand and act on the failure after the toast disappears.

---

# 58. Destructive Actions

For removal/reset actions:

- state what will be removed;
- distinguish current vs historical consequences;
- require confirmation when impact is meaningful;
- do not imply deletion scope that implementation cannot guarantee.

Example:

> Remove this PDF from the current learning context? ARIA will stop using it for future Study responses.

Exact historical retention/deletion semantics belong to privacy/architecture design.

---

# 59. Accessibility of Status & Errors

R0 must support:

- errors not conveyed only by colour;
- status text associated with affected controls;
- focus movement to important blocking errors where appropriate;
- screen-reader announcements for meaningful async completion/failure where practical;
- no rapidly flashing loading indicators;
- retry controls reachable by keyboard;
- error text that remains available long enough to act upon.

---

# 60. Mobile Error UX

On mobile:

- errors should remain close to the affected content;
- bottom sheets/modals must not hide the recovery action;
- long technical-looking messages should not dominate the screen;
- fixed/sticky actions must not cover error text;
- network/offline banners should consume minimal space while remaining visible.

---

# 61. Observability / Validation Events

R0 should record enough non-sensitive product/system events to understand reliability during Gate A/B, including:

- resource upload/processing failure;
- retrieval failure;
- Study generation failure;
- assessment generation failure;
- answer save/sync failure;
- submission uncertainty/failure;
- evaluation failure;
- evidence update failure;
- learner-state recalculation failure;
- adaptation generation failure;
- correction/recheck failure;
- retry attempts and outcomes;
- session expiry;
- resume after failure.

This is not permission to log sensitive document or learner content indiscriminately.

---

# 62. Failure Injection for Gate A

Controlled validation should deliberately test failures rather than waiting for accidental production errors.

At minimum inject/test:

```text
PDF processing failure
Study generation failure
Assessment generation failure
submission retry / duplicate submit
Evaluation failure
Evidence-stage retry
Learner-state update failure
Adapted Study generation failure
Correction propagation failure/retry
Session expiry
Unauthorized cross-user request
```

Gate A passes only when the workflow recovers without corrupting consequential state.

---

# 63. Cross-Product Recovery Invariant

For the R0 pipeline:

```text
Resource
  ↓
Study
  ↓
Assessment
  ↓
Evaluation
  ↓
Evidence
  ↓
learner_concept_state
  ↓
Adaptation
  ↓
Adapted Study
  ↓
Reassessment
```

If stage `N` fails:

> **Valid completed stages before `N` remain valid. Incomplete stages after `N` must not be represented as complete.**

This is the central recovery invariant for ARIA R0.

---

# 64. Anti-Patterns

Avoid:

### Endless spinner

No timeout, status or recovery path.

### Generic failure everywhere

`Something went wrong` for every stage.

### Destructive retry

Restarting the whole adaptive loop when only one downstream call failed.

### False save confirmation

Claiming persistence before server confirmation.

### Error-as-learner-failure

Turning infrastructure failure into incorrect assessment evidence.

### Duplicate retry side effects

Creating multiple attempts/evidence records from repeated clicks.

### Stale success

Showing an old learner_concept_state after corrected evidence without indicating recalculation.

### Toast-only consequential error

Critical failure disappears before learner can act.

### Fake offline capability

Claiming actions are saved/synced when R0 does not guarantee it.

---

# 65. Acceptance Criteria

Step 6 UX is valid only if:

- every major async R0 stage has loading/processing/failure states;
- empty states have clear next actions;
- no-evidence is represented honestly;
- offline behaviour does not overpromise persistence;
- auth/session/authorization failures have safe recovery;
- failed resources never appear ready;
- retrieval failure cannot masquerade as grounded Study;
- assessment generation failure creates no evidence;
- submission uncertainty is reconciled safely;
- evaluation failure cannot become learner weakness;
- evidence/state/adaptation failures are distinguishable;
- downstream failures preserve upstream valid work;
- retries are stage-specific and idempotency-aware;
- refresh/back/multi-tab stale state is recoverable;
- consequential failures remain visible/actionable;
- accessibility requirements apply to status/errors;
- Gate A includes deliberate failure injection.

---

# 66. Traceability

| Prior requirement | Step 6 treatment |
|---|---|
| Resource processing safety | PDF/text failure states |
| Grounding honesty | Retrieval failure UX |
| Assessment persistence | save/submission recovery |
| Deterministic evaluation safety | evaluation failure contract |
| Evidence/state separation | distinct evidence/state failures |
| Downstream failure preservation | adaptation failure recovery |
| Idempotency | retry/submission rules |
| Returning-user resume | Home recovery + safe resume |
| Cross-user isolation | authorization failure UX |
| Accessibility | error/status accessibility |
| Gate A resilience | failure injection matrix |

---

# 67. Scope Guardrail

Step 6 does not freeze:

- exact timeout durations;
- retry backoff algorithm;
- queue technology;
- caching strategy;
- offline database technology;
- monitoring vendor;
- auth provider;
- error-code taxonomy;
- final API response schema;
- final visual component styling.

It freezes the learner-facing reliability and recovery contract.

---

# 68. Step 6 Completion

**Phase 2 — Step 6 is complete.**

ARIA R0 now has a unified UX contract for non-happy paths, including preservation, retry, stale-state handling and safe resume across the entire adaptive-learning pipeline.

Next:

# Step 7 — R0 Wireframe Specification

Step 7 will turn the information architecture, Study UX, assessment UX and recovery rules into low-fidelity screen layouts for the core route-level surfaces and their most important states. This will be the final structural design pass before visual design/component-system decisions.
---

## Next

Step 7 — R0 Wireframe Specification.
