# ARIA — Phase 2: Product & UX Design

## Step 5 — Assessment, Results & Learner-State UX

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 2 — Product & UX Design  
**Status:** Step 5 complete  
**Inputs:** Frozen Phase 1 PRD + Phase 2 Steps 1–4

---

# 1. Purpose

Assessment is where R0 turns learning activity into structured evidence. The UX therefore has two responsibilities:

1. provide a clear, fair assessment experience; and
2. communicate what the resulting evidence does — and does not — justify.

The assessment UX must not make ARIA feel like a scoring app. Its purpose is to gather useful evidence that can improve the next learning action.

---

# 2. R0 Assessment Model

Required R0 assessment format:

> **MCQ**

R0 assessment flow:

```text
Configure
   ↓
Generate + validate
   ↓
Take assessment
   ↓
Submit
   ↓
Deterministic evaluation
   ↓
Results
   ↓
Evidence
   ↓
Learner-state reconsideration
   ↓
Adapt / gather more evidence / continue
```

Targeted reassessment reuses this model after adapted Study.

---

# 3. Assessment Types in R0

R0 distinguishes two formal assessment purposes.

## Baseline / normal assessment

Used to gather evidence after ordinary Study.

## Targeted reassessment

Used after an adaptation or when more evidence is needed for a specific concept.

Both produce formal evidence only after valid deterministic evaluation.

Informal Study checks remain separate and do not automatically update learner_concept_state.

---

# 4. Assessment Setup Screen

Required controls:

```text
Topic / concept
Question count
Difficulty
Optional timer
```

Example:

```text
Create assessment

Topic
Serializability

Questions
5

Difficulty
Medium

Timer
Off

[Generate assessment]
```

The UI should show only supported configuration values rather than accepting arbitrary options that the implementation cannot honor.

---

# 5. Topic Selection

R0 may constrain topic choices to the validation context, such as:

- Transactions;
- Concurrency Control;
- Schedules;
- Serializability;
- Conflict Serializability.

Where Study already has an active concept, Assessment Setup may preselect it.

The learner can change the selection within supported scope.

---

# 6. Question Count

Question count must stay within a bounded R0 range chosen during implementation.

UX requirements:

- supported values are clear;
- the learner cannot accidentally request an unbounded assessment;
- targeted reassessments may use fewer questions than normal assessments;
- the UI should not imply that more questions automatically produce better learner-state certainty.

Exact limits are an implementation/configuration decision unless validation later requires freezing them.

---

# 7. Difficulty

Difficulty should use a small supported set, for example:

```text
Easy
Medium
Hard
```

Difficulty is assessment configuration, not a learner identity label.

Avoid wording such as:

> ARIA thinks you are an Easy learner.

If adaptation later changes recommended difficulty, the reason should be understandable and bounded.

---

# 8. Timer UX

Timer is optional in R0.

When disabled, no hidden time pressure should exist.

When enabled:

- duration is shown before starting;
- remaining time is visible but not unnecessarily distracting;
- timer warnings are accessible and not colour-only;
- expiry behaviour is stated before the assessment;
- server/client timing differences must not create ambiguous submission outcomes;
- accessibility needs must be considered.

R0 should prefer simple, predictable timer behaviour over sophisticated proctoring.

---

# 9. Assessment Generation State

After `Generate assessment`:

```text
Preparing your assessment…
```

The learner should know:

- topic;
- question count;
- that generation is in progress.

If generation fails:

> I couldn't create a valid assessment right now. Your learning context is safe.

Actions:

- `Try again`
- `Change settings`
- `Return to Study`

No evidence/state is changed by generation failure.

---

# 10. Assessment Start Screen

Before entering the first question, show a compact summary:

```text
Serializability Check
5 questions · Medium
No timer

Your submitted answers will be used as learning evidence
so ARIA can decide what to focus on next.

[Start]
```

For targeted reassessment:

```text
Targeted check: Conflict Serializability
3 new questions

This check will give ARIA another signal after your focused review.

[Start check]
```

---

# 11. Assessment Session Layout

Conceptual layout:

