# ARIA — Phase 1 PRD

## Step 8 — Acceptance Criteria, Success Metrics & PRD Closure

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Reviewed for amended R0 validation model  
**Primary sources:** `VISION.md`, Steps 1–7 of the Phase 1 PRD

---

# 1. Purpose

This document defines how ARIA requirements become testable product outcomes.

The central rule is:

> **A release is not complete because its UI exists or its pipeline executes once. It is complete when the release hypothesis has been tested at the appropriate level.**

For R0, this requires two distinct gates:

- **Gate A — Engineering Validation:** rigorous and reproducible;
- **Gate B — Real-User Signal:** small-scale and directional, without causal overclaiming.

---

# 2. R0 Hypothesis

> **ARIA can observe meaningful learning evidence, update a basic learner state, and use that state to appropriately change the learner's next study experience.**

R0 therefore validates this loop:

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
 Basic Learner State
          ↓
Adapt Next Study Experience
          ↓
          ↺
```

R0 acceptance is intentionally narrower than acceptance of the complete Learning OS.

---

# 3. R0 Validation Context

R0 shall use one or a small number of representative learning contexts from ARIA's initial audience: college students, recent graduates, and early-career learners.

The validation context should be concrete enough to produce repeatable learning cycles and meaningful assessment evidence.

R0 is **not required** to prove that the same implementation is equally effective for every university subject, certification, competitive exam, placement journey, interview type, or professional skill.

A later structurally different context should be used to expose assumptions before generalizing abstractions.

---

# 4. Core R0 User Journey

A learner can complete at least two connected learning cycles:

```text
Create / enter validation goal-context
        ↓
Add/select supported learning material
        ↓
Study with ARIA
        ↓
Take supported assessment
        ↓
Receive validated evaluation
        ↓
Evidence is stored
        ↓
Basic learner state changes when warranted
        ↓
ARIA adapts the next study experience
        ↓
Learner studies again
        ↓
Targeted reassessment / new evidence
```

The second cycle matters: a one-shot Study → Assessment demo does not prove adaptation influenced future behaviour.

---

# 5. R0 Acceptance — Foundation

## AC-R0-FND-001

A learner can securely access their own validation workspace and persistent learning context.

## AC-R0-FND-002

Private learner-owned validation data cannot be accessed by another normal learner through predictable/copied identifiers.

## AC-R0-FND-003

The validation goal/context persists across the repeated cycles required for testing.

## AC-R0-FND-004

Failures in later AI stages do not erase already persisted learner input, assessment attempts, or valid evidence.

---

# 6. R0 Acceptance — Resources & Study

## AC-R0-STUDY-001

A learner can provide/select at least the resource type(s) chosen for the validation context.

## AC-R0-STUDY-002

ARIA can conduct a study interaction grounded in the selected context/resources where grounding is required.

## AC-R0-STUDY-003

ARIA does not claim unavailable source material was retrieved.

## AC-R0-STUDY-004

The study system can receive an adaptation instruction derived from learner state and materially alter the subsequent study experience.

## AC-R0-STUDY-005

The system retains enough information to identify **what changed and why** between the baseline and adapted study experiences.

---

# 7. R0 Acceptance — Assessment & Evaluation

## AC-R0-ASSESS-001

The learner can take an assessment format supported by the selected R0 validation context.

## AC-R0-ASSESS-002

The assessment produces evidence attributable to the relevant concept/topic/context.

## AC-R0-EVAL-001

Deterministically scorable responses use deterministic scoring where appropriate.

## AC-R0-EVAL-002

AI-evaluated responses use bounded evaluation criteria and validated structured output where applicable.

## AC-R0-EVAL-003

Evaluation failure does not become false negative evidence.

## AC-R0-EVAL-004

A corrected evaluation can be reflected in dependent evidence/state when correction is supported.

---

# 8. R0 Acceptance — Evidence & Basic Learner State

## AC-R0-EVD-001

Supported evaluated activity creates structured evidence with provenance.

## AC-R0-EVD-002

One isolated wrong answer does not automatically become a confirmed misconception.

## AC-R0-EVD-003

One isolated correct answer does not automatically become mastery.

## AC-R0-EVD-004

Lack of evidence remains distinguishable from evidence of difficulty.

## AC-R0-LM-001

The system can derive/update a conservative concept-level state from supported evidence.

## AC-R0-LM-002

Learner-state changes are traceable to the evidence that caused them.

## AC-R0-LM-003

Contradictory/uncertain evidence does not silently become high-confidence state.

Full misconception diagnosis is not required for R0.

---

# 9. R0 Acceptance — Adaptation

## AC-R0-ADAPT-001

A supported learner-state change can alter the next study experience.

## AC-R0-ADAPT-002

The adaptation is relevant to the evidence/state that triggered it.

## AC-R0-ADAPT-003

The system can expose a testable reason for the adaptation.

## AC-R0-ADAPT-004

The adaptation does not silently modify unrelated learner contexts.

## AC-R0-ADAPT-005

When evidence is insufficient, ARIA can retain uncertainty rather than forcing an adaptation.

## AC-R0-ADAPT-006

A subsequent assessment can generate new evidence that confirms, weakens, or changes the previous learner-state estimate.

---

# 10. Gate A — Engineering Validation

Gate A is **mandatory and rigorous**.

Its question is:

> **Does the adaptive machinery correctly close the loop under controlled, reproducible scenarios?**

Gate A should include automated and/or controlled integration scenarios such as:

### Scenario A — Evidence causes targeted adaptation

```text
Known concept/context
    ↓
Controlled weak performance
    ↓
Expected evidence record
    ↓
Expected conservative learner-state change
    ↓
