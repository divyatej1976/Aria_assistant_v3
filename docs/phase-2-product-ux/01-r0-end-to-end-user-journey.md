# ARIA — Phase 2: Product & UX Design

## Step 1 — R0 End-to-End User Journey

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 2 — Product & UX Design  
**Status:** Step 1 complete  
**Product baseline:** `docs/phase-1-prd/PRD.md` + `R0-DECISIONS.md`

---

# 1. Purpose

Phase 1 defined what R0 must do. Phase 2 defines how a learner actually experiences it.

This document maps the complete R0 journey from first arrival through the second adaptive learning cycle, including the important failure, uncertainty, correction and return paths.

The UX must make ARIA's central difference visible:

> ARIA does not merely answer questions or generate quizzes. It uses evidence from learning activity to change what happens next, while showing the learner enough of that reasoning to remain understandable and correctable.

---

# 2. UX Principles for R0

1. **Learning first, system complexity hidden.** Learners should not need to understand evidence pipelines or state machines.
2. **Adaptation must be visible.** If ARIA changes Study because of evidence, the learner should be able to tell that something changed and why.
3. **State is tentative, not judgmental.** `NEEDS_REVIEW` is a current evidence signal, not a label on the learner.
4. **No evidence is not weakness.** Untested concepts remain untested.
5. **Learner control matters.** The learner may inspect/challenge an incorrect evaluation or adaptation.
6. **Failures preserve work.** A failed AI step must not force the learner to redo a completed assessment.
7. **The second cycle matters.** R0 UX is incomplete until adaptation is followed by targeted reassessment and state reconsideration.
8. **R0 stays narrow.** No Planner, Notes, Audio, Roadmap orchestration or other later-release surface is introduced into this journey.

---

# 3. Canonical R0 Journey

```text
LANDING
   ↓
SIGN UP / SIGN IN
   ↓
FIRST-TIME SETUP
   ↓
CREATE LEARNING CONTEXT
   ↓
ADD PDF / PASTED TEXT
   ↓
RESOURCE PROCESSING
   ↓
STUDY
   ↓
CONFIGURE MCQ
   ↓
ASSESSMENT
   ↓
SUBMIT
   ↓
DETERMINISTIC EVALUATION
   ↓
RESULT + EVIDENCE
   ↓
BASIC learner_concept_state
   ↓
ARIA EXPLAINS NEXT ADAPTATION
   ↓
ADAPTED STUDY
   ↓
TARGETED REASSESSMENT
   ↓
NEW EVIDENCE
   ↓
STATE RECONSIDERED
   ↓
CYCLE SUMMARY / CONTINUE
```

---

# 4. Stage 0 — Landing

## Learner intent

Understand what ARIA does and begin using it.

## UX

The landing experience should communicate the product in learner language, for example:

> Learn with your own material. Test yourself. Let ARIA use your results to adapt what you study next.

Primary actions:

- **Get started**
- **Sign in**

The landing page should not advertise every long-term ARIA subsystem as though it already exists in R0.

---

# 5. Stage 1 — Authentication

## New learner

```text
Get started
   ↓
Create account
   ↓
Authentication succeeds
   ↓
First-time setup
```

## Returning learner

```text
Sign in
   ↓
Authentication succeeds
   ↓
Existing R0 context found?
   ├── Yes → Resume workspace
   └── No  → Create learning context
```

## Failure states

- invalid credentials;
- expired session;
- network/auth provider failure;
- unauthorized resource/context access.

Failures should be explicit and must never expose another learner's data.

---

# 6. Stage 2 — First-Time Setup

R0 onboarding should be short.

ARIA needs only information required to establish the validation experience.

Suggested first-time setup:

```text
Welcome to ARIA
      ↓
What are you preparing for?
      ↓
College subject / exam
      ↓
DBMS validation context
```

Because DBMS is the frozen R0 validation fixture, the UI may present it directly in the validation build rather than pretending arbitrary domains are fully supported.

The implementation should still model the context generically enough that DBMS is configuration rather than permanent product logic.

---

# 7. Stage 3 — Learning Context

The learner enters the R0 workspace.

Visible context should include enough orientation to answer:

- What am I studying?
- What material is ARIA using?
- What should I do next?

R0 context example:

```text
DBMS
Transactions & Concurrency

Resources: 1 PDF
Current next step: Study
```

The learner should not need to manually coordinate hidden evidence/state systems.

---

# 8. Stage 4 — Add Learning Material

The learner can:

- upload a supported PDF;
- paste text;
- use both.

## PDF path

```text
Choose PDF
   ↓
Validate file
   ↓
Upload
   ↓
Processing
   ↓
Ready
```

## Pasted-text path

```text
Paste text
   ↓
Validate input
   ↓
Save/process
   ↓
Ready
```

## Resource UI states

- uploading;
- processing;
- ready;
- failed;
- unsupported;
- removed.

A learner must not enter a grounded Study experience while ARIA silently believes a failed resource was successfully processed.

---

# 9. Resource Failure Branch

```text
Upload resource
      ↓
Processing fails
      ↓
Show failure clearly
      ↓
Preserve context
      ↓
Retry / remove / replace resource
```

Do not:

- pretend retrieval succeeded;
- silently continue as grounded Study;
- erase other valid resources;
- destroy the learner's learning context.

---

# 10. Stage 5 — Baseline Study

Once material is ready, the learner enters **Study**.

Study may provide:

- explanations;
- examples;
- learner questions and ARIA answers;
- concept-focused teaching grounded in selected resources where appropriate;
- an obvious path to test understanding.

The learner should be able to move naturally from:

```text
Learn
  ↓
Think I understand this
  ↓
Test me
```

R0 should avoid turning Study into a giant dashboard containing future features.

---

# 11. Stage 6 — Configure Assessment

The learner chooses **Test me / Create assessment**.

Required R0 format: **MCQ**.

Configuration may expose:

- topic/concept;
- question count within supported limits;
- difficulty;
- optional timer.

Example:

```text
Create Assessment

Topic: Serializability
Questions: 5
Difficulty: Medium
Timer: Off

[Generate Assessment]
```

The learner is choosing within the R0-supported assessment surface, not being told that MCQ is ARIA's permanent universal exam format.

---

# 12. Assessment Generation States

```text
Configuration
      ↓
Generating
      ↓
Validation
      ↓
Valid?
 ├── Yes → Assessment ready
 └── No  → bounded repair/retry
              ↓
          still invalid?
              ↓
          explicit failure
```

If generation fails, the learner's context/resources remain intact.

---

# 13. Stage 7 — Take Assessment

The assessment experience should prioritize answering questions, not showing learner-state machinery.

Required behaviours:

- clear question numbering;
- selected answer visible;
- navigation appropriate to supported question count;
- timer only if enabled;
- explicit submit action;
- submission confirmation when needed;
- keyboard-operable controls;
- accessible focus/error states.

---

# 14. Stage 8 — Submission & Evaluation

```text
Learner submits
      ↓
Attempt persisted
      ↓
Deterministic MCQ evaluation
      ↓
Evaluation valid?
 ├── Yes → create evidence
 └── No  → attempt remains saved
           no learning evidence created
           retry evaluation
```

The UX must never make an evaluation-service failure look like the learner answered incorrectly.

---

# 15. Stage 9 — Results

The first results view should answer the learner's immediate questions:

- How did I do?
- What did I get wrong/right?
- What concepts need attention?
- What is ARIA going to do next?

Example:

```text
Assessment complete
3 / 5 correct

Serializability
Current evidence: Developing

ARIA noticed difficulty across the questions
about conflict-serializable schedules.

Next: review this concept with a worked example
before trying a targeted check.
```

The UX should avoid statements such as:

> You are bad at DBMS.

or:

> You have mastered serializability.

when the evidence does not justify them.

---

# 16. Stage 10 — Basic learner_concept_state UX

Internal R0 states:

```text
UNTESTED
DEVELOPING
NEEDS_REVIEW
SUPPORTED
```

Learner-facing language can be softer and explanatory:

| Internal state | Possible learner-facing wording |
|---|---|
| `UNTESTED` | Not enough evidence yet |
| `DEVELOPING` | Still building confidence |
| `NEEDS_REVIEW` | Worth reviewing |
| `SUPPORTED` | Current results look solid |

The UI should expose evidence context where useful rather than presenting the state as an unquestionable score.

---

# 17. Insufficient-Evidence Branch