```text
┌──────────────────────────────────────────────────────┐
│ Serializability       Question 2 of 5       08:42    │
├──────────────────────────────────────────────────────┤
│                                                      │
│ Question text                                        │
│                                                      │
│ ○ Option A                                           │
│ ○ Option B                                           │
│ ● Option C                                           │
│ ○ Option D                                           │
│                                                      │
├──────────────────────────────────────────────────────┤
│ [Previous]                        [Next]              │
│                                                      │
│ Questions: 1  2  3  4  5                            │
└──────────────────────────────────────────────────────┘
```

The interface should prioritize answering, not learner-model information.

---

# 12. Answer Selection

Required behaviour:

- exactly one selected answer per single-answer MCQ;
- selection is visually clear;
- selection is not communicated by colour alone;
- keyboard interaction works;
- changing an answer before submission is allowed;
- final submitted answer becomes immutable unless the product explicitly supports correction through a separate workflow.

ARIA should not reveal correctness during a formal assessment unless the assessment mode explicitly permits it; R0 formal evidence assumes post-submission evaluation.

---

# 13. Question Navigation

The learner may navigate among questions before final submission.

Question navigator should distinguish:

- current;
- answered;
- unanswered.

It should not distinguish correct/incorrect before submission.

---

# 14. Leaving an Assessment

If progress is safely persisted:

> Your answers are saved. You can continue this assessment later.

If leaving risks unsaved work:

> Leave assessment? Your latest unsaved changes may be lost.

The final implementation should minimize unsaved-risk states.

---

# 15. Submission Review

Before final submission, especially with unanswered questions:

```text
Submit assessment?

Answered: 4 of 5
Unanswered: 1

After submission, your answers cannot be changed.

[Continue assessment]
[Submit]
```

If all questions are answered, confirmation may be lighter but finality should remain clear.

---

# 16. Submission State

After submit:

```text
Submitting your answers…
```

The submit control becomes non-repeatable while the operation is pending.

If the network outcome is uncertain, ARIA reconciles the attempt rather than encouraging creation of another attempt.

---

# 17. Evaluation State

After successful submission:

```text
Answers saved
Evaluating your assessment…
```

Because MCQ evaluation is deterministic, R0 should normally make this transition quickly, but the UX must still support asynchronous/failure states.

---

# 18. Evaluation Failure

If evaluation fails:

```text
Your answers are safe

We couldn't evaluate this assessment right now.
No learning signal has been changed.

[Try evaluation again]
```

Do not show:

- score;
- wrong-answer state;
- learner-state change;
- adaptation;

until evaluation is valid.

---

# 19. Results Information Hierarchy

The results screen should answer, in order:

```text
1. How did I do?
2. What did I miss?
3. What does ARIA have enough evidence to say?
4. What happens next?
5. Why?
```

System internals belong below these learner questions.

---

# 20. Results Header

Example:

```text
Assessment complete

3 / 5 correct
Serializability

[Review answers]
```

Score should be visible but should not dominate the entire adaptive-learning experience.

---

# 21. Concept-Level Results

Where questions map to concepts, results can summarize evidence by concept.

Example:

```text
Conflict detection
2 questions · 0 correct
Current signal: Worth reviewing

Precedence graph cycles
2 questions · 2 correct
Current signal: Still building confidence
```

The signal must follow evidence policy rather than simply converting percentages into labels.

---

# 22. Internal vs Learner-Facing State

| Internal state | Learner-facing default |
|---|---|
| `UNTESTED` | Not enough evidence yet |
| `DEVELOPING` | Still building confidence |
| `NEEDS_REVIEW` | Worth reviewing |
| `SUPPORTED` | Current results look solid |

Internal enum names may appear in developer/debug tooling but should not be the primary learner-facing language.

---

# 23. State Card Anatomy

A concept signal card should include:

```text
Concept
Learner-facing state
Short evidence basis
Optional confidence/uncertainty explanation
Next action
```

Example:

```text
Conflict detection
Worth reviewing

You missed two different questions that required
identifying conflicting operations.

Next: work through a schedule step by step.

[Why this?]
[Start focused review]
```

---

# 24. UNTESTED UX

Use when there is not enough usable evidence.

Example:

> **Not enough evidence yet**  
> ARIA hasn't seen a formal result for this concept yet.