Expected targeted study adaptation
```

### Scenario B — Stronger evidence changes behaviour differently

A controlled supported-performance pattern should not produce the same remediation as the weak-performance scenario.

### Scenario C — Insufficient evidence

Weak/ambiguous evidence should not trigger an unsupported high-confidence conclusion.

### Scenario D — Evaluation failure

Failed evaluation should not create false negative evidence or downstream learner-state damage.

### Scenario E — Contradictory evidence

Contradictory results should affect state/confidence according to the defined evidence policy rather than being silently discarded.

### Scenario F — Context isolation

Evidence from one validation context should not incorrectly adapt an unrelated context.

### Scenario G — Repeated cycle

New evidence after an adapted study session can update the learner state again and influence the next action.

## Gate A completion condition

Gate A passes when all critical controlled scenarios have documented expected outcomes and pass reproducibly under the defined test environment, with no unresolved severity-critical defects in the adaptive loop.

Exact numeric AI-quality thresholds may be added once the selected models/evaluation datasets are known.

---

# 11. Gate B — Real-User Signal

Gate B is **small-scale product evidence**, not a controlled educational trial.

Its question is:

> **When target learners use the R0 loop, do the adaptations appear relevant and useful enough to justify continuing the product direction?**

Appropriate Gate B evidence can include:

- initial assessment → adaptation → targeted reassessment;
- before/after performance observations;
- repeated sessions where feasible;
- whether learners understood why ARIA adapted;
- whether the adapted explanation/activity felt relevant;
- whether ARIA adapted to the wrong thing;
- qualitative feedback;
- observed failure cases;
- whether learners would choose to continue the adapted flow.

## Gate B constraints

Gate B does **not** require:

- statistical significance;
- a large randomized sample;
- a formal control group;
- proof that ARIA caused the learner's improvement;
- publication-grade educational research.

A learner getting a later question correct after earlier mistakes is useful evidence, but by itself does not prove ARIA caused the improvement.

## Gate B reporting rule

Report observations honestly as directional signals.

A defensible conclusion is:

> **The adaptive pipeline was rigorously validated through controlled engineering scenarios. Small-scale real-user testing then provided directional before/after evidence and qualitative feedback, without claiming statistically established causal improvement.**

---

# 12. R0 Success Metrics

R0 metrics should be divided by what they actually measure.

## Engineering metrics

Examples:

- critical Gate A scenario pass rate;
- valid structured-evaluation rate;
- valid evidence-creation rate;
- correct learner-state transition rate on controlled fixtures;
- correct adaptation-selection rate on controlled fixtures;
- cross-context contamination incidents;
- unrecovered adaptive-workflow failures;
- duplicate consequential-state creation under retry tests.

## Product/user metrics

Examples suitable for small-scale directional reporting:

- number of users completing at least two learning cycles;
- proportion of adaptations users judge relevant/useful;
- proportion of adaptations users judge incorrect/confusing;
- before/after assessment observations;
- qualitative themes from learner feedback;
- number/type of learner corrections;
- whether users choose to continue after the first adapted cycle.

These should not be presented as population-level causal learning-effect estimates.

---

# 13. R0 Explicitly Deferred Acceptance Areas

R0 completion is not blocked by acceptance criteria for:

- Notes;
- Audio;
- Planner;
- notifications;
- full Roadmaps;
- roadmap adaptation;
- sophisticated Progress;
- mature Revision/spaced repetition;
- confirmed misconception detection;
- external learning integrations;
- production coding sandbox;
- advanced multi-agent orchestration;
- every assessment type;
- every resource type;
- broad domain generalization.

Those requirements remain available for later release acceptance.

---

# 14. Later-Release Acceptance Direction

## R1 — Learning-path adaptation

Acceptance should test whether evidence can lead to explainable, learner-reviewable changes to a structured learning path.

## R2 — Longitudinal learning

Acceptance should test evidence accumulation over time, revision prioritization, confidence handling, progress, and conservative misconception hypotheses.

## R3 — Learning coordination

Acceptance should test planning, missed-work recovery, deadlines, revision/new-learning prioritization, reminders, and multiple-goal coordination where supported.

## R4 — Learning interfaces

Acceptance should test Notes, Audio, richer resources/search, and whether these interfaces preserve shared learner context.

## R5 — Cross-system orchestration

Acceptance should test bounded automation, event reliability, human-in-the-loop controls, auditability, and advanced integrations/orchestration.

---

# 15. Open Questions for R0 Finalization

The following should be resolved before R0 implementation is considered specification-complete:

1. Which concrete learning context(s) will be used for Gate A fixtures and Gate B user testing?
2. Which resource type(s) are required for those contexts?
3. Which assessment format(s) give reliable evidence with manageable evaluation complexity?
4. What exact conservative learner-state representation will R0 use?
5. What adaptation actions are allowed in R0?
6. What evidence threshold is sufficient to trigger each adaptation?
7. What constitutes a critical Gate A failure?
8. How many real target users/sessions are realistically available for Gate B reporting?

These questions should be answered to make R0 executable; they should not expand into requirements to solve every domain or educational research question.

---

# 16. PRD Closure Status

The earlier PRD version treated the first product release as a broad feature loop and separated a foundation-only R0 from adaptive intelligence. The reviewed Phase 0 vision changes that release model.

The PRD is therefore **not yet frozen**.

Before canonical `PRD.md` is produced:

- remaining Phase 1 documents must be checked for assumptions that imply universal R0 domain support;
- full-vision requirements must be clearly distinguishable from R0 implementation requirements;
- R0 open questions above must be resolved;
- requirement traceability must be checked against the revised release boundaries.

Phase 1 remains **IN PROGRESS** until that consistency pass and final PRD consolidation are complete.