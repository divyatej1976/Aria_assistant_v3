# ARIA — Phase 1 PRD

## Step 5 — AI, Learner Model, Memory & Evidence Requirements

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Reviewed and release-classified  
**Primary sources:** `VISION.md`, Steps 1–4 and 7–8

---

# 1. Purpose

This document defines ARIA's intelligence requirements without choosing an LLM provider, agent framework, vector database, memory library, orchestration framework, or final learner-model algorithm.

For R0, the intelligence problem is deliberately narrow:

```text
reliable learning observation
        ↓
structured evidence
        ↓
basic evidence-backed learner_concept_state
        ↓
confidence-aware adaptation decision
        ↓
adapted Study
        ↓
reassessment
        ↓
new evidence
```

The central principle remains:

> **ARIA must know the difference between remembering something about a learner and having evidence that the learner understands something.**

R0 does not need a complete lifelong learner model, autonomous multi-agent tutor, full misconception engine, long-term memory system, prerequisite graph, or mastery-science platform to test this hypothesis.

---

# 2. Release Labels

- **R0 MUST** — required to close and validate the first adaptive-learning loop.
- **R0 SHOULD** — useful for a credible R0 but may be simplified.
- **R1+** — learning-path/Roadmap intelligence.
- **R2+** — longitudinal Learner Model, Revision, forgetting, misconception/prerequisite reasoning.
- **R3+** — multi-goal coordination and planning intelligence.
- **R4+** — richer interfaces/modalities.
- **R5+** — mature orchestration/integrations/agentic intelligence.
- **LONG-TERM MUST** — invariant whose implementation release may vary.

---

# 3. Intelligence Layers

ARIA conceptually separates:

```text
Current Context ───────────────┐
                               │
Persistent Memory (later) ─────┼──→ AI / deterministic reasoning
                               │              │
Structured Evidence ───────────┘              │
       │                                      │
       ↓                                      │
Basic learner_concept_state (R0) ─────────────────────┘
                                              ↓
                                      Learning Action
```

These are not interchangeable:

- **Context** = what is relevant now.
- **Memory** = durable useful information about the learner/environment.
- **Evidence** = observations of learning performance.
- **learner_concept_state** = conclusions derived from evidence.
- **Adaptation** = action chosen using context + learner_concept_state + product rules.

---

# 4. Requirement Categories

```text
AI-BEH-*      General AI behaviour
AI-CTX-*      Context management
AI-TOOL-*     Tool use
AI-MEM-*      Memory
AI-EVD-*      Evidence
AI-LM-*       Learner Model
AI-STATE-*    R0 learner_concept_state
AI-MIS-*      Misconceptions
AI-PREQ-*     Prerequisite gaps
AI-CONF-*     Confidence / uncertainty
AI-ADAPT-*    Adaptation reasoning
AI-VAL-*      Validation
AI-CORR-*     Correction
AI-FAIL-*     Failure behaviour
AI-AGENT-*    Agent boundaries
```

---

# 5. General AI Behaviour

## AI-BEH-001 — Learning-purpose alignment — R0 MUST
AI behaviour shall serve the active learning context rather than optimize for conversation alone.

## AI-BEH-002 — Context-sensitive output — R0 MUST
ARIA shall use relevant current context without injecting unrelated history.

## AI-BEH-003 — No false certainty — R0 MUST
Uncertain conclusions shall not be presented as established learner facts.

## AI-BEH-004 — Generation is not knowledge state — R0 MUST
Explaining a concept does not prove learner understanding.

## AI-BEH-005 — Exposure is not mastery — R0 MUST
Reading, viewing or discussing material does not itself establish mastery.

## AI-BEH-006 — Product rules outrank model improvisation — R0 MUST
Authorization, schemas, state-transition rules, evidence rules and learner control outrank free-form model decisions.

## AI-BEH-007 — Explicit learner instruction precedence — R0 MUST
Current explicit learner instructions normally override conflicting inferred preferences/assumptions.

## AI-BEH-008 — Appropriate teaching action — R0 MUST
Within supported R0 capabilities, ARIA should choose among explanation, example, hint, diagnostic question and targeted practice based on the adaptation need rather than always generating the same response type.

## AI-BEH-009 — Appropriate complexity — R0 SHOULD
## AI-BEH-010 — Specific feedback over empty praise — R0 SHOULD
## AI-BEH-011 — Correct incorrect assumptions — R0 MUST
## AI-BEH-012 — State limitations — R0 MUST
ARIA shall not invent missing information, evidence or tool results.

---

# 6. R0 Context Management

## AI-CTX-001 — Working context — R0 MUST
R0 shall maintain only the context needed for its current loop, potentially including:

```text
active validation goal/context
active topic/concept
selected resource(s)
current Study activity
assessment specification
current attempt
relevant evidence
relevant basic learner_concept_state
current adaptation
```

## AI-CTX-002 — Relevant retrieval — R0 SHOULD
Only relevant prior R0 context/evidence should be retrieved for a task.

## AI-CTX-003 — Scope — R0 MUST
Context-specific information shall not silently become global learner information.

## AI-CTX-004 — Temporary context — R0 MUST
Temporary instructions shall remain temporary unless explicitly persisted later.

## AI-CTX-005 — Explicit correction — R0 MUST
Subsequent reasoning shall use corrected context.

## AI-CTX-006 — Provenance — R0 MUST WHERE CONSEQUENTIAL
ARIA should distinguish explicitly supplied, inherited/retrieved and inferred context.

## AI-CTX-007 — Conflict — R0 MUST
Current explicit information normally outranks conflicting historical/inferred information.

## AI-CTX-008 — Context minimization — R0 SHOULD
Use only task-relevant context where practical for privacy, latency, cost and reliability.

---

# 7. Tool Use

## AI-TOOL-001 — Tool necessity — R0 MUST
Use deterministic tools/services when information or execution should not be fabricated by an LLM.

## AI-TOOL-002 — Authorization — R0 MUST
AI components may invoke only actions permitted by the workflow and learner permissions.

## AI-TOOL-003 — Input validation — R0 MUST
Consequential tool inputs shall be schema/constraint validated.

## AI-TOOL-004 — Output grounding — R0 MUST
Authoritative tool results shall ground downstream reasoning.

## AI-TOOL-005 — Failure distinction — R0 MUST
## AI-TOOL-006 — No fabricated execution — R0 MUST
## AI-TOOL-007 — Least authority — LONG-TERM MUST
## AI-TOOL-008 — High-impact confirmation — LONG-TERM MUST

R0 tool needs should remain minimal: resource processing/retrieval, assessment execution/evaluation where applicable, and deterministic validation/state operations.

---

# 8. Memory — Explicitly Not Required for the Core R0 Hypothesis

A sophisticated persistent conversational memory system is **not required** to prove R0 adaptive learning.

R0 may persist ordinary product state required for continuity (account, context, resources, attempts, evidence, learner_concept_state). That persistence must not be confused with a generalized AI memory subsystem.

## AI-MEM-001 — Memory is not Learner Model — LONG-TERM MUST
Memory may eventually store preferences, useful facts, prior decisions and recurring constraints; it shall not create mastery claims by itself.

## AI-MEM-002 — Explicit vs inferred — R2+
## AI-MEM-003 — Scoped memory — R2+
## AI-MEM-004 — Temporary exclusion — R2+
## AI-MEM-005 — Selective persistence — R2+
## AI-MEM-006 — Relevant retrieval — R2+
## AI-MEM-007 — Correction — R2+
## AI-MEM-008 — Deletion/control — R2+
## AI-MEM-009 — Uncertainty — R2+
## AI-MEM-010 — Provenance — R2+

Later memory may influence **how ARIA interacts**; evidence-backed learner_concept_state determines **what ARIA has grounds to believe about learning performance**.

---

# 9. R0 Evidence Model

Evidence is an observation about learner performance under known conditions. It is not merely activity telemetry.

## AI-EVD-001 — Structured evidence — R0 MUST
Supported R0 assessment/evaluation observations shall become structured evidence.

## AI-EVD-002 — Provenance — R0 MUST
Each evidence record shall link to the source attempt/response/evaluation.

## AI-EVD-003 — Concept association — R0 MUST
Evidence shall identify the concept/skill/learning objective it is intended to measure.

## AI-EVD-004 — Context association — R0 MUST
Evidence shall preserve the relevant validation/goal context.

## AI-EVD-005 — Timestamp/order — R0 MUST
Evidence shall retain when it occurred and enough ordering information for before/after cycles.

## AI-EVD-006 — Evidence type — R0 MUST
ARIA shall distinguish supported evidence forms rather than treating all observations identically.

## AI-EVD-007 — Observed outcome — R0 MUST
Evidence records what happened, not merely that an activity was opened/completed.

## AI-EVD-008 — Reliability/strength metadata — R0 MUST
Evidence shall support factors that affect how strongly it should influence state.

## AI-EVD-009 — Conditions — R0 MUST WHERE APPLICABLE
Relevant difficulty, assistance/hints, evaluation confidence and comparable conditions should be preserved.

## AI-EVD-010 — Independent attempts — R0 MUST
Independent attempts shall be distinguishable from repeated exposure to the same answer/problem.

## AI-EVD-011 — Assisted success — R0 MUST WHERE SUPPORTED
A correct answer after answer-revealing assistance shall not automatically equal an independent correct answer.

## AI-EVD-012 — Negative evidence — R0 MUST
Incorrect/incomplete performance may indicate difficulty but does not by itself prove a misconception.

## AI-EVD-013 — Historical preservation — R0 MUST
New evidence shall not overwrite prior attempts needed for validation.

## AI-EVD-014 — Correctability — R0 MUST
Evidence derived from an incorrect evaluation shall be revisable/invalidatable.

## AI-EVD-015 — Evidence validity — R0 MUST
Invalid, failed or unevaluated attempts shall not silently become learner-performance evidence.

---

# 10. What R0 learner_concept_state Actually Needs

R0 should **not** begin with a rich seven-state mastery ontology simply because the long-term product may need one.

The minimum state needed to test adaptation is concept-level, evidence-linked and uncertainty-aware.

A valid implementation may use labels, probabilities, scores or another representation, but it must semantically distinguish at least:

```text
INSUFFICIENT_EVIDENCE
        │
        ├── evidence suggests DIFFICULTY
        │
        └── evidence suggests COMPETENCE
```

Optional neutral/mixed representation may be used where useful.

This is deliberately **not** equivalent to permanent `WEAK`, `STRONG`, or `MASTERED` declarations.

## AI-STATE-001 — Insufficient evidence — R0 MUST
ARIA shall distinguish lack of evidence from poor performance.

## AI-STATE-002 — Difficulty signal — R0 MUST
ARIA shall be able to represent that current evidence supports targeted help/practice.

## AI-STATE-003 — Competence signal — R0 MUST
ARIA shall be able to represent that current evidence supports reducing unnecessary remediation or selecting a more appropriate next action.

## AI-STATE-004 — Uncertainty — R0 MUST
Each consequential state shall support confidence/uncertainty.

## AI-STATE-005 — Evidence links — R0 MUST
State shall link to supporting evidence.

## AI-STATE-006 — Revisability — R0 MUST
State shall change when new/corrected evidence warrants it.

## AI-STATE-007 — Concept granularity — R0 MUST
State shall exist at a useful concept/skill level rather than only one overall learner score.

## AI-STATE-008 — No permanent mastery inference — R0 MUST
R0 shall not claim durable mastery from the evidence needed merely to run a short adaptive validation cycle.

---

# 11. Rich Learner Model — R2+

The long-term Learner Model may include:

```text
learner_concept_state
confidence
supporting evidence
recency
change history
mastery/review state
possible misconceptions
prerequisite gaps
revision state
cross-session trends
```

Preserved requirements for R2+:

- evidence-backed state rather than conversation memory;
- concept/skill granularity;
- confidence and provenance;
- contradictory evidence handling;
- recency and forgetting;
- transferable state across goals only when concept equivalence is justified;
- no unsupported psychological/personality diagnosis;
- stronger thresholds for durable mastery than for short-term competence signals;
- review/decay when old evidence no longer supports a current claim.

---

# 12. Misconception Detection — R2+ by Default

A misconception is a systematic incorrect mental model, not simply a wrong answer.

Full misconception detection is **not required for R0 completion**.

Later requirements remain:

- candidate/suspected misconception state;
- single-error protection;
- repeated-pattern evidence;
- targeted diagnostic questions;
- suspected vs sufficiently supported distinction;
- targeted remediation;
- retest before resolution;
- uncertainty-aware learner-facing language;
- resolution history.

R0 may use a diagnostic question because a learner shows difficulty, but it should not market that as a mature misconception-detection engine.

---

# 13. Prerequisite-Gap Reasoning — R2+ by Default

The mature product should distinguish difficulty in concept B from difficulty caused by missing prerequisite A.

Later requirements remain:

- dependency awareness;
- prerequisite-gap hypotheses;
- diagnostic validation;
- no automatic certainty from a dependency edge;
- remediation recommendation;
- Roadmap impact under R1/R2 rules;
- dependent-concept retesting.

R0 may target a known prerequisite as a bounded Study adaptation if its validation content supplies that relationship, but generalized prerequisite inference is not an R0 requirement.

---

# 14. Confidence & Uncertainty

Confidence is required in R0, but R0 does **not** need fake scientific precision.

## AI-CONF-001 — Representation — R0 MUST
Consequential learner-state conclusions shall represent uncertainty/confidence.

## AI-CONF-002 — Evidence confidence, not LLM confidence — R0 MUST
Confidence shall derive from evidence quality/consistency and evaluation reliability, not how certain model prose sounds.

## AI-CONF-003 — Quantity — R0 MUST
Multiple relevant independent observations may strengthen a conclusion.

## AI-CONF-004 — Quality — R0 MUST
Higher-quality evidence may contribute more strongly than weak evidence.

## AI-CONF-005 — Contradiction — R0 MUST
Contradictory evidence shall reduce certainty or motivate diagnostic/reassessment behaviour.

## AI-CONF-006 — Assistance level — R0 MUST WHERE APPLICABLE
Highly assisted performance shall not create unsupported independent-competence confidence.

## AI-CONF-007 — Action threshold — R0 MUST
Higher-impact conclusions/actions require stronger support than low-risk diagnostic actions.

## AI-CONF-008 — Learner-facing uncertainty — R0 SHOULD
When uncertainty materially affects an adaptation, ARIA should communicate it understandably.

## AI-CONF-009 — Recency/forgetting — R2+
Longitudinal decay/forgetting models are later scope.

---

# 15. Evidence Weighting — Product Behaviour, Not Final Formula

R0 requires the *behaviour* of weighting evidence, not a research-grade knowledge-tracing algorithm.

A future implementation might consider:

```text
Evidence influence ≈
    evaluation reliability
  × relevance to concept
  × independence
  × difficulty relevance
  × assistance factor
```

R2+ may add recency/forgetting and richer longitudinal factors.

Examples:

```text
Independent correct answer on a relevant unseen problem
→ stronger competence evidence

Correct after answer-revealing hint
→ weaker independent-competence evidence

Reading an explanation
→ exposure/context, not mastery evidence

One wrong answer
→ difficulty signal at most; not confirmed misconception
```

ARIA shall not show learners fake precision merely because internal implementation uses numeric values.

---

# 16. R0 Adaptation Reasoning

## AI-ADAPT-001 — Evidence/state grounded — R0 MUST
An adapted Study action shall be selected using relevant current learner_concept_state and its evidence.

## AI-ADAPT-002 — Real causal software trace — R0 MUST
ARIA shall preserve enough decision metadata to demonstrate that the recorded learner-state signal actually influenced the selected adaptation.

## AI-ADAPT-003 — Supported action set — R0 MUST
R0 adaptation shall choose from supported bounded actions such as:

```text
simpler/deeper explanation
worked example
additional scaffold
hint-first practice
targeted concept practice
diagnostic question
known prerequisite refresh
reduced redundant remediation when evidence supports competence
```

## AI-ADAPT-004 — Material difference — R0 MUST
When adaptation is triggered, the resulting Study action shall not be merely a cosmetically reworded generic response if the evidence calls for a substantive change.

## AI-ADAPT-005 — Uncertainty behaviour — R0 MUST
Uncertain state should favour diagnostic or low-risk adaptation rather than strong unsupported conclusions.

## AI-ADAPT-006 — Explanation — R0 MUST
ARIA shall be capable of producing a learner/tester-readable reason grounded in the actual decision factors.

## AI-ADAPT-007 — No causal learning overclaim — R0 MUST
ARIA may record that evidence caused a software adaptation decision. It shall not infer from a subsequent improvement alone that the adaptation caused human learning improvement.

---

# 17. Generate → Validate → Fix

Important structured AI outputs shall not be trusted solely because generation succeeded.

```text
Generate
   ↓
Validate
   ↓
Valid? ── Yes → Use
   │
   No
   ↓
Repair / regenerate
   ↓
Validate again
   ↓
bounded stop
```

## AI-VAL-001 — Schema validation — R0 MUST
Consequential structured AI output shall satisfy required schema/constraints before downstream use.

## AI-VAL-002 — Assessment validation — R0 MUST
Generated assessments shall be checked against the learner-selected/supported specification where applicable, including relevant question count/format, answer/rubric availability, topic/source relevance and scoring consistency.

## AI-VAL-003 — Evidence extraction validation — R0 MUST
AI-derived evidence shall be validated sufficiently for the impact it may have on learner_concept_state.

## AI-VAL-004 — Adaptation validation — R0 MUST
An adaptation shall be checked for context relevance, supported action type and traceable reason before it becomes the R0 next Study action.

## AI-VAL-005 — Repair — R0 MUST WHERE SAFE
## AI-VAL-006 — Bounded retry — R0 MUST
## AI-VAL-007 — Graceful failure — R0 MUST
Invalid structured output shall not be forwarded into consequential state after retries are exhausted.

## AI-VAL-008 — Roadmap validation — R1+
## AI-VAL-009 — Planner validation — R3+

---

# 18. Task Decomposition

## AI-BEH-013 — Decompose when useful — R0 SHOULD
Complex R0 tasks may be separated into bounded stages when doing so improves reliability.

Example:

```text
Create assessment
      ↓
interpret specification
      ↓
retrieve relevant source/context
      ↓
generate questions
      ↓
generate/verify answers or rubric
      ↓
validate
      ↓
deliver
```

## AI-BEH-014 — Do not over-decompose — R0 MUST
Simple deterministic actions shall not become unnecessary agent workflows.

## AI-BEH-015 — Clear responsibility — LONG-TERM MUST
AI responsibilities shall have explicit inputs, outputs, permissions and failure behaviour.

---

# 19. Agent Architecture Boundaries

R0 does not require multiple agents. The PRD intentionally does not decide agent count.

## AI-AGENT-001 — Agents are implementation choices — R0 MUST
A feature does not automatically imply a dedicated agent.

## AI-AGENT-002 — Deterministic-first — R0 MUST
Rules, authorization, schema validation, calculations and deterministic state transitions should use deterministic code where probabilistic reasoning adds no value.

## AI-AGENT-003 — Specialized reasoning when justified — LONG-TERM
## AI-AGENT-004 — Orchestrator authority limits — LONG-TERM MUST
## AI-AGENT-005 — Controlled shared-state updates — R0 MUST
No AI component may independently overwrite consequential learner_concept_state outside the controlled update mechanism.

## AI-AGENT-006 — Structured communication — R0 MUST WHERE MULTIPLE COMPONENTS EXIST
## AI-AGENT-007 — Bounded loops — R0 MUST
## AI-AGENT-008 — Observability — R0 MUST
Consequential workflows shall expose enough trace information for debugging/Gate A without exposing private internal chain-of-thought.

---

# 20. Correction

## AI-CORR-001 — Context correction — R0 MUST
## AI-CORR-002 — Evaluation correction/review — R0 MUST
## AI-CORR-003 — Learner-state challenge — R0 MUST
A learner/tester may challenge an inaccurate state conclusion. A self-assertion need not overwrite strong contrary evidence; ARIA may instead recompute or reassess.

## AI-CORR-004 — Downstream recomputation — R0 MUST
Corrected source evaluation/evidence shall allow dependent state/adaptation to be revised or invalidated.

## AI-CORR-005 — Audit history — R0 MUST
Enough history shall remain to understand why derived state changed.

## AI-CORR-006 — Persistent-memory correction — R2+

---

# 21. AI Failure Behaviour

## AI-FAIL-001 — No silent fabrication — R0 MUST
## AI-FAIL-002 — Preserve valid partial completion — R0 MUST
## AI-FAIL-003 — Distinguish reasoning/tool failure — R0 MUST WHERE USEFUL
## AI-FAIL-004 — Bounded retry — R0 MUST
## AI-FAIL-005 — Invalid output cannot become consequential state — R0 MUST
## AI-FAIL-006 — Reliable fallback — R0 SHOULD
Where practical, provide a lower-intelligence reliable path instead of making unaffected functionality unusable.

## AI-FAIL-007 — Preserve learner work — R0 MUST
AI failure shall not discard submitted answers, uploaded resources or completed valid work.

## AI-FAIL-008 — No endless retry — R0 MUST
## AI-FAIL-009 — Actionable failure explanation — R0 SHOULD
## AI-FAIL-010 — Failed evaluation is not negative evidence — R0 MUST

---

# 22. Memory vs learner_concept_state — Explicit Separation

| Memory / learner-provided context | Evidence-backed learner_concept_state |
|---|---|
| "I prefer examples before formulas" | "Current evidence suggests difficulty with Bayes' theorem" |
| "I'm preparing for GATE" | "Current attempts support competence on process scheduling" |
| "I think I'm good at DBMS" | "Evidence is insufficient to conclude competence across DBMS" |
| "Give me hints before solutions" | "Independent performance on this concept is not yet established" |

Memory/context can influence **how ARIA interacts**.

learner_concept_state influences **what ARIA has evidence to believe about performance and which bounded learning action may be useful next**.

Neither silently substitutes for the other.

---

# 23. Example — One Wrong Answer

```text
Question answered incorrectly
        ↓
Was evaluation valid/reliable?
        ↓
Valid difficulty evidence recorded
        ↓
What concept did it measure?
Was assistance involved?
Is there other evidence?
        ↓
Basic learner_concept_state updated conservatively
        ↓
Do NOT declare mastery failure or misconception
        ↓
Possible low-risk adaptation:
explanation / example / diagnostic question
```

R0 must be useful without pretending one observation reveals the learner's entire mental model.

---

# 24. Example — Evidence-Grounded Adaptation

```text
Attempt A:
learner misses two independent
serializability questions
        ↓
Evaluation valid
        ↓
Evidence linked to
"conflict serializability"
        ↓
Basic state:
evidence suggests difficulty
(confidence: sufficient for low-risk adaptation)
        ↓
ARIA chooses:
worked serializability example
+ targeted practice
        ↓
Decision record says WHY:
selected because of attempt A evidence
        ↓
Attempt B tests serializability again
        ↓
new evidence stored independently
        ↓
state reconsidered
```

This is the core R0 intelligence thesis.

---

# 25. Example — Learner Claim Without Evidence

Learner says:

> "I'm really good at DBMS."

ARIA may use that statement as learner-provided context. It shall **not** mark DBMS concepts as mastered. Performance evidence remains separate.

---

# 26. Example — Contradictory Evidence

```text
Attempt A → difficulty
Attempt B → strong independent result
Attempt C → mixed result
        ↓
Do not discard inconvenient evidence
        ↓
confidence remains mixed/uncertain
        ↓
prefer targeted diagnostic/reassessment
rather than a strong permanent label
```

---

# 27. Example — Incorrect Evaluation

```text
AI evaluator marks correct answer wrong
        ↓
negative evidence created
        ↓
learner/test detects evaluation error
        ↓
evaluation corrected
        ↓
dependent evidence revised/invalidated
        ↓
basic learner_concept_state recomputed
        ↓
stale adaptation invalidated/recomputed
```

ARIA's intelligence must be correctable all the way downstream.

---

# 28. Gate A Intelligence Validation Requirements

R0 is not complete merely because an LLM can generate explanations and quizzes.

Gate A shall include controlled scenarios demonstrating at least:

1. **difficulty path** — valid negative evidence changes learner_concept_state and produces a relevant bounded adaptation;
2. **competence path** — sufficiently strong evidence does not trigger unnecessary remediation;
3. **insufficient-evidence path** — absence of evidence does not become weakness;
4. **contradictory-evidence path** — conflicting observations reduce certainty/trigger further testing;
5. **correction path** — corrected evaluation changes dependent evidence/state/adaptation;
6. **retry/idempotency path** — repeated processing does not duplicate consequential evidence/state;
7. **failure path** — AI/tool failure does not fabricate evidence or destroy learner work;
8. **traceability path** — the tester can show which evidence caused which state and which adaptation;
9. **second-cycle path** — reassessment creates new evidence and the state is reconsidered.

These scenarios test engineering behaviour. They do not establish causal human-learning efficacy.

---

# 29. Intelligence Safety Invariants

1. **Memory is not mastery.**
2. **Exposure is not understanding.**
3. **One error is not automatically a misconception.**
4. **One success is not durable mastery.**
5. **No evidence is not weakness.**
6. **LLM confidence is not evidence confidence.**
7. **AI output is not valid merely because it is fluent.**
8. **Consequential structured output is validated.**
9. **Uncertain upstream conclusions remain uncertain downstream.**
10. **Evidence remains separate from derived learner_concept_state.**
11. **learner_concept_state remains separate from conversational memory/context.**
12. **R0 adaptation is bounded and evidence-grounded.**
13. **Correction propagates through dependent derived state.**
14. **Deterministic logic is not replaced by agents without reason.**
15. **AI/tool loops are bounded.**
16. **Learner work survives AI failures.**
17. **A software adaptation trace is not proof of causal learning improvement.**
18. **R0 does not claim a richer intelligence capability than it actually validates.**

---

# 30. Step 5 Decisions

The R0 intelligence stack is now deliberately small:

```text
Current learning context
        +
Structured performance evidence
        ↓
Basic concept-level learner_concept_state
        +
Uncertainty
        ↓
Bounded adaptation decision
        ↓
Adapted Study
        ↓
Reassessment
        ↓
New evidence / state reconsideration
```

The following remain part of ARIA's vision but are not required to prove R0:

```text
rich persistent conversational memory
full mastery ontology
longitudinal forgetting model
mature misconception detection
mature prerequisite-gap inference
revision intelligence
roadmap adaptation intelligence
planner intelligence
multi-goal coordination
large autonomous agent architecture
```

This preserves the long-term Learning OS while preventing R0 from becoming an AI research programme before its smallest adaptive hypothesis is tested.

---

# 31. Step 5 Completion

**Step 5 — AI, Learner Model, Memory & Evidence Requirements has been audited and realigned.**

The key correction is not removing ARIA's intelligence ambitions. It is separating:

> **the minimum intelligence needed to prove evidence-driven adaptation now**

from:

> **the richer intelligence ARIA can earn through later validated releases.**

Next:

# Step 6 — Non-Functional, Privacy, Security, Reliability & Accessibility Requirements Audit

Step 6 will identify which reliability/security/privacy/performance requirements are true R0 blockers, which need measurable thresholds now, and which scalability/production requirements should remain later-release targets rather than making a solo-capstone R0 pretend to be an internet-scale production platform.
---

## Next

Step 6 — Non-Functional, Privacy, Security, Reliability & Accessibility Requirements.