Do not show a zero score as though zero evidence means zero knowledge.

---

# 25. DEVELOPING UX

Use when evidence exists but does not justify a strong conclusion.

Example:

> **Still building confidence**  
> I have one usable result on this concept. Let's gather another signal before making a strong change.

Possible next action:

`Take another focused check`

or normal Study.

---

# 26. NEEDS_REVIEW UX

Use only when conservative policy is satisfied.

Example:

> **Worth reviewing**  
> Two separate assessment opportunities showed difficulty with identifying conflicts in schedules.

Then show the bounded adaptation ARIA proposes.

Avoid:

> You don't understand serializability.

---

# 27. SUPPORTED UX

Example:

> **Current results look solid**  
> Your recent independent results support this concept, so ARIA won't repeat the basic explanation unless you ask.

Avoid:

> Mastered forever.

`SUPPORTED` may later change when new evidence arrives.

---

# 28. Evidence Detail

`Why this?` opens a concise evidence explanation.

Example:

```text
Why ARIA shows "Worth reviewing"

Assessment 1
Question 2 — Incorrect
Concept: Conflict detection

Assessment 2 / distinct opportunity
Question 1 — Incorrect
Concept: Conflict detection

ARIA requires more than one aligned observation
before showing a strong review signal.
```

The learner does not need to see database IDs, model prompts or confidence internals.

---

# 29. Evidence Provenance UX

When useful, the learner should be able to trace a signal back to:

```text
Assessment
  ↓
Question
  ↓
Learner answer
  ↓
Correct answer
  ↓
Evaluation
  ↓
Concept attribution
```

This supports trust and correction without turning the results screen into developer tooling.

---

# 30. Review Answers

Question review should show:

- question text;
- learner's submitted answer;
- correct answer;
- correct/incorrect result;
- explanation;
- concept;
- optional link to evidence effect;
- challenge action.

Example:

```text
Question 2

Which pair conflicts?

Your answer: R1(X), R2(X)
Correct answer: W1(X), R2(X)

Why:
Two reads do not conflict. At least one operation must be a write.

Concept: Conflict detection

[This result looks wrong]
```

---

# 31. Correct Answers

Correct answers should receive useful explanation where appropriate, not only a green check.

Example:

> Correct. `W1(X)` and `R2(X)` access the same item from different transactions and one operation is a write.

This reinforces reasoning without turning every result into a lecture.

---

# 32. Incorrect Answers

Incorrect-answer feedback should explain the reasoning gap without making an unsupported diagnosis.

Prefer:

> These operations access the same item, but both are reads, so they do not satisfy the write condition for a conflict.

Avoid:

> You have a misconception about read operations.

unless later evidence and a future misconception system genuinely justify that conclusion.

---

# 33. Challenge Flow

From answer review:

```text
[This result looks wrong]
      ↓
Explain what is being challenged
      ↓
Recheck / correction mechanism
      ↓
Outcome
```

Possible outcomes:

```text
Evaluation unchanged
Evaluation corrected
Concept attribution corrected
```

If correction changes evidence, downstream learner_concept_state and pending adaptation must be reconsidered.

---

# 34. Correction Confirmation

If corrected:

> **Result corrected**  
> This answer is now recorded correctly. ARIA is updating the learning signal that depended on it.

Then show a processing state until dependent state/adaptation is reconciled.

Do not leave stale `NEEDS_REVIEW` messaging visible after the evidence supporting it has been invalidated.

---

# 35. State Reconsideration UX

When new/corrected evidence causes state recalculation, avoid dramatic gamified transitions.

Possible message:

> Your learning signal for Conflict Detection has been updated based on the corrected result.

Then display the new current state and evidence basis.

---

# 36. Adaptation CTA from Results

If adaptation is justified:

```text
Next recommended step

Work through a conflict-serializability schedule step by step,
then take a short targeted check.

[Start focused review]
```

If strong adaptation is not justified:

```text
I need another signal before changing your Study experience strongly.

[Take focused check]
[Continue studying]
```

---

# 37. Targeted Reassessment Setup

Targeted reassessment should require less configuration than a normal assessment because ARIA already knows the concept/purpose.

Example:

```text
Targeted check
Conflict detection
3 new questions · Medium

This check will be used as new formal evidence.

[Start]
```

The learner may be allowed to adjust supported settings if doing so does not undermine the validation purpose.

---

# 38. Reassessment Independence

The reassessment UX should explicitly avoid exact answer repetition.

Possible learner-facing note:

> These are new questions on the same concept, so ARIA can collect another signal rather than test whether you remember the previous answer.

This supports the R0 validation thesis.

---

# 39. Reassessment Results

The second results view should emphasize comparison without causal overclaiming.

Example:

```text
Targeted check complete

Conflict detection
Previous signal: Worth reviewing
Current signal: Still building confidence

Your latest check added new correct evidence.
ARIA has updated the current signal accordingly.
```

Avoid:

> ARIA taught you successfully.

or:

> Your learning improved by 42% because of adaptation.

unless future research actually supports such claims.

---

# 40. Cycle Summary

After the second evidence cycle:

```text
Learning cycle complete

Conflict Serializability

Initial assessment
Repeated difficulty identifying conflicts

ARIA changed Study
Worked schedule + more scaffolding

Targeted reassessment
New independent evidence collected

Current signal
Still building confidence

[Continue studying]
[Review details]
```

This is the primary learner-facing proof that ARIA connected assessment to future learning.

---

# 41. Continued Difficulty

If reassessment remains weak:

> **Still worth reviewing**  
> The new targeted check showed the same difficulty again. We can try a different explanation or revisit the prerequisite concept.

Actions may include:

- another bounded focused review;
- prerequisite recap;
- continue Study.

Do not shame the learner or imply failure of the learner.

---

# 42. Contradictory Reassessment

If new evidence conflicts with prior evidence:

> **Results are mixed**  
> Your latest answer was correct, but earlier results showed difficulty. I don't have enough evidence to call this solid yet.

Next action:

- gather another independent signal;
- continue Study;
- inspect evidence.

---

# 43. Stronger Supported Signal

When policy truly supports `SUPPORTED`:

> **Current results look solid**  
> Multiple independent results now support this concept. I'll reduce basic repetition and focus on applying it in harder examples.

This is still reversible when future evidence changes.

---

# 44. Score vs learner_concept_state

R0 must keep these separate.

```text
Assessment score
= performance on one assessment

learner_concept_state
= conservative conclusion from relevant evidence across opportunities
```

Therefore:

- 100% on one small assessment does not automatically equal `SUPPORTED`;
- 0% on one assessment does not automatically equal `NEEDS_REVIEW`;
- concept-level evidence matters more than a single overall percentage for adaptation.

The UX should not visually imply otherwise.

---

# 45. Confidence Without Fake Precision

R0 should prefer qualitative uncertainty explanations.

Examples:

- `Not enough evidence yet`;
- `One result so far`;
- `Multiple results point in the same direction`;
- `Results are mixed`.

Avoid default learner-facing percentages such as:

> Confidence: 73.8%

unless such numbers later become meaningful and validated.

---

# 46. Evidence Recency

R0 may show simple temporal context:

```text
Latest evidence: today
```

But it does not need a sophisticated forgetting/decay model.

`SUPPORTED` should not be presented as permanent even if R0 does not yet implement mature longitudinal decay.

---

# 47. Results Accessibility

Results must not rely only on red/green.

Use:

- icons + labels;
- explicit `Correct` / `Incorrect` text;
- semantic headings;
- keyboard-accessible answer review;
- accessible expandable evidence explanations;
- logical focus movement after submission;
- screen-reader-friendly status updates where practical.

---

# 48. Assessment Accessibility

Required baseline:

- radio controls/answer options are semantically labeled;
- question text is associated with controls;
- keyboard selection/navigation works;
- focus is visible;
- timer warnings are announced accessibly where practical;
- no essential interaction requires drag/hover;
- target sizes support touch;
- error messages identify the problem clearly.

---

# 49. Mobile Assessment UX

On smaller screens:

```text
Topic + progress
Timer (if enabled)
Question
Large answer targets
Previous / Next
Question overview access
```

Do not compress all question numbers into an unusable horizontal strip. Use a drawer/sheet/grid if necessary.

Submission remains clearly separated from answer selection.

---

# 50. Assessment Validation Events

R0 should capture enough events to validate the product experience, such as:

- assessment configured;
- generation succeeded/failed;
- assessment started;
- assessment abandoned/resumed;
- submitted;
- evaluation succeeded/failed;
- results viewed;
- evidence explanation opened;
- answer review opened;
- result challenged;
- correction occurred;
- adaptation CTA accepted/skipped;
- reassessment started/completed;
- cycle completed.

These are product-validation requirements, not a demand for a large analytics dashboard.

---

# 51. Assessment Anti-Patterns

Avoid:

### Score-only UX

Showing `3/5` and providing no concept/evidence meaning.

### State-from-score shortcut

`<50% = weak`, `>80% = mastered` regardless of evidence policy.

### Premature feedback leakage

Revealing answers during a formal evidence-producing assessment unintentionally.

### Retake-as-recovery

Forcing a learner to redo an assessment because evaluation infrastructure failed.

### Fake certainty

Showing precise mastery percentages without validated meaning.

### Hidden evidence

Changing Study without allowing the learner to inspect why.

### Permanent labels

Treating `SUPPORTED` or `NEEDS_REVIEW` as learner identity.

### Repeated-question reassessment

Calling memorization of the revealed answer new independent evidence.

### Correction dead-end

Correcting an answer but leaving stale learner_concept_state/adaptation unchanged.

---

# 52. Acceptance Criteria

Step 5 UX is valid only if:

- MCQ configuration is bounded and understandable;
- baseline and targeted assessments are distinguishable;
- generation/failure states are explicit;
- answer selection/navigation/submission are safe;
- evaluation failure creates no false result/evidence;
- score and learner_concept_state are visibly distinct concepts;
- all four learner states have conservative learner-facing language;
- evidence basis is inspectable;
- question-level review is available;
- correction can propagate to visible state/adaptation;
- insufficient and contradictory evidence are represented honestly;
- targeted reassessment uses new evidence opportunities;
- second-cycle comparison avoids causal overclaiming;
- assessment/results are accessible and responsive;
- product events support Gate A/B validation.

---

# 53. Traceability

| Frozen requirement / prior UX decision | Step 5 treatment |
|---|---|
| Configurable R0 MCQ | Setup UX |
| Deterministic evaluation | Evaluation state/result contract |
| Invalid evaluation creates no evidence | Evaluation failure UX |
| Concept-attributed evidence | Concept results/evidence detail |
| UNTESTED/DEVELOPING/NEEDS_REVIEW/SUPPORTED | Learner-facing state system |
| Conservative thresholds | State wording and score separation |
| Evidence provenance | Why-this/evidence detail |
| Correction propagation | Challenge/correction UX |
| Adaptation visibility | Results next-step CTA |
| Targeted reassessment | Dedicated reassessment flow |
| Second cycle required | Reassessment results + cycle summary |
| No causal overclaiming | Comparison wording |
| Accessibility | Assessment/results baseline |

---

# 54. Scope Guardrail

Step 5 does not freeze:

- exact supported question-count limits;
- final difficulty-generation algorithm;
- exact timer duration options;
- question-generation model/provider;
- database schema;
- final confidence calculation;
- sophisticated item-response theory;
- psychometric validity claims;
- proctoring;
- anti-cheat surveillance;
- every future assessment type;
- visual brand styling.

It freezes the R0 learner-facing assessment/evidence/state contract.

---

# 55. Step 5 Completion

**Phase 2 — Step 5 is complete.**

ARIA R0 now has a complete learner-facing contract for formal assessment, deterministic results, evidence transparency, conservative learner-state communication, correction and targeted reassessment.

Next:

# Step 6 — Error, Empty, Loading & Recovery UX

Step 6 will consolidate all cross-product non-happy states into one UX specification: loading/processing feedback, empty states, network/offline behaviour, authentication/session failures, resource-processing errors, assessment/evaluation failures, AI-generation failures, retry behaviour, stale-state recovery and safe return/resume patterns.
---

## Next

Step 6 — Error, Empty, Loading & Recovery UX.
