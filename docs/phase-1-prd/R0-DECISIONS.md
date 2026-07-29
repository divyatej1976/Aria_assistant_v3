# ARIA — R0 Product & Validation Decisions

**Status:** FROZEN for R0 implementation  
**Purpose:** Resolve the concrete choices left open by Phase 1 without expanding R0 into the full ARIA vision.

---

## 1. Validation Context

R0 will validate ARIA using a **college-level DBMS learning context**, initially centered on **Transactions, Concurrency Control, Schedules and Serializability**.

Why this context:

- it belongs directly to ARIA's initial college-student audience;
- concepts can be assessed objectively enough for controlled Gate A fixtures;
- the material contains both conceptual understanding and applied reasoning;
- weak concepts can lead to visibly different explanations/examples/practice;
- it is narrow enough for a solo R0 but rich enough to test adaptation;
- it does not become a permanent hardcoded product category.

The product model remains generic: the DBMS context is validation data/configuration, not a permanent `if domain == DBMS` branch.

After R0 is validated, a structurally different second context should be introduced before generalizing abstractions.

---

## 2. R0 Resource Surface

R0 supports:

1. **PDF upload**; and
2. **pasted text**.

A learner may use either or both within the active validation context.

R0 must preserve source/context association so generated study material and assessments can be traced to the selected material where grounding is expected.

Deferred: websites, video ingestion, YouTube, external course synchronization, broad web research ingestion, image-heavy/OCR-first workflows and every planned document type.

---

## 3. R0 Assessment Surface

R0's required assessment format is **MCQ**.

MCQ is deliberately selected because deterministic scoring gives Gate A a clean evidence source and avoids making the first adaptive-loop proof depend on subjective LLM grading.

R0 assessment configuration may include:

- number of questions within supported limits;
- selected topic/concept scope;
- difficulty within supported levels;
- optional time limit;
- targeted reassessment after adaptation.

**Short-answer evaluation is R0 OPTIONAL**, not a completion blocker. It may be implemented only if the core loop is already stable and its AI evaluation can be bounded and tested.

Long-term ARIA still supports learner-chosen assessment formats appropriate to the learner's goal. Selecting MCQ for R0 is a validation constraint, not a permanent product restriction.

---

## 4. Basic Learner-State Representation

R0 uses a conservative concept-level state:

```text
UNTESTED
DEVELOPING
NEEDS_REVIEW
SUPPORTED
```

Each concept state should retain at least:

- `concept_id` / concept reference;
- current state;
- confidence band or score;
- supporting evidence references;
- last evaluated/updated time;
- reason/rule that produced the current state.

Meaning:

### UNTESTED
No sufficient evaluated evidence exists.

### DEVELOPING
Some evidence exists, but it is mixed, limited or not strong enough to justify either `NEEDS_REVIEW` or `SUPPORTED`.

### NEEDS_REVIEW
Repeated or sufficiently strong evidence indicates difficulty and targeted support is justified.

### SUPPORTED
Repeated evidence across separate assessment opportunities indicates the learner currently demonstrates adequate understanding for the R0 context.

`SUPPORTED` deliberately does **not** mean permanent mastery.

---

## 5. Allowed R0 Adaptation Actions

R0 may adapt the next Study experience by:

1. **prioritizing the weak/uncertain concept**;
2. **changing explanation strategy** — e.g. simpler decomposition or alternate framing;
3. **adding a worked example** relevant to the identified gap;
4. **providing prerequisite recap** when the evidence/rules justify it;
5. **changing scaffolding** — more hints/steps for difficulty, less scaffolding when supported;
6. **generating targeted practice/check questions** before reassessment;
7. **reducing unnecessary repetition** for currently supported concepts;
8. **requesting more evidence instead of adapting strongly** when confidence is insufficient.

R0 adaptation does not silently rewrite a Roadmap or Planner because those systems are not part of R0.

Every consequential adaptation must be traceable to the evidence/state that triggered it.

---

## 6. Evidence & Adaptation Policy

R0 begins with an intentionally conservative deterministic policy that can later be refined from validation results.

### Evidence unit

Each deterministically evaluated MCQ produces concept-attributed evidence containing the response/result, assessment attempt, concept/context and provenance.