```text
Assessment evidence
      ↓
Only one / insufficient observation
      ↓
DEVELOPING
      ↓
ARIA does NOT declare weakness/mastery
      ↓
Ask another targeted question
or continue normal Study
```

Possible learner message:

> I don't have enough evidence yet to make a strong call on this concept. Let's check it once more.

---

# 18. Contradictory-Evidence Branch

```text
Evidence A → difficulty
Evidence B → supported result
      ↓
Mixed evidence
      ↓
Confidence reduced
      ↓
Do not force strong label
      ↓
Targeted diagnostic/reassessment
```

Learner-facing explanation might say:

> Your recent answers are mixed, so I'd rather check this concept again before changing your study plan strongly.

R0 does not need a full misconception engine to behave responsibly here.

---

# 19. Stage 11 — Adaptation Explanation

This is one of ARIA R0's most important UX moments.

The learner should see three things:

```text
WHAT ARIA OBSERVED
        ↓
WHAT ARIA THINKS CURRENTLY
        ↓
WHAT WILL CHANGE NEXT
```

Example:

```text
What I noticed
You missed two different questions involving
conflict-serializable schedules.

Current signal
This concept is worth reviewing.

What I'm changing
I'll use a step-by-step worked schedule before
asking you another targeted question.

[Start adapted study]
```

This is far more useful than silently changing content behind the scenes.

---

# 20. Learner Challenge / Correction Branch

The learner must have a way to challenge a consequential conclusion.

Possible actions:

- **Review answers**
- **This result looks wrong**
- **Why did ARIA choose this?**

```text
Learner challenges result
      ↓
Review source answer/evaluation
      ↓
Was evaluation incorrect?
 ├── Yes → correct evaluation
 │          ↓
 │       revise evidence
 │          ↓
 │       recompute state
 │          ↓
 │       recompute/invalidate adaptation
 │
 └── No  → retain evidence
           explain current reasoning
           optionally gather more evidence
```

A learner claiming "I know this" does not automatically overwrite valid contrary evidence, but ARIA should not trap them inside an unchallengeable label either.

---

# 21. Stage 12 — Adapted Study

The learner enters a Study experience materially influenced by evidence.

Possible R0 adaptations:

- simpler decomposition;
- alternate explanation;
- worked example;
- prerequisite recap;
- additional scaffolding/hints;
- targeted practice;
- reduced repetition for supported concepts;
- diagnostic question when evidence remains uncertain.

The interface should make the adapted purpose clear without overwhelming the learner with system internals.

Example header:

> **Focused review: Conflict Serializability**  
> Based on your latest assessment, we're reviewing this before the next check.

---

# 22. Stage 13 — Targeted Reassessment

After adapted Study, ARIA offers a targeted reassessment.

```text
Adapted Study
      ↓
Ready to check again?
      ↓
Targeted MCQ reassessment
      ↓
Independent/new evidence
```

The reassessment should test the relevant concept without merely repeating the exact same answer-revealed question.

---

# 23. Stage 14 — State Reconsideration

The new evidence is evaluated using the same conservative rules.

Possible outcomes:

### Improvement signal

```text
NEEDS_REVIEW / DEVELOPING
        ↓
new independent correct evidence
        ↓
state/confidence reconsidered
```

### Continued difficulty

```text
new weak evidence
        ↓
NEEDS_REVIEW remains / strengthens
        ↓
ARIA may recommend another supported R0 action
```

### Still mixed

```text
contradictory evidence remains
        ↓
DEVELOPING / uncertainty
        ↓
ARIA requests more evidence rather than pretending certainty
```

---

# 24. Stage 15 — Cycle Summary

After the second cycle, the learner should receive a compact summary.

Example:

```text
Learning cycle complete

Serializability
Before: Worth reviewing
After reassessment: Current results look stronger

What changed
✓ Reviewed a worked schedule
✓ Practiced conflict detection
✓ Completed targeted reassessment

[Continue studying]
[Review assessment]
```

ARIA may say that the **evidence/state changed after adaptation**. It should not claim the adaptation scientifically caused human learning improvement.

---

# 25. Returning Learner Journey

```text
Sign in
   ↓
ARIA restores active context
   ↓
Show current status
   ↓
Resume most relevant unfinished step
```

Examples:

- resource ready but Study not started → **Continue Study**;
- assessment generated but not submitted → **Continue Assessment**;
- attempt submitted but evaluation failed → **Retry evaluation / status**;
- adaptation ready → **Continue focused review**;
- adapted Study completed → **Take targeted reassessment**.

Do not force the learner to reconstruct the workflow manually.

---

# 26. Downstream AI Failure Branch

Example: evidence/state is valid, but adapted explanation generation fails.

```text
Valid attempt
   ↓
Valid evaluation
   ↓
Valid evidence/state
   ↓
Adapted Study generation fails
   ↓
Preserve all valid prior work
   ↓
Show retry
```

The learner must never have to retake the assessment solely because a later generation call failed.

---

# 27. Retry / Idempotency UX

When the learner retries:

- retry should resume the failed stage where possible;
- the UI should not create duplicate attempts/evidence;
- repeated button clicks should be safely handled;
- completed stages should remain completed.

Example:

```text
Evaluation failed

Your answers are safely saved.
We couldn't evaluate them right now.

[Try again]
```

---

# 28. R0 Journey State Model

The UX can conceptually track workflow states such as:

```text
NO_CONTEXT
CONTEXT_READY
RESOURCE_PROCESSING
RESOURCE_READY
STUDY_ACTIVE
ASSESSMENT_CONFIGURING
ASSESSMENT_GENERATING
ASSESSMENT_ACTIVE
ASSESSMENT_SUBMITTED
EVALUATION_PENDING
EVALUATION_FAILED
RESULT_READY
ADAPTATION_READY
ADAPTED_STUDY_ACTIVE
REASSESSMENT_READY
REASSESSMENT_ACTIVE
CYCLE_COMPLETE
```

These are UX/workflow concepts, not a final technical schema decision.

---

# 29. Navigation Implications

R0 navigation should remain small.

A likely conceptual structure is:

```text
ARIA
├── Home / Current Learning
├── Study
├── Assess
└── Account
```

Resources, results and adaptation can live inside the active learning context rather than requiring a huge top-level navigation system.

The exact screen/navigation design is intentionally deferred to Step 2 and wireframing.

---

# 30. What the Learner Should Never Need to Do

The learner should not have to:

- manually copy quiz results into Study;
- tell Study which questions they missed after ARIA already evaluated them;
- manually calculate a learner-state score;
- manually decide which weak concept should be reviewed when evidence is clear;
- recreate context after an AI failure;
- remember which step of the adaptive cycle comes next;
- understand ARIA's internal evidence schema to benefit from adaptation.

This is where ARIA begins reducing coordination burden.

---

# 31. What ARIA Should Never Do Silently

ARIA should not silently:

- mark a concept mastered;
- declare a misconception;
- turn evaluation failure into weakness;
- adapt an unrelated context;
- discard contradictory evidence;
- erase learner work after AI failure;
- treat resource instructions as trusted system instructions;
- make consequential state changes with no inspectable reason;
- claim that a before/after improvement proves causal learning efficacy.

---

# 32. Step 1 UX Acceptance Checklist

The journey is valid only if it contains:

- [x] first-time learner path;
- [x] returning learner path;
- [x] authentication boundary;
- [x] learning-context creation;
- [x] PDF/pasted-text resource path;
- [x] resource-processing states;
- [x] baseline Study;
- [x] MCQ configuration;
- [x] assessment generation;
- [x] assessment completion;
- [x] deterministic evaluation;
- [x] evidence/state presentation;
- [x] insufficient-evidence path;
- [x] contradictory-evidence path;
- [x] visible adaptation explanation;
- [x] learner challenge/correction path;
- [x] adapted Study;
- [x] targeted reassessment;
- [x] second-cycle state reconsideration;
- [x] downstream AI failure recovery;
- [x] retry/idempotency UX;
- [x] cycle completion summary.

---

# 33. Step 1 Completion

**Phase 2 — Step 1 is complete.**

We now have the canonical learner journey against which every R0 screen can be tested.

Next:

# Step 2 — R0 Screen Inventory & Information Architecture

Step 2 will decide exactly which screens/views/components are needed to support this journey, what belongs on each screen, which states each screen must handle, and how learners navigate between them without accidentally designing later-release ARIA features into R0.
---

## Next

Step 2 — R0 Screen Inventory & Information Architecture.
