# ARIA — Phase 1 PRD

## Step 8 — Acceptance Criteria, Success Metrics & PRD Closure

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Reviewed and R0 decisions resolved  
**Primary sources:** `VISION.md`, Steps 1–7, `R0-DECISIONS.md`

---

# 1. Purpose

A release is not complete because its UI exists or its pipeline executes once. It is complete when the release hypothesis has been tested at the appropriate level.

For R0:

- **Gate A — Engineering Validation:** rigorous and reproducible;
- **Gate B — Real-User Signal:** small-scale and directional, without causal overclaiming.

---

# 2. R0 Hypothesis

> **ARIA can observe meaningful learning evidence, update a basic learner_concept_state, and use that state to appropriately change the learner's next study experience.**

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
 Basic learner_concept_state
          ↓
Adapt Next Study Experience
          ↓
Targeted Reassessment
          ↓
      New Evidence
          ↺
```

---

# 3. Frozen R0 Validation Context

R0 validates the loop in a **college-level DBMS context**, initially centered on Transactions, Concurrency Control, Schedules and Serializability.

This is a validation fixture, not a permanent hardcoded ARIA domain.

R0 supports **PDF upload and pasted text** as its required resource surface.

R0's required assessment format is **MCQ**, enabling deterministic evaluation. Short-answer evaluation is optional and cannot block R0 completion.

---

# 4. Core R0 User Journey

A learner completes at least two connected cycles:

```text
Create / enter DBMS validation context
        ↓
Upload PDF and/or paste text
        ↓
Study with ARIA
        ↓
Take configurable MCQ assessment
        ↓
Deterministic evaluation
        ↓
Concept-attributed evidence
        ↓
Basic learner_concept_state reconsidered
        ↓
ARIA adapts the next Study experience
        ↓
Learner studies again
        ↓
Targeted MCQ reassessment
        ↓
New evidence + state reconsideration
```

The second cycle is mandatory to validate the adaptive loop.

---

# 5. R0 Acceptance — Foundation

## AC-R0-FND-001
A learner can securely access their own validation workspace and persistent learning context.

## AC-R0-FND-002
Private learner-owned validation data cannot be accessed by another normal learner through predictable/copied identifiers.

## AC-R0-FND-003
The validation goal/context persists across repeated cycles.

## AC-R0-FND-004
Failures in later AI stages do not erase already persisted learner input, attempts or valid evidence.

---

# 6. R0 Acceptance — Resources & Study

## AC-R0-RES-001
The learner can upload a supported PDF and/or provide pasted text for the active validation context.

## AC-R0-RES-002
Resource processing exposes explicit ready/failed state and retains source/context association.

## AC-R0-STUDY-001
ARIA can conduct a study interaction grounded in selected resources where grounding is expected.

## AC-R0-STUDY-002
ARIA does not claim unavailable source material was retrieved.

## AC-R0-STUDY-003
Study can receive an adaptation instruction derived from learner_concept_state and materially alter the subsequent experience.

## AC-R0-STUDY-004
The system retains enough information to identify what changed and why between baseline and adapted Study.

---

# 7. R0 Acceptance — Assessment & Evaluation

## AC-R0-ASSESS-001
The learner can take an MCQ assessment scoped to the selected DBMS concept/context.

## AC-R0-ASSESS-002
Within supported limits, the learner can configure question count, concept/topic scope, difficulty and optional time limit.

## AC-R0-ASSESS-003
Targeted MCQ reassessment can be generated/conducted after adaptation.

## AC-R0-EVAL-001
Required R0 MCQs are scored deterministically.

## AC-R0-EVAL-002
Evaluation produces concept-attributed results with provenance to the attempt/question/context.

## AC-R0-EVAL-003
Evaluation failure does not become false negative learning evidence.

## AC-R0-EVAL-004
A corrected evaluation can propagate into dependent evidence/state/adaptation.

Optional short-answer AI evaluation, if implemented, must use bounded criteria and validated structured output.

---

# 8. R0 Acceptance — Evidence & Basic learner_concept_state

R0 states are:

```text
UNTESTED
DEVELOPING
NEEDS_REVIEW
SUPPORTED
```

## AC-R0-EVD-001
Each usable evaluated MCQ creates structured concept-attributed evidence with provenance.

## AC-R0-EVD-002
One isolated wrong answer does not establish `NEEDS_REVIEW` or a confirmed misconception.

## AC-R0-EVD-003
One isolated correct answer does not establish `SUPPORTED` or mastery.

## AC-R0-EVD-004
No evidence remains distinguishable from evidence of difficulty.

## AC-R0-LM-001
No sufficient evidence maps to `UNTESTED`.

## AC-R0-LM-002
One usable observation normally maps to `DEVELOPING` rather than a strong conclusion.

## AC-R0-LM-003
At least two aligned weak evidence points across distinct questions/opportunities are normally required before `NEEDS_REVIEW` and strong remediation.

## AC-R0-LM-004
At least two aligned correct evidence points across distinct opportunities are normally required before `SUPPORTED`, including an independent/later question or reassessment opportunity.

## AC-R0-LM-005
Mixed/contradictory evidence remains conservative, normally `DEVELOPING` or a lower-confidence retained prior state.

## AC-R0-LM-006
State changes retain evidence references, confidence, time and reason/rule.

`SUPPORTED` means current evidence supports understanding in the R0 context; it is not permanent mastery.

---

# 9. R0 Acceptance — Adaptation

Allowed R0 adaptations include:

- prioritize the weak/uncertain concept;
- change explanation strategy;
- add a relevant worked example;
- recap a prerequisite when justified;
- increase/decrease scaffolding;
- provide targeted practice/check questions;
- reduce unnecessary repetition for supported concepts;
- request more evidence instead of forcing a strong adaptation.

## AC-R0-ADAPT-001
A supported learner-state change can alter the next Study experience.

## AC-R0-ADAPT-002
The adaptation is relevant to the evidence/state that triggered it.

## AC-R0-ADAPT-003
The system exposes a testable reason and provenance for the adaptation.

## AC-R0-ADAPT-004
Adaptation does not silently modify unrelated contexts.

## AC-R0-ADAPT-005
Insufficient evidence may retain uncertainty instead of forcing remediation/support conclusions.

## AC-R0-ADAPT-006
A subsequent assessment creates new evidence capable of confirming, weakening or changing the prior state.

---

# 10. Gate A — Engineering Validation

Gate A asks:

> **Does the adaptive machinery correctly close the loop under controlled, reproducible scenarios?**

Required scenarios include:

### A — Weak evidence causes targeted adaptation
Controlled repeated weak performance → expected evidence → expected conservative state → targeted remediation.

### B — Supported evidence produces different behaviour
Repeated supported performance must not produce the same remediation as the weak case.

### C — Insufficient evidence
One/ambiguous observation must not trigger unsupported high-confidence conclusions.

### D — Evaluation failure
Failure creates no false negative evidence or downstream learner-state damage.

### E — Contradictory evidence
Contradictory results reduce/retain uncertainty according to policy rather than being discarded.

### F — Context isolation
Evidence from one context cannot incorrectly adapt another context.

### G — Correction propagation
Correcting a source evaluation/evidence record recomputes or invalidates dependent state/adaptation as required.

### H — Retry/idempotency
Retrying a consequential operation cannot create duplicate evidence/state/adaptation.

### I — Downstream AI failure
A downstream generation/provider failure cannot erase already persisted valid attempts/evidence.

### J — Repeated adaptive cycle
Adapted Study → targeted reassessment → new evidence → learner-state reconsideration works end to end.

### K — Cross-user isolation/security
One learner cannot retrieve or mutate another learner's private R0 data.

## Gate A critical failure

Any required-scenario failure involving authorization/privacy, evidence attribution/integrity, false evidence, incorrect controlled state transition, unrelated adaptation, correction failure, duplicate consequential state, lost valid state, inability to close the second cycle, or unsafe secrets/security is critical.

## Gate A completion

All required critical scenarios must pass reproducibly with **zero unresolved critical failures**.

---

# 11. Gate B — Real-User Signal

Gate B asks:

> **When target learners use the R0 loop, do the adaptations appear relevant and useful enough to justify continuing the product direction?**

Target:

- 5–10 target learners where realistically available;
- at least two connected learning cycles per participant where feasible;
- aim for 10+ completed adaptive cycles total;
- report actual participation and completion counts honestly.

Collect:

- baseline assessment observations;
- adaptation shown;
- targeted reassessment observations;
- adaptation relevance/usefulness;
- whether the learner understood why ARIA adapted;
- incorrect/confusing adaptations;
- learner corrections;
- qualitative feedback;
- willingness to continue the adaptive flow.

If fewer than five usable participants are available, report Gate B as a pilot and state the limitation.

Gate B does not require statistical significance, a control group or causal proof of learning improvement.

Defensible conclusion:

> **The adaptive pipeline was rigorously validated through controlled engineering scenarios. Small-scale real-user testing then provided directional before/after evidence and qualitative feedback, without claiming statistically established causal improvement.**

---

# 12. R0 Success Metrics

## Engineering

- critical Gate A scenario pass rate;
- deterministic evaluation correctness on controlled fixtures;
- valid evidence-creation rate;
- correct learner-state transition rate on fixtures;
- correct adaptation-selection rate on fixtures;
- cross-user/context contamination incidents;
- unrecovered adaptive-workflow failures;
- duplicate consequential-state creation under retries;
- correction/recomputation correctness.

## Product / user signal

- number of participants completing at least two cycles;
- total completed adaptive cycles;
- relevant/useful adaptation judgments;
- incorrect/confusing adaptation judgments;
- before/after assessment observations;
- qualitative themes;
- learner corrections;
- willingness to continue.

These are directional R0 measures, not population-level causal learning-effect estimates.

---

# 13. Explicitly Deferred R0 Acceptance Areas

R0 completion is not blocked by acceptance criteria for:

- Notes;
- Audio;
- Planner;
- notifications;
- full Roadmaps/roadmap adaptation;
- sophisticated Progress;
- mature Revision/spaced repetition;
- confirmed/full misconception detection;
- external learning integrations;
- production coding sandbox;
- advanced multi-agent orchestration;
- every assessment type;
- every resource type;
- multiple simultaneous goals;
- broad domain generalization.

---

# 14. Later-Release Acceptance Direction

## R1 — Learning-path adaptation
Test explainable, learner-reviewable evidence-driven changes to a structured learning path.

## R2 — Longitudinal learning
Test evidence accumulation, revision prioritization, confidence, progress, richer learner_concept_state and conservative misconception hypotheses.

## R3 — Learning coordination
Test planning, missed-work recovery, deadlines, revision/new-learning prioritization, reminders and multi-goal coordination.

## R4 — Learning interfaces
Test Notes, Audio, richer resources/search and preservation of shared learner context.

## R5 — Cross-system orchestration
Test bounded automation, event/workflow reliability, human controls, auditability and justified integrations/agentic orchestration.

---

# 15. R0 Decision Closure

The eight previously open R0 decisions are resolved in `R0-DECISIONS.md`:

1. validation context — DBMS / Transactions, Concurrency, Schedules, Serializability;
2. resources — PDF + pasted text;
3. required assessment — MCQ; short answer optional;
4. learner_concept_state — `UNTESTED`, `DEVELOPING`, `NEEDS_REVIEW`, `SUPPORTED`;
5. adaptation actions — bounded Study adaptations defined above;
6. evidence thresholds — conservative two-aligned-evidence default for strong state conclusions;
7. Gate A critical failures — explicitly defined;
8. Gate B — 5–10 target learners where feasible, two cycles each, 10+ total adaptive cycles target.

These are R0 implementation/validation choices, not permanent limits on ARIA's complete vision.

---

# 16. PRD Closure Status

The Step 1–8 consistency audit is complete and the R0 product decisions are resolved.

The remaining mechanical closure work is:

- final requirement traceability check;
- consolidate the reviewed Phase 1 specification into canonical `PRD.md`;
- mark Phase 1 frozen.

No unresolved product-scope question currently blocks that closure.

**Step 8: COMPLETE.**
---

## Next

Step 9.
