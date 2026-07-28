# ARIA — Phase 1 PRD

## Step 5 — AI, Learner Model, Memory & Evidence Requirements

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 1 — Product Requirements Document  
**Status:** Step 5 — Complete  
**Primary sources:** `VISION.md`, Steps 1–4 of the Phase 1 PRD

---

# 1. Purpose

This document defines ARIA's intelligence requirements before choosing any particular LLM provider, agent framework, vector database, memory library, orchestration framework, or model architecture.

It specifies how ARIA should reason about:

- AI-generated learning interactions;
- context;
- tools;
- memory;
- evidence;
- learner state;
- mastery and weakness;
- unknown/untested knowledge;
- misconceptions;
- prerequisite gaps;
- confidence and uncertainty;
- validation;
- corrections;
- failures.

The central principle is:

> **ARIA should know the difference between remembering something about the learner and having evidence that the learner understands something.**

---

# 2. Intelligence Model

ARIA's intelligence should conceptually separate several layers.

```text
                    LEARNER
                       │
       ┌───────────────┼────────────────┐
       │               │                │
    Context          Memory          Evidence
       │               │                │
       │               │                ↓
       │               │          Learner Model
       │               │                │
       └───────────────┼────────────────┘
                       ↓
                AI Reasoning Layer
                       ↓
      ┌────────────────┼─────────────────┐
      │                │                 │
    Study          Recommendations    Adaptation
      │                │                 │
      └────────────────┼─────────────────┘
                       ↓
                Learning Actions
```

These layers may interact, but they must not be treated as interchangeable.

---

# 3. Requirement Categories

```text
AI-BEH-*      General AI behaviour
AI-CTX-*      Context management
AI-TOOL-*     Tool use
AI-MEM-*      Memory
AI-EVD-*      Evidence
AI-LM-*       Learner Model
AI-MAST-*     Mastery / weakness / unknown
AI-MIS-*      Misconceptions
AI-PREQ-*     Prerequisite gaps
AI-CONF-*     Confidence / uncertainty
AI-VAL-*      Validation
AI-CORR-*     User correction
AI-FAIL-*     AI failure behaviour
AI-AGENT-*    Agent architecture boundaries
```

---

# 4. General AI Behaviour

## AI-BEH-001 — Learning-purpose alignment

AI behaviour shall prioritize helping the learner make meaningful progress toward the active learning goal/context.

## AI-BEH-002 — Context-sensitive responses

AI responses should use relevant current context without unnecessarily injecting unrelated historical information.

## AI-BEH-003 — No false certainty

ARIA shall not present uncertain AI conclusions as established facts.

## AI-BEH-004 — Distinguish generation from knowledge state

The fact that ARIA explained a concept to the learner shall not be interpreted as evidence that the learner understood it.

## AI-BEH-005 — Distinguish exposure from mastery

Reading, viewing, listening to, or discussing material shall not automatically imply mastery.

## AI-BEH-006 — Product rules outrank model improvisation

AI-generated behaviour shall remain constrained by explicit product rules, learner permissions, context boundaries, and approval requirements.

## AI-BEH-007 — Learner instruction precedence

Current explicit learner instructions shall generally override conflicting inferred preferences or AI assumptions.

## AI-BEH-008 — Appropriate assistance

ARIA should be capable of choosing among explanation, hinting, questioning, retrieval, practice, feedback, or recommendation rather than always answering in the same mode.

## AI-BEH-009 — Avoid unnecessary complexity

ARIA should match explanation complexity to the learner's request and demonstrated context rather than defaulting to advanced or overly verbose language.

## AI-BEH-010 — Avoid empty encouragement

ARIA should prioritize specific, evidence-based learning feedback over generic praise or motivational filler.

## AI-BEH-011 — Challenge incorrect assumptions

ARIA should respectfully correct learner misconceptions or incorrect assumptions rather than agreeing merely to maintain conversational flow.

## AI-BEH-012 — State limitations