### Minimum rule

**One isolated answer cannot establish `NEEDS_REVIEW` or `SUPPORTED`.**

### Initial state rules

For a concept with fewer than two meaningful evidence observations:

- no evidence → `UNTESTED`;
- one observation → `DEVELOPING` unless the observation is invalid/unusable.

With at least two usable observations:

- repeated weak/incorrect performance across separate questions/opportunities → candidate `NEEDS_REVIEW`;
- repeated correct performance across separate questions/opportunities → candidate `SUPPORTED`;
- mixed/contradictory evidence → `DEVELOPING` or retain the prior conservative state with reduced confidence.

### Strong adaptation threshold

Targeted remediation requiring a `NEEDS_REVIEW` conclusion should normally require **at least two aligned evidence points**, preferably across distinct questions or attempts.

### Supported threshold

`SUPPORTED` should normally require **at least two aligned correct evidence points**, with at least one coming from a later/independent question or reassessment opportunity rather than duplicate repetition.

### Reassessment

After adaptation, targeted reassessment creates new evidence. New evidence may strengthen, weaken or reverse the previous state estimate.

### Failure/correction rule

Invalid evaluation creates no learning evidence. If an evaluation/evidence record is corrected, dependent learner state and pending adaptation must be recomputed or invalidated as appropriate.

These thresholds are R0 validation defaults, not claims of educational-science mastery measurement.

---

## 7. Gate A Critical Failure Definition

A Gate A run fails critically if any of the following occurs in a required scenario:

- cross-user/private-data access or authorization failure;
- evidence attributed to the wrong learner/context/concept;
- failed/invalid evaluation recorded as valid learning evidence;
- one isolated result incorrectly becomes confirmed mastery/misconception-level state contrary to policy;
- expected evidence fails to update learner state according to the defined fixture/rule;
- learner-state change fails to produce the expected adaptation in a controlled fixture;
- adaptation targets an unrelated concept/context;
- correction does not propagate to dependent state/adaptation where required;
- retry creates duplicate consequential evidence/state/adaptation;
- persisted valid attempts/evidence are lost because a downstream AI stage fails;
- the repeated second cycle cannot generate new evidence and reconsider state;
- a security/secrets failure makes the validation environment unsafe to use.

Gate A passes only when all required critical scenarios pass reproducibly with **zero unresolved critical failures**.

Non-critical UX defects may be recorded separately and do not automatically invalidate the adaptive hypothesis unless they prevent the scenario from being completed reliably.

---

## 8. Gate B Practical Scope

R0 Gate B target:

- **5–10 target learners** where realistically available;
- each participant should complete **at least two connected learning cycles**;
- aim for **10+ completed adaptive cycles total**, while reporting the actual number honestly;
- participants should come from ARIA's initial audience, preferably college students for the DBMS validation context.

Collect:

- baseline/initial assessment observations;
- adaptation shown to the learner;
- targeted reassessment observations;
- whether the adaptation felt relevant/useful;
- whether the learner understood why ARIA adapted;
- incorrect/confusing adaptations;
- learner corrections;
- qualitative comments;
- whether the learner would continue using the adaptive flow.

If fewer than five usable participants are available, Gate B may still be reported as a pilot, but the limitation must be explicit. Gate B never becomes a claim of causal learning improvement from this sample.

---

## R0 Frozen Validation Slice

```text
Authenticated learner
        ↓
One DBMS validation goal/context
        ↓
PDF and/or pasted text
        ↓
Grounded Study
        ↓
Configurable MCQ assessment
        ↓
Deterministic evaluation
        ↓
Concept-attributed evidence
        ↓
UNTESTED / DEVELOPING / NEEDS_REVIEW / SUPPORTED
        ↓
Traceable Study adaptation
        ↓
Targeted MCQ reassessment
        ↓
New evidence + state reconsideration
        ↺
```

---

## Change-Control Rule

These choices are frozen for R0 so implementation can begin from a stable specification.

A change is allowed if validation reveals a genuine blocker, but it must be documented as a deliberate PRD change. New long-term ARIA features must not be pulled into R0 merely because they are desirable.

**R0 product decision set: RESOLVED.**