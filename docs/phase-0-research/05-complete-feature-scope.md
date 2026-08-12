# ARIA — Phase 0 Research

## 05 — Complete Feature Scope

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 0 — Research  
**Status:** Step 5 — Complete Feature Scope  
**Basis:** Steps 1–4, product discussions, user research, competitor analysis, product vision, target users, and use cases

---

# 1. Scope Principle

ARIA is being designed as a complete integrated learning system, not as a collection of unrelated AI study features.

The long-term product vision includes the complete learning workflow. Implementation may happen incrementally, but the architecture should be designed with the complete system in mind.

ARIA has three product commitments:

1. **Integration** — major learning activities exist in one coherent environment.
2. **Automation** — the learner should not manually coordinate every part of the learning workflow.
3. **Adaptation** — evidence from learning should be capable of changing future teaching, assessment, revision, roadmaps, planning, and recommendations.

A fourth UX principle applies throughout the product:

> **Maximum user control when the learner wants it; automation where it removes unnecessary management work.**

---

# 2. Complete ARIA Product Map

```text
ARIA
│
├── Account & Onboarding
├── Home
├── Study
├── Resources
├── Notes
├── Audio
├── Exams / Assessment
├── Roadmaps
├── Planner
├── Progress
├── Search
├── Notifications
└── Settings & User Control

Shared Intelligence
│
├── Learner Model
├── Memory
├── Evidence Engine
├── Evaluation Engine
├── Misconception Tracking
├── Revision Engine
├── Recommendation Engine
├── Prerequisite Detection
├── Personalization
└── Readiness / Learning-State Estimation

Orchestration & Reliability
│
├── ARIA Orchestrator
├── Cross-feature Events
├── Agent Workflows
├── Human-in-the-Loop Controls
├── Validation
├── Error Recovery
└── Provenance / Traceability

Platform
│
├── Authentication
├── Database
├── File Storage
├── Retrieval / Search
├── Notification Delivery
├── External Integrations
├── AI Providers
├── Security / Privacy
└── Observability
```

---

# 3. Account, Authentication & Onboarding

ARIA requires persistent accounts because learning history, goals, roadmaps, resources, assessments, notes, memory, and learner_concept_state belong to an individual learner.

## Authentication capabilities

- Sign up
- Sign in
- Email verification
- Sign out
- Password recovery / reset
- Session management
- Account deletion
- Optional social sign-in such as Google in later implementation

## Onboarding

Onboarding should remain lightweight.

ARIA should not ask the learner to completely describe their learning style, deadlines, subjects, and future goals before using the product.

Initial onboarding may establish:

- basic account/profile information;
- what the learner broadly wants to use ARIA for;
- optional initial goal;
- useful preferences.

ARIA should learn substantially more through actual use.

There should be no assumption that every user has one deadline or one examination.

---

# 4. Home — Learning Command Centre

Home answers:

> **What should I do now?**

It should be personalized from the learner's current state rather than populated with hardcoded subjects or generic widgets.

Possible capabilities:

- Continue the latest learning session
- Today's planned activities
- Due revision
- Upcoming exams and deadlines
- Active goals
- Roadmap progress
- Weak areas needing attention
- Recent progress
- Recommended next action
- Plan-change proposals
- Recently used resources
- Upcoming assessments
- Important ARIA notifications
- Quick actions such as Study, Generate Exam, Add Resource, or Create Goal

Home should summarize the system without becoming another manually maintained dashboard.

---

# 5. Study

Study is ARIA's primary conversational learning environment.

## Core capabilities

The learner can:

- ask questions;
- learn a topic from scratch;
- ask follow-up questions;
- request examples and analogies;
- request simpler or deeper explanations;
- work through problems;
- request hints rather than solutions;
- study from selected resources;
- ask ARIA to question them during learning;
- connect the conversation to a goal or roadmap topic;
- create notes from useful parts of the session;
- create revision or assessment material from the session.

## Study behaviours / modes

Possible behaviours include:

### Tutor

Normal explanatory conversation.

### Guided Learning

ARIA uses hints and intermediate questions rather than immediately revealing answers.

### Socratic Learning

Question-driven exploration.

### Teach ARIA

The learner explains the concept and ARIA evaluates conceptual coverage.

### Rapid Revision

High-density review when the learner has limited time.

### Resource-Grounded Study

ARIA prioritizes selected learner resources and preserves source provenance where practical.

These do not necessarily require separate pages. They can be interaction modes within Study.

## Study-to-system automation

Study interactions may produce learning evidence, but conversational behaviour alone should not automatically be treated as proof of mastery or weakness.

Repeated confusion can become low-confidence evidence. Stronger conclusions should rely on assessment, retrieval, teach-back, or other meaningful evidence.

---

# 6. Resources

Resources are the learner's connected learning library.

## Supported resource concepts

Potential resource types include:

- PDFs
- Documents
- Slides
- Syllabus files
- Previous exam papers
- Websites
- Articles
- YouTube videos
- Course links
- Documentation
- Books / references
- Personal notes
- ARIA notes
- ARIA conversations
- Generated learning material
- Audio material
- External practice links

## Capabilities

- Upload / add resources
- Organize by goal, roadmap, topic, or collection
- Search resources
- Preview resources
- Study from one or multiple resources
- Generate notes from resources
- Generate assessments from resources
- Generate audio from resources
- Associate resources with roadmap topics
- Track relevant resource usage
- Preserve source provenance / citations where practical
- Recommend resources where appropriate

ARIA should not hardcode resources such as DSA or AWS. Resources must follow the learner's goals.

## External platforms

ARIA can link to specialist platforms rather than unnecessarily rebuild them.

Examples include course platforms, coding-practice platforms, video platforms, documentation, and other learning systems.

Where APIs and permissions make synchronization feasible, external progress integrations may be added. Otherwise, links and learner-confirmed progress remain valid.

---

# 7. Notes

Notes support both manual knowledge capture and AI-assisted transformation.

## Capabilities

- Create notes manually
- Edit notes
- Organize notes by goal/topic
- Generate notes from Study
- Generate notes from resources
- Consolidate multiple resources into notes
- Generate notes from exam mistakes
- Generate topic summaries
- Create detailed notes
- Create concise notes
- Create revision sheets
- Extract definitions, formulas, examples, and key concepts
- Convert notes into retrieval prompts / flashcards
- Convert notes into audio
- Link notes back to sources where possible
- Search notes

Notes should remain editable. ARIA-generated notes are not immutable outputs.

---

# 8. Audio Learning

Audio has two major product directions.

## 8.1 Source Audio

The learner selects material such as:

- notes;
- PDFs;
- resources;
- study-session content;
- selected roadmap topics.

ARIA generates an audio learning experience.

Possible styles include:

- detailed explanation;
- concise summary;
- revision;
- conversational / podcast-style explanation;
- custom learner instruction.

## 8.2 Adaptive Audio

ARIA can generate audio based on learner_concept_state rather than merely narrating a source.

Example request:

> "I have 15 minutes. Revise me for my exam."

ARIA may consider:

- exam scope;
- available time;
- completed topics;
- assessment evidence;
- weak concepts;
- misconceptions;
- revision history;
- topic importance.

The result can prioritize the learner's actual needs.

## Future interactive audio

Audio may eventually become conversational: ARIA asks questions, waits for responses, evaluates recall, and continues revision.

---

# 9. Exams & Assessment Engine

Assessment must **not** be designed around one fixed exam format.

Different learners prepare for fundamentally different assessment experiences.

Examples:

- government / competitive exams may emphasize MCQs;
- GATE-style preparation may use MCQ, MSQ, and numerical-answer formats;
- university exams may use sections, marks, short answers, long answers, and problems;
- placement DSA assessment may require timed coding contests;
- interview or viva preparation may require conversational questioning.

Therefore ARIA uses a **configurable Assessment Engine**.

---

# 10. Generate Exam Flow

The learner controls the final exam specification.

ARIA may assist with defaults or recommendations, but it should not silently decide the learner's desired exam format.

## Creation flow

```text
Generate Exam
     ↓
Choose what to test
     ↓
Select goal / topics / resources
     ↓
Choose question / assessment format
     ↓
Configure exam
     ↓
Review specification
     ↓
Generate
     ↓
Exam Card
     ↓
Start assessment
```

## Natural-language creation

The learner may describe the assessment directly:

> "Give me 30 hard MCQs from these notes, 45 minutes, with negative marking."

ARIA can translate the request into an editable configuration before generation.

## Advanced configuration

Possible options include:

- Goal / exam type
- Topics
- Syllabus
- Selected resources
- Question formats
- Number of questions
- Marks
- Duration
- Difficulty
- Sections
- Scoring rules
- Negative marking
- Partial marking
- Attempts
- Feedback timing
- Source restrictions
- Custom instructions
- Language where relevant

Not every field must be required. Unspecified fields can use visible sensible defaults.

---

# 11. Assessment Formats

The Assessment Engine should be extensible.

Potential formats include:

- MCQ
- Multiple-select
- Numerical answer
- True / false
- Fill in the blank
- Short answer
- Long answer
- Essay
- Conceptual reasoning
- Scenario / application questions
- Problem solving
- Coding problems
- Timed coding contest
- Oral / viva
- Teach-back
- Mixed / custom assessment

A custom assessment may combine multiple sections and formats.

---

# 12. Exam Specification & Dynamic Exam Cards

An assessment is represented by an **Exam Specification** rather than a hardcoded UI.

Example:

```text
Exam Specification
│
├── Goal / context
├── Topics
├── Resources / syllabus
├── Formats
├── Sections
├── Question count / marks
├── Difficulty
├── Duration
├── Scoring rules
├── Feedback behaviour
└── Custom instructions
```

The UI renderer creates an appropriate exam experience from the specification.

Examples:

### Competitive exam card

```text
GATE CSE — Operating Systems
30 Questions
45 Minutes
MCQ • MSQ • NAT
Configured scoring rules
```

### Coding contest card

```text
DSA Placement Contest
3 Problems
90 Minutes
Coding assessment
Configured language / evaluation rules
```

### University exam card

```text
DBMS Semester Mock
70 Marks
3 Hours
Section A — Short Answer
Section B — Long Answer
Section C — Problems
```

The exam card is generated from the learner's chosen configuration.

---

# 13. Assessment Modes

Depending on configuration, ARIA may support:

- Practice assessment
- Mock exam
- Quick quiz
- Diagnostic assessment
- Revision test
- Timed contest
- Viva / oral assessment
- Teach-back assessment
- Custom mixed assessment

The user controls the desired format. ARIA can recommend an assessment type when useful, but recommendations remain editable.

---

# 14. Coding Assessment Boundary

ARIA should not attempt to replace large specialist coding-practice platforms.

However, coding can be an **assessment type** inside ARIA.

A future coding assessment environment may support:

- generated coding problems;
- language selection;
- code execution;
- visible / hidden test cases;
- time limits;
- correctness evaluation;
- complexity discussion;
- timed contest structure;
- assessment evidence feeding the learner model.

External coding platforms can remain learning resources or practice systems while ARIA uses targeted coding assessments to evaluate progress.

---

# 15. Evaluation Engine

Assessment generation and assessment evaluation are separate responsibilities.

The Evaluation Engine may analyze:

- correctness;
- conceptual coverage;
- reasoning quality;
- missing concepts;
- misconceptions;
- repeated mistakes;
- application ability;
- performance by topic;
- improvement over time;
- source-grounded correctness where relevant.

ARIA should avoid reducing every assessment to a single percentage.

Example:

```text
Normalization       Strong
SQL                 Strong
Transactions        Moderate
Indexing            Weak

Recurring misconception:
Clustered vs non-clustered indexes
```

Evaluation becomes evidence for other ARIA systems.

---

# 16. Roadmaps

Roadmaps represent the learner's path toward a goal.

## Capabilities

- Create roadmap from a goal
- Personalized phases
- Topics and subtopics
- Prerequisites
- Dependencies
- Milestones
- Resources
- Learning activities
- Assessments
- Estimated effort
- Topic status
- Progress
- Roadmap history

Roadmaps are not hardcoded around any domain.

## Living roadmaps

Roadmaps should be capable of adapting to learning evidence.

Example:

```text
Assessment
   ↓
Prerequisite weakness detected
   ↓
Roadmap change proposed
   ↓
Learner reviews reason
   ↓
Accept / modify / reject
```

Important changes should be explainable.

---

# 17. Planner

Planner translates goals and roadmaps into time.

## Inputs

- Multiple goals
- Roadmaps
- Deadlines
- Learner availability
- Topic dependencies
- Estimated effort
- Revision requirements
- Assessment schedule
- Priority
- Missed sessions

## Capabilities

- Today view
- Week view
- Calendar view
- Goal schedule
- Study sessions
- Revision sessions
- Mock-exam scheduling
- Milestones
- Reminders
- Rescheduling
- Plan recovery

## Automatic recovery

Missed work should not simply accumulate as overdue tasks.

ARIA can recalculate remaining work and propose a realistic recovery plan while respecting prerequisites, deadlines, and learner availability.

---

# 18. Revision Engine

Revision determines what knowledge should return and when.

The scheduling component should use deterministic learning/repetition logic where appropriate rather than delegating everything to an LLM.

Possible revision formats include:

- flashcards / retrieval prompts;
- short-answer recall;
- rapid quizzes;
- teach-back;
- oral questioning;
- audio revision;
- targeted mini-assessments.

Revision results become new evidence.

---

# 19. Progress

Progress should emphasize learning rather than app usage.

## Views

- Goal progress
- Roadmap progress
- Topic / concept status
- Knowledge map
- Assessment history
- Misconceptions
- Revision health
- Improvement over time
- Untested concepts
- Exam / goal readiness where applicable

Activity metrics such as study time may exist, but they should not be treated as proof of learning.

---

# 20. Learner Model

The Learner Model is ARIA's central structured representation of the learning journey.

Potential state includes:

```text
Learner
│
├── Goals
├── Concepts / topics
├── Knowledge estimates
├── Strengths
├── Weaknesses
├── Misconceptions
├── Evidence
├── Assessment history
├── Revision history
├── Learning history
├── Resources
├── Roadmaps
├── Plans
├── Deadlines
└── Relevant preferences
```

The Learner Model is not identical to conversational memory.

---

# 21. Memory

Memory stores useful persistent information that helps ARIA personalize interactions.

Examples:

- prefers examples before formal definitions;
- prefers hints before solutions;
- prefers concise revision;
- currently following a particular external course;
- relevant recurring learning preferences.

Users should eventually have a **What ARIA Knows About Me** interface with controls such as:

- Why does ARIA think this?
- Correct
- Edit
- Forget

---

# 22. Evidence Engine

ARIA's beliefs about learning should be connected to evidence.

Potential evidence sources include:

- exam answers;
- quizzes;
- coding assessments;
- viva responses;
- teach-back;
- retrieval attempts;
- study interactions;
- completed activities;
- manual learner corrections.

Evidence should have different strengths.

For example, asking a question about recursion is much weaker evidence than repeatedly failing application questions about recursion.

The system should represent confidence rather than treating every signal equally.

---

# 23. Misconception Tracking

ARIA should remember specific conceptual errors where evidence supports them.

Example:

```text
Recursion
├── Base case          understood
├── Recursive step     understood
└── Stack unwinding    misconception detected
```

Misconceptions can influence:

- Study explanations
- Revision
- Future assessments
- Recommendations
- Roadmap decisions
- Progress views

---

# 24. Prerequisite Detection

When a learner struggles with an advanced topic, ARIA should consider whether the actual problem is a missing prerequisite.

Example:

```text
Difficulty with advanced concept
       ↓
Evidence analysis
       ↓
Possible prerequisite gap
       ↓
Targeted assessment / confirmation
       ↓
Roadmap or Study recommendation
```

ARIA should avoid making large roadmap changes from weak evidence alone.

---

# 25. Recommendation Engine

ARIA continuously determines useful next actions.

Examples:

- Continue a topic
- Review a prerequisite
- Take a diagnostic assessment
- Perform due retrieval
- Take a mock exam
- Listen to a revision audio session
- Resume a paused roadmap
- Review a proposed plan change

Recommendations should include understandable reasons where useful.

---

# 26. Search Across Learning History

ARIA should provide global search across relevant learner content.

Potential searchable areas:

- Chats
- Notes
- Resources
- Roadmaps
- Topics
- Assessments
- Audio

Example:

> "Where did I learn about cosine similarity?"

ARIA can return relevant conversations, notes, and resources.

---

# 27. Notifications & Reminders

Notifications are part of the learning system rather than an isolated feature.

## Initial delivery channels

- In-app notifications
- Email reminders

Future deployment may support push notifications where appropriate.

## Notification sources

```text
Planner ──────────┐
Revision ─────────┤
Assessments ──────┤
Roadmaps ─────────┼→ Notification Service → In-app / Email
Goal deadlines ───┤
Plan recovery ────┤
ARIA alerts ──────┘
```

## Examples

- Revision due
- Upcoming planned study session
- Upcoming exam
- Goal deadline approaching
- Plan recovery ready for review
- Roadmap change ready for review
- Important weak area remains unassessed

Users must control notification type, email delivery, frequency, and reminder timing.

ARIA should avoid excessive reminder spam.

---

# 28. Settings & User Control

Settings should include appropriate controls for:

- Profile
- Account
- Password / security
- Learning preferences
- Memory
- Personalization
- Notifications
- Email reminders
- Privacy / data controls
- Integrations
- Appearance / accessibility
- Export / delete learning data where supported

Automation should not remove learner agency.

---

# 29. Human-in-the-Loop Controls

ARIA may automate low-risk coordination, but meaningful changes should remain inspectable.

Examples:

```text
Roadmap change proposed
→ Why?
→ Preview
→ Accept
→ Modify
→ Reject
```

Similar controls can apply to major planner changes, learner-model corrections, and other consequential personalization decisions.

---

# 30. Cross-Feature Automation

Cross-feature coordination is one of ARIA's defining features.

ARIA should eventually use structured events rather than tightly coupling every page directly to every other page.

## Example: ExamCompleted

```text
Exam completed
      ↓
Evaluation Engine
      ↓
Evidence Engine
      ↓
Learner Model
      ↓
Misconception Tracking
      ↓
Progress
      ↓
Revision scheduling
      ↓
Roadmap adaptation check
      ↓
Planner adaptation check
      ↓
Recommendation update
```

## Example: StudySessionCompleted

```text
Study session completed
      ↓
Learning history updated
      ↓
Relevant evidence extracted carefully
      ↓
Notes / revision candidates available
      ↓
Roadmap progress reconsidered
      ↓
Home recommendations update
```

## Example: PlannedSessionMissed

```text
Planned session missed
      ↓
Planner evaluates remaining workload
      ↓
Recovery plan generated
      ↓
Learner reviews proposed changes
      ↓
Plan updated
      ↓
Notifications adjusted
```

The detailed event contracts belong in later architecture work.

---

# 31. ARIA Orchestrator

The learner interacts with ARIA rather than manually selecting backend agents.

The orchestrator determines which capabilities are required for a request.

Example:

```text
Learner:
"My exam is Friday and I'm weak in chapters 4 and 5. Help me."

                  ARIA
                    ↓
               Orchestrator
                    ↓
        ┌───────────┼───────────┐
        ↓           ↓           ↓
      Study      Planner     Evaluation
        ↓           ↓           ↓
      Notes      Roadmap    Learner Model
                    ↓
                  Audio
```

Agent boundaries will be formally designed during the AI Architecture phase.

Not every subsystem should become an LLM agent. Deterministic services should handle tasks such as authentication, database operations, notification delivery, calculations, and appropriate scheduling logic.

---

# 32. Validation & Reliability

ARIA's interconnected nature increases the cost of incorrect AI outputs.

A bad conclusion could propagate:

```text
Incorrect evaluation
       ↓
Incorrect learner_concept_state
       ↓
Incorrect roadmap adaptation
       ↓
Incorrect plan
       ↓
Poor future learning recommendations
```

Therefore later architecture should include appropriate:

- structured outputs;
- validation;
- source grounding;
- provenance;
- confidence handling;
- retries / fallbacks;
- logging;
- workflow testing;
- human approval for meaningful changes;
- Generate–Validate–Fix patterns where valuable.

---

# 33. Product Boundaries

ARIA can integrate with external learning ecosystems without recreating all of them.

ARIA is not primarily intended to become:

- a full LeetCode replacement;
- a YouTube replacement;
- a Coursera / Udemy replacement;
- a general-purpose Notion replacement;
- a coding IDE;
- an institutional LMS;
- a general-purpose search engine.

ARIA coordinates the learning journey and can treat specialist products as resources, activities, or integrations.

---

# 34. Complete Learning Loop

```text
                 LEARNING GOAL
                       ↓
                    ROADMAP
                       ↓
                    PLANNER
                       ↓
                     STUDY
                       ↓
              NOTES / RESOURCES
                       ↓
              PRACTICE / EXAM
                       ↓
                  EVALUATION
                       ↓
                   EVIDENCE
                       ↓
                LEARNER MODEL
                       ↓
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
     ROADMAP         PLANNER         STUDY
     adapts          adapts          adapts
        ↓              ↓              ↓
        └────────── REVISION ─────────┘
                       ↓
              AUDIO / STUDY / TEST
                       ↓
                  NEW EVIDENCE
                       ↓
                       ↺
```

This loop is the central behaviour that connects ARIA's feature scope.

---

# 35. Scope Audit

The Step 5 audit confirms that the complete scope now covers the major requirements discovered in Steps 1–4 and subsequent product decisions:

- goal-driven, domain-independent learning;
- authentication and persistent user state;
- lightweight onboarding;
- personalized Home;
- conversational and guided Study;
- connected Resources;
- editable AI-assisted Notes;
- source and adaptive Audio;
- fully configurable assessment generation;
- dynamic exam cards based on learner-selected format;
- MCQ, theory, coding, viva, teach-back, and mixed assessment support;
- Evaluation separated from generation;
- living Roadmaps;
- multi-goal Planner;
- automatic plan recovery;
- Revision;
- learning-focused Progress;
- Learner Model;
- persistent Memory with user controls;
- evidence and confidence;
- misconception tracking;
- prerequisite detection;
- recommendations;
- global search;
- in-app and email reminders;
- human-in-the-loop controls;
- cross-feature automation;
- orchestration;
- validation and reliability;
- external-resource / platform boundaries.

This is the **complete product scope**, not a statement that every capability must be implemented simultaneously.

The complete vision remains the target while implementation can proceed system by system.

---

# 36. Step 5 Conclusion

ARIA's scope can be summarized as:

> **One integrated, automated, adaptive learning environment for goal-driven learners.**

The learner controls what they want to achieve and how they want to be assessed. ARIA helps coordinate the surrounding learning workflow — resources, studying, notes, audio, assessment, evaluation, revision, roadmaps, planning, progress, and recommendations — around shared learner_concept_state.

The product is not differentiated by the existence of any one feature. Its defining behaviour is that these capabilities **work together**.

---

# 37. Next Phase 0 Step

**Step 6 — Build Stages / Scope Sequencing**

The complete product remains the target. Step 6 should not remove features from the vision; it should determine the order in which the systems can be implemented safely and logically.

This should identify:

- foundational systems that other features depend on;
- feature dependencies;
- implementation stages;
- which end-to-end learning loop should become functional first;
- how later systems attach without requiring architectural rewrites;
- checkpoints at which ARIA becomes usable during development.

The result will provide a development sequence before the final Phase 0 `VISION.md` is assembled.
---

## Next

Step 6 — Build Stages Scope Sequencing.