When ARIA lacks sufficient information, evidence, or tool access, it should communicate the limitation rather than inventing missing state.

---

# 5. Context Management

## AI-CTX-001 — Working context

ARIA shall maintain the context required for the current learning activity.

This may include:

```text
active goal
active topic
current task
selected resources
recent conversation
assessment specification
relevant learner-state signals
relevant preferences
time constraints
```

## AI-CTX-002 — Relevant-context retrieval

ARIA should retrieve relevant historical context when needed rather than injecting the learner's entire history into every interaction.

## AI-CTX-003 — Context scope

Context-specific information shall not automatically be treated as global learner information.

## AI-CTX-004 — Temporary context

ARIA shall support temporary constraints that expire after the relevant activity.

## AI-CTX-005 — Explicit context correction

When the learner corrects the current context, subsequent reasoning shall use the correction.

## AI-CTX-006 — Context provenance

Where consequential, ARIA should distinguish context that was explicitly supplied, retrieved, inherited, or inferred.

## AI-CTX-007 — Context conflict

When retrieved historical context conflicts with the learner's current explicit statement, current explicit information shall normally take precedence.

## AI-CTX-008 — Context minimization

ARIA should use only context relevant to the task where practical, improving privacy, cost, latency, and reasoning reliability.

---

# 6. Tool Use

ARIA may need tools for retrieval, search, scheduling, document processing, assessment execution, code execution, notifications, integrations, and other deterministic actions.

## AI-TOOL-001 — Tool necessity

ARIA should use a tool when the task requires information or an action that should not be fabricated by the language model.

## AI-TOOL-002 — Tool authorization

AI components shall only invoke tools/actions permitted for the learner and current workflow.

## AI-TOOL-003 — Tool input validation

Consequential tool calls should use validated inputs rather than unverified free-form model output.

## AI-TOOL-004 — Tool output grounding

When a tool provides authoritative task data, ARIA should ground downstream reasoning in the returned result rather than silently replacing it with model assumptions.

## AI-TOOL-005 — Tool failure

Tool failure shall be distinguishable from successful execution.

## AI-TOOL-006 — No fabricated execution

ARIA shall never claim an external action succeeded when the relevant tool did not confirm success.

## AI-TOOL-007 — Least authority

AI components should receive only the tool permissions necessary for their responsibilities.

## AI-TOOL-008 — High-impact confirmation

High-impact tool actions should respect confirmation/approval requirements defined by the product.

---

# 7. Memory Model

Memory represents useful persistent information about the learner and their learning environment.

Memory is **not** the same as the Learner Model.

```text
Memory
│
├── Explicit learner preferences
├── Persistent interaction preferences
├── Useful learner facts
├── Goal/context facts
├── Prior decisions
├── Relevant recurring constraints
└── Other durable context
```

## AI-MEM-001 — Persistent useful context

ARIA shall be capable of retaining useful information across sessions where appropriate.

## AI-MEM-002 — Explicit vs inferred memory

ARIA should distinguish learner-provided memory from inferred memory where relevant.

## AI-MEM-003 — Memory scope

Memory should support scopes such as global learner, goal-specific, or context-specific where necessary.

## AI-MEM-004 — Temporary information exclusion

Temporary instructions shall not automatically become persistent memory.

Example:

> "Explain this quickly because I have five minutes."

shall not automatically become:

> "Learner always wants short explanations."

## AI-MEM-005 — Memory usefulness

ARIA should avoid storing every conversational detail as durable memory merely because it appeared in a chat.

## AI-MEM-006 — Memory retrieval

Relevant memory should be retrievable when useful to the current task.

## AI-MEM-007 — Memory correction

Learners shall eventually be able to correct important persistent memory.

## AI-MEM-008 — Memory deletion

Learners shall eventually be able to remove supported persistent memory subject to required data rules.

## AI-MEM-009 — Memory uncertainty

Inferred memory should not be treated with the same certainty as explicit learner-provided facts.

## AI-MEM-010 — Memory provenance

Important inferred memory should retain enough provenance to support correction or explanation where appropriate.

---

# 8. Evidence Model

Evidence represents observations about learner performance or understanding.

Examples:

```text
Assessment answer
Teach-back response
Retrieval attempt
Problem-solving attempt
Revision retest
Coding solution result
Viva response
```

## AI-EVD-001 — Evidence records

ARIA shall store supported learning-performance observations as structured evidence.

## AI-EVD-002 — Evidence provenance

Evidence shall retain the activity that produced it.

## AI-EVD-003 — Concept association

Evidence should be associated with the concept, skill, topic, or learning objective it measures.

## AI-EVD-004 — Goal/context association

Evidence shall retain relevant goal/context association where necessary.

## AI-EVD-005 — Timestamp

Evidence shall retain when it was produced.

## AI-EVD-006 — Evidence type

ARIA shall distinguish different evidence types.

## AI-EVD-007 — Outcome

Evidence should capture the observed outcome, not merely that an activity occurred.

## AI-EVD-008 — Strength/reliability

Evidence should support a strength or reliability representation.

## AI-EVD-009 — Difficulty/context

Where relevant, evidence interpretation should account for difficulty, assistance, hints, time constraints, or other conditions affecting its strength.

## AI-EVD-010 — Independent attempts

Repeated independent successful attempts should generally provide stronger evidence than repeated exposure to the same answer.

## AI-EVD-011 — Assisted success

A correct response after extensive hints should not necessarily carry the same evidence strength as an independent correct response.

## AI-EVD-012 — Negative evidence

Incorrect or incomplete responses may provide evidence of weakness but shall not automatically prove a misconception.

## AI-EVD-013 — Evidence retention

ARIA should preserve sufficient historical evidence to reason about trends and changes over time.

## AI-EVD-014 — Corrected evidence

Evidence derived from an incorrect evaluation shall be revisable if the evaluation is corrected.

---

# 9. Learner Model

The Learner Model is ARIA's evidence-backed representation of the learner's current learning state.

```text
Learner Model
│
├── Concept state
├── Confidence
├── Supporting evidence
├── Recency
├── Possible misconceptions
├── Prerequisite gaps
├── Revision state
└── Change history
```

## AI-LM-001 — Evidence-backed state

Learner Model conclusions shall be derived from learning evidence rather than conversation memory alone.

## AI-LM-002 — Concept-level representation

ARIA should represent learner state at a useful concept/skill granularity rather than only one global score.

## AI-LM-003 — State uncertainty

Learner Model entries shall support uncertainty/confidence.

## AI-LM-004 — Evidence links

Important learner-state conclusions should retain links to supporting evidence.

## AI-LM-005 — State change over time

Learner state shall be capable of changing as new evidence arrives.

## AI-LM-006 — Contradictory evidence

Conflicting evidence should influence confidence rather than being silently discarded.

## AI-LM-007 — Recency

ARIA should consider evidence recency where relevant.

## AI-LM-008 — Forgetting

Strong historical performance shall not necessarily imply permanent mastery indefinitely.

## AI-LM-009 — Goal independence

Learner state may be reused across goals only when the underlying concept/skill is genuinely transferable and provenance remains clear.

## AI-LM-010 — No personality diagnosis

The Learner Model shall focus on learning-relevant state and shall not make unsupported psychological or personality diagnoses.

---

# 10. Concept-State Model

ARIA should support richer states than simply `known / unknown`.

A conceptual state model may include:

```text
UNTESTED
    ↓
EXPOSED
    ↓
DEVELOPING
   ↙   ↘
WEAK   STRONG
   ↘   ↙
REQUIRES_REVIEW
    ↓
MASTERED (high-confidence, evidence-backed)
```

Possible misconceptions and prerequisite gaps should remain separate flags/structures rather than being forced into the same linear scale.

Exact state names may change during architecture/design.

## AI-MAST-001 — Untested

ARIA shall distinguish insufficient evidence from poor performance.

## AI-MAST-002 — Developing

ARIA should support intermediate states when evidence is incomplete or mixed.

## AI-MAST-003 — Weak

Weak state should require meaningful evidence of difficulty, not merely lack of activity.

## AI-MAST-004 — Strong

Strong state should reflect repeated or sufficiently reliable evidence of understanding/performance.

## AI-MAST-005 — Mastery threshold

Mastery should require a stronger evidence threshold than a single successful attempt.

## AI-MAST-006 — Mastery decay/review

Mastery may transition to a review-needed state when evidence becomes stale or later performance contradicts it.

## AI-MAST-007 — Explain state

Where useful, the learner should be able to understand why ARIA considers a concept weak, strong, untested, or due for review.

---

# 11. Misconception Detection

A misconception is not simply an incorrect answer. It is a potentially systematic incorrect mental model or reasoning pattern.

## AI-MIS-001 — Candidate misconception

ARIA may create a possible-misconception hypothesis when evidence suggests a repeated or structured misunderstanding.

## AI-MIS-002 — Single-error protection

A single incorrect answer shall not normally be sufficient to confirm a misconception.

## AI-MIS-003 — Pattern requirement

Misconception confidence should increase when similar reasoning errors recur across relevant independent evidence.

## AI-MIS-004 — Diagnostic questioning

ARIA should be capable of asking targeted diagnostic questions to distinguish a misconception from a careless mistake or missing prerequisite.

## AI-MIS-005 — Possible vs confirmed

ARIA shall distinguish a suspected misconception from a sufficiently supported misconception.

## AI-MIS-006 — Remediation

A supported misconception may trigger targeted explanation, counterexample, guided reasoning, practice, or revision.

## AI-MIS-007 — Retest

After remediation, ARIA should seek new evidence before considering the misconception resolved.

## AI-MIS-008 — Learner visibility

Misconception-related learner-facing language should avoid presenting uncertain hypotheses as unquestionable facts.

## AI-MIS-009 — Resolution history

ARIA should retain enough history to know that a misconception was detected, addressed, and later retested where useful.

---

# 12. Prerequisite Gap Detection

A learner may struggle with topic B because concept A is missing.

```text
Prerequisite A
      ↓
   Topic B
      ↓
Observed difficulty
```

ARIA should attempt to distinguish "B is difficult" from "A is missing, causing B to fail."

## AI-PREQ-001 — Dependency awareness

ARIA should support concept prerequisite/dependency relationships where available.

## AI-PREQ-002 — Gap hypothesis

ARIA may hypothesize a prerequisite gap when learner errors are consistent with missing prerequisite knowledge.

## AI-PREQ-003 — Diagnostic validation

ARIA should validate important prerequisite-gap hypotheses through existing evidence or targeted diagnostic activity.

## AI-PREQ-004 — No automatic certainty

A prerequisite relationship alone shall not prove the learner lacks the prerequisite.

## AI-PREQ-005 — Remediation recommendation

A sufficiently supported prerequisite gap may trigger a recommendation to review the prerequisite before continuing dependent material.

## AI-PREQ-006 — Roadmap impact

Significant prerequisite gaps may trigger roadmap adaptation proposals according to Step 4 approval rules.

## AI-PREQ-007 — Re-evaluation

After prerequisite remediation, ARIA should re-evaluate performance on the dependent concept.

---

# 13. Confidence & Uncertainty

## AI-CONF-001 — Confidence representation

Important AI-derived learner conclusions shall support a confidence/uncertainty representation.

## AI-CONF-002 — Confidence is not model swagger

Confidence shall be based on available evidence quality and consistency, not merely how certain an LLM sounds.

## AI-CONF-003 — Evidence quantity

Multiple relevant independent observations may increase confidence.

## AI-CONF-004 — Evidence quality

Higher-quality evidence should contribute more strongly than weak evidence.

## AI-CONF-005 — Contradiction

Contradictory evidence should reduce or complicate confidence.

## AI-CONF-006 — Recency

Old evidence may carry less weight for current-state claims where forgetting is relevant.

## AI-CONF-007 — Assistance level

Highly assisted responses may carry lower confidence for independent mastery claims.

## AI-CONF-008 — Confidence thresholds

Consequential actions shall require stronger confidence than low-risk recommendations.

## AI-CONF-009 — Learner-facing uncertainty

ARIA should communicate uncertainty in understandable language when it materially affects a recommendation or conclusion.

---

# 14. Example Evidence Weighting Model

The final mathematical model is an architecture/research decision, but the PRD requires the following conceptual behaviour.

```text
Evidence Strength ≈
    task reliability
  × difficulty relevance
  × independence
  × recency factor
  × assistance factor
  × evaluation confidence
```

Examples:

```text
Independent correct answer on a difficult unseen problem
→ relatively strong evidence

Correct answer after answer-revealing hints
→ weaker mastery evidence

Reading a note
→ exposure evidence, not mastery evidence

Repeated same conceptual error across independent questions
→ stronger misconception signal
```

ARIA shall not expose a fake precision score to learners merely because an internal model uses numeric values.

---

# 15. Generate → Validate → Fix

For important structured AI outputs, ARIA should not rely solely on one unconstrained generation pass.

```text
Generate
   ↓
Validate
   ↓
Valid? ── Yes → Use
   │
   No
   ↓
Repair / Regenerate
   ↓
Validate again
```

## AI-VAL-001 — Structured output validation

AI-generated structured data shall be validated against the required schema/constraints before downstream use.

## AI-VAL-002 — Assessment validation

Generated assessments should be checked for specification compliance before delivery.

Potential checks include:

- requested question count;
- selected formats;
- marks consistency;
- answer availability;
- source/topic relevance;
- duplicate questions;
- invalid options;
- impossible scoring.

## AI-VAL-003 — Roadmap validation

Generated roadmaps should be checked for structural validity and obvious dependency inconsistencies before becoming active.

## AI-VAL-004 — Planner validation

Generated plans should be checked for obvious time conflicts, deadline violations, and impossible workloads.

## AI-VAL-005 — Evidence validation

AI-generated evidence extraction shall be checked before it can create high-confidence learner-state changes.

## AI-VAL-006 — Repair

When validation fails and safe repair is possible, ARIA should repair/regenerate the invalid portion rather than accepting malformed output.

## AI-VAL-007 — Retry limit

Validation-repair loops shall have bounded retry limits.

## AI-VAL-008 — Graceful failure

If valid output cannot be produced after bounded attempts, ARIA shall fail safely rather than forwarding invalid data downstream.

---

# 16. Task Decomposition

## AI-BEH-013 — Decompose complex tasks

ARIA should decompose complex learning/product tasks into bounded subtasks when doing so improves reliability.

Example:

```text
"Create my exam"
       ↓
Interpret specification
       ↓
Retrieve relevant source material
       ↓
Generate questions
       ↓
Generate/verify answer keys or rubrics
       ↓
Validate specification compliance
       ↓
Render assessment
```

## AI-BEH-014 — Do not over-decompose

Simple deterministic actions should not be converted into unnecessary multi-agent workflows.

## AI-BEH-015 — Clear responsibility

Each decomposed AI responsibility should have clear inputs, outputs, permissions, and failure behaviour.

---

# 17. Agent Architecture Boundaries

This PRD intentionally does **not** decide how many agents ARIA will have.

## AI-AGENT-001 — Agents are implementation choices

A product feature shall not automatically imply a dedicated AI agent.

## AI-AGENT-002 — Deterministic-first

Deterministic code should be used for rules, validation, authorization, calculations, state transitions, and other tasks where probabilistic reasoning is unnecessary.

## AI-AGENT-003 — Specialized reasoning where useful

Specialized AI components may be used where distinct prompts, tools, context, validation, or permissions improve reliability.

## AI-AGENT-004 — Orchestrator authority limits

An orchestrator shall not bypass product approval, authorization, or validation boundaries.

## AI-AGENT-005 — Shared state discipline

Multiple AI components shall not independently overwrite learner state without controlled state-update mechanisms.

## AI-AGENT-006 — Communication contracts

Where multiple AI components communicate, outputs should use explicit contracts/structured schemas for consequential data.

## AI-AGENT-007 — No autonomous infinite loops

Agentic workflows shall have bounded iteration, tool-use, and retry limits.

## AI-AGENT-008 — Observability

Consequential agentic workflows should produce enough trace information for debugging and evaluation without requiring exposure of private internal reasoning to the learner.

---

# 18. User Correction

## AI-CORR-001 — Correct memory

Learners shall be able to correct important persistent information about themselves.

## AI-CORR-002 — Correct learner state

Where appropriate, learners should be able to challenge an inaccurate learner-state conclusion.

A learner assertion alone need not automatically overwrite strong contrary performance evidence; instead, it should trigger review/reassessment where appropriate.

## AI-CORR-003 — Correct context

Learners shall be able to correct goal/topic/context association.

## AI-CORR-004 — Correct evaluation

Incorrect AI evaluation shall have a correction/review path.

## AI-CORR-005 — Downstream correction

When source evidence or evaluation is corrected, dependent derived state should be capable of recomputation.

## AI-CORR-006 — Preserve audit history

Corrections should preserve sufficient history to understand why derived state changed.

---

# 19. AI Failure Behaviour

## AI-FAIL-001 — No silent fabrication

When required information is unavailable, ARIA shall not fabricate it to complete a workflow.

## AI-FAIL-002 — Partial completion

If one AI subtask fails, successful independent work should be preserved where possible.

## AI-FAIL-003 — Tool failure distinction

ARIA shall distinguish AI reasoning failure from external tool/service failure where useful.

## AI-FAIL-004 — Model timeout/retry

Transient model failures may be retried within bounded limits.

## AI-FAIL-005 — Invalid structured output

Invalid model output shall not be written directly into consequential product state without validation.

## AI-FAIL-006 — Fallback behaviour

Where practical, ARIA should provide a lower-intelligence but reliable fallback rather than making the entire product unusable.

Example:

If personalized recommendation generation fails, the learner can still access their roadmap and planned work.

## AI-FAIL-007 — Preserve learner work

AI failure shall not discard learner-created notes, submitted answers, uploaded resources, or completed work.

## AI-FAIL-008 — Avoid repeated harmful retry

ARIA shall not endlessly retry a failing AI/tool workflow.

## AI-FAIL-009 — Explain actionable failure

Where learner action can resolve the problem, ARIA should explain the next useful action.

---

# 20. Memory vs Learner Model — Explicit Separation

This distinction is mandatory.

| Memory | Learner Model |
|---|---|
| "Prefers examples before formulas" | "Weak evidence on Bayes' theorem" |
| "Preparing for GATE" | "Strong on process scheduling" |
| "Usually studies in the evening" | "Serializability requires review" |
| "Wants hints before solutions" | "Possible misconception about deadlock prevention" |
| "Uses concise revision before exams" | "Prerequisite gap suspected in normalization" |

Memory may help determine **how ARIA interacts**.

The Learner Model helps determine **what the learner appears to know and what learning action may be useful next**.

Neither should silently replace the other.

---

# 21. Example — One Wrong Answer

```text
Question: incorrect
        ↓
Evidence recorded
        ↓
Was it independent?
Was the question valid?
Was evaluation reliable?
Is there previous evidence?
Was this a careless error?
        ↓
Insufficient pattern
        ↓
Do NOT declare misconception
        ↓
Potentially ask another diagnostic question
```

This protects ARIA from overreacting to noise.

---

# 22. Example — Repeated Misconception

```text
Attempt 1:
Learner uses the same incorrect reasoning
        ↓
Attempt 2:
Different question, same reasoning error
        ↓
Teach-back:
Learner explicitly states incorrect mental model
        ↓
Evidence converges
        ↓
Possible misconception confidence rises
        ↓
ARIA provides targeted remediation
        ↓
New diagnostic questions
        ↓
Evidence improves
        ↓
Misconception marked resolved / confidence reduced
```

---

# 23. Example — Memory Without Evidence

Learner says:

> "I'm really good at DBMS."

ARIA may remember that the learner considers themselves confident in DBMS.

It should **not** immediately mark every DBMS concept as mastered.

Later assessments may independently produce learner-model evidence.

---

# 24. Example — Evidence Without Memory

A learner completes several strong SQL assessments but never says:

> "I'm good at SQL."

ARIA may still develop a high-confidence learner-model state for the assessed SQL concepts because performance evidence exists.

The learner did not need to explicitly state the fact for the Learner Model to update.

---

# 25. Example — Prerequisite Gap

```text
Learner repeatedly struggles with JOIN query reasoning
                 ↓
ARIA notices errors depend on weak relational-key understanding
                 ↓
Existing evidence on keys is insufficient
                 ↓
ARIA asks targeted prerequisite questions
                 ↓
Key-concept weakness confirmed with sufficient evidence
                 ↓
Recommendation:
Review keys before advanced JOIN practice
                 ↓
Roadmap adaptation check if impact is significant
```

---

# 26. Example — Explainable Adaptation

Bad:

> "ARIA changed your roadmap because AI thinks this is better."

Required behaviour:

> "ARIA is suggesting one prerequisite session on normalization because your last two independent attempts showed difficulty identifying functional dependencies, which the next roadmap topic depends on."

The learner can inspect, accept, modify, or reject the consequential change according to Step 4.

---

# 27. Intelligence Safety Rules

ARIA's intelligence layer shall preserve these invariants:

1. **Memory is not mastery.**
2. **Exposure is not understanding.**
3. **One error is not automatically a misconception.**
4. **One success is not automatically mastery.**
5. **No evidence is not weakness.**
6. **Model confidence is not evidence confidence.**
7. **AI output is not valid merely because it is well-written.**
8. **Important structured outputs require validation.**
9. **Uncertain upstream conclusions remain uncertain downstream.**
10. **User correction must be possible.**
11. **Consequential adaptations remain bounded by Step 4 approval rules.**
12. **Deterministic logic should not be replaced by an agent without reason.**
13. **Agent/tool loops must be bounded.**
14. **Learner work survives AI failures.**
15. **ARIA should be useful even when its most advanced intelligence is unavailable.**

---

# 28. Step 5 Decisions

Step 5 establishes the core intelligence philosophy for ARIA:

```text
Conversation Context
       +
Persistent Memory
       +
Structured Learning Evidence
       ↓
Evidence-backed Learner Model
       ↓
Confidence-aware reasoning
       ↓
Recommendations / Revision / Adaptation
       ↓
Validation + learner control
```

ARIA is therefore not intended to become a chatbot that simply remembers everything the learner says.

Its differentiating intelligence should come from connecting **what the learner is trying to achieve**, **what they have done**, **what evidence suggests they understand**, **what may be missing**, and **what action makes sense next**.

---

# 29. Step 5 Completion

**Step 5 — AI, Learner Model, Memory & Evidence Requirements is complete.**

Next:

# Step 6 — Non-Functional, Privacy, Security, Reliability & Accessibility Requirements

Step 6 will define requirements for:

```text
performance
availability
scalability
latency
privacy
security
authorization
data retention
AI/data boundaries
resource security
reliability
observability
backup/recovery
accessibility
responsive behaviour
browser/device support
cost-awareness
rate limits
abuse protection
```

After Step 6, the PRD can move toward acceptance criteria, prioritization, MVP sequencing, and the transition from product requirements into system architecture.