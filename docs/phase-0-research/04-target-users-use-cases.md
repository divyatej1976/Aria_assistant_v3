# ARIA — Phase 0 Research

## 04 — Target Users & Use Cases

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 0 — Research  
**Status:** Step 4 — Complete  
**Research basis:** Phase 0 market/user research, competitor analysis, product vision, and differentiation work

---

# 1. Step 4 Decisions

ARIA's target audience is best defined by **learning intent**, not by age, degree, profession, or subject.

Three product decisions are locked for this step:

### Primary audience

> **Goal-driven learners — people actively preparing for or trying to learn something.**

### Optimize for

> **Genuine progress toward the learner's goal, rather than content consumption or engagement alone.**

### First product priority

> **Reduce the learner's manual coordination burden while supporting effective learning by connecting and adapting the learning workflow around them.**

---

# 2. Primary User Definition

ARIA's primary user is:

> **A learner actively working toward one or more learning goals who wants help understanding what to learn, learning it effectively, evaluating their understanding, staying organized, revising appropriately, and adapting their plan over time without manually coordinating multiple disconnected tools.**

ARIA is therefore not fundamentally a product only for university students.

The same underlying learning system can support someone preparing for a university exam, certification, interview, competitive examination, professional skill, technical field, or independent subject of interest.

---

# 3. Goal-Driven Learners

The common characteristic of ARIA's users is not what they study. It is that they have a learning objective.

Examples include:

```text
Goal-Driven Learner
│
├── Academic goal
│   └── "Prepare for my DBMS exam"
│
├── Certification goal
│   └── "Pass an AWS certification"
│
├── Career goal
│   └── "Prepare for a technical interview"
│
├── Skill goal
│   └── "Learn Agentic AI"
│
├── Competitive-exam goal
│   └── "Prepare for a banking examination"
│
└── Independent-learning goal
    └── "Learn economics properly"
```

ARIA should remain **domain-independent**. Subjects such as DSA, AWS, medicine, finance, mathematics, or AI must not be hardcoded into the core product experience.

---

# 4. Learning Situations, Not Permanent Personas

ARIA should not permanently classify a user as an "exam learner" or "skill learner."

One person may simultaneously be:

- preparing for a university exam;
- learning a technical skill over several months;
- preparing for a certification;
- revising something at the last minute.

Therefore ARIA should adapt to the **current goal and situation**.

Major learning situations include:

### Structured learning

The learner knows what they want to learn but needs a path.

### Exam preparation

The learner has defined material, scope, and often a deadline.

### Long-term skill development

The learner is developing competence over weeks or months.

### Certification preparation

The learner is working toward an external syllabus or examination objective.

### Resource-heavy learning

The learner has PDFs, videos, notes, courses, websites, or books distributed across sources.

### Last-minute revision

The learner has limited time and needs high-priority review.

### Multi-goal learning

The learner is pursuing several goals simultaneously.

### Recovery after falling behind

The learner has missed planned work and needs the learning plan reorganized.

---

# 5. Jobs To Be Done

ARIA's product should be designed around the jobs learners are trying to accomplish rather than around isolated feature requests.

## JTBD 1 — Starting something new

> **When I decide to learn something, help me understand what I need to learn and create a realistic path forward.**

## JTBD 2 — Understanding difficult material

> **When I do not understand something, teach it in a way that helps me genuinely understand rather than simply giving me an answer.**

## JTBD 3 — Managing resources

> **When my learning material is spread across PDFs, videos, websites, notes, courses, and other sources, keep those resources connected to what I am trying to learn.**

## JTBD 4 — Knowing whether I understand

> **When I think I have learned something, test me and show what I actually understand, what I only partially understand, and what I misunderstand.**

## JTBD 5 — Remembering what I learn

> **When I have studied something, help me revisit it at useful times so that learning does not disappear after the first session.**

## JTBD 6 — Preparing for an assessment

> **When an exam or assessment is approaching, help me prioritize the material that matters most based on my remaining time and current knowledge.**

## JTBD 7 — Recovering after missed work

> **When I fall behind, help me recover by reorganizing the plan instead of forcing me to manually rebuild everything.**

## JTBD 8 — Continuing after time away

> **When I return after days or weeks, remember where I was and help me continue without reconstructing my learning context.**

## JTBD 9 — Managing multiple goals

> **When I am learning several things at once, help me balance them according to deadlines, priorities, progress, and available time.**

## JTBD 10 — Understanding ARIA's personalization

> **When ARIA changes my plan or decides that I am weak in something, let me understand why and correct the system when necessary.**

---

# 6. Core Use Case — Learn a New Skill

### Scenario

The learner says:

> "I want to learn Agentic AI."

### Intended flow

```text
Learning goal
     ↓
ARIA identifies expected knowledge / prerequisites
     ↓
Existing learner knowledge considered
     ↓
Personalized roadmap created
     ↓
Resources attached or recommended
     ↓
Planner creates actionable learning sessions
     ↓
Learner studies
     ↓
Study interactions create learning evidence
     ↓
Assessments test understanding
     ↓
Weaknesses / misconceptions detected
     ↓
Learner model updates
     ↓
Roadmap + planner + revision adapt
     ↓
Learning continues
```

### Important behaviour

The roadmap is not treated as a static checklist. Evidence gathered during learning should be capable of changing what happens next.

---

# 7. Core Use Case — Prepare for an Exam

### Scenario

The learner has a DBMS exam in one week.

They provide some combination of:

- syllabus;
- lecturer notes;
- textbook chapters;
- previous examination papers;
- personal notes;
- other resources.

### Intended flow

```text
Exam goal + deadline
       ↓
Scope / syllabus mapped
       ↓
Resources connected
       ↓
Current understanding assessed
       ↓
Knowledge gaps identified
       ↓
7-day preparation plan
       ↓
Study + retrieval
       ↓
Practice / mock exam
       ↓
Evaluation
       ↓
Weak areas identified
       ↓
Remaining plan adapts
       ↓
Final revision
       ↓
Exam
```

### Product implication

ARIA's exam preparation should connect planning, study, resources, assessment, revision, and progress rather than treating them as separate workflows.

---

# 8. Core Use Case — Last-Minute Adaptive Revision

### Scenario

The learner has approximately 15 minutes before an exam and cannot perform a full study session.

They say:

> "ARIA, revise me for my exam."

ARIA already has access to relevant learning state such as:

- exam scope;
- completed topics;
- recent assessment evidence;
- weak concepts;
- recurring mistakes;
- previous revision;
- available time.

### Possible revision structure

```text
15-minute revision
│
├── Essential concepts
├── High-risk weak areas
├── Rapid recall questions
├── Recurring misconceptions
└── Final high-yield review
```

The experience may support audio so the learner can revise when reading is inconvenient.

### Product implication

ARIA's audio direction should not be limited to generic document-to-audio conversion. Learning state can make revision audio adaptive and goal-aware.

---

# 9. Core Use Case — Learner Falls Behind

### Scenario

Original plan:

```text
Monday     Topic A
Tuesday    Topic B
Wednesday  Topic C
Thursday   Revision
Friday     Assessment
```

The learner misses Monday and Tuesday.

### Weak product behaviour

```text
OVERDUE: Topic A
OVERDUE: Topic B
```

This transfers the planning problem back to the learner.

### Intended ARIA behaviour

ARIA considers:

- remaining time;
- prerequisites;
- topic importance;
- existing knowledge;
- assessment deadline;
- available study time.

It proposes a recovery plan.

Example:

```text
Wednesday  Topic A + essential Topic B
Thursday   Topic C + targeted revision
Friday     Rapid retrieval / assessment preparation
```

Important changes should be explainable and support user approval or modification where appropriate.

---

# 10. Core Use Case — Test Whether I Actually Understand

### Scenario

The learner says:

> "I think I understand DBMS. Test me properly."

ARIA may combine multiple forms of evidence:

- conceptual questions;
- application questions;
- short answers;
- teach-back;
- timed assessment where useful;
- retrieval of previously weak concepts.

### Result

Instead of only:

```text
Score: 78%
```

ARIA should aim for something closer to:

```text
Normalization       Strong
SQL                 Strong
Transactions        Moderate
Indexing            Weak

Recurring misconception:
Clustered vs non-clustered indexes
```

This evidence then becomes useful elsewhere in ARIA.

---

# 11. Core Use Case — Teach ARIA

### Scenario

The learner wants to verify whether they can explain a topic from memory.

ARIA asks:

> "Explain gradient descent to me as though I am a beginner."

ARIA evaluates coverage rather than immediately teaching.

Example:

```text
Purpose             ✓
Gradient            ✓
Learning rate       ✓
Update rule         ✓
Convergence         Partial
Local minima        Missing
```

ARIA then focuses teaching or questioning on the missing pieces.

### Product implication

ARIA should support active learning and productive struggle, not only answer generation.

---

# 12. Core Use Case — Oral / Viva Preparation

### Scenario

The learner needs conversational assessment rather than a written quiz.

ARIA asks a question, evaluates the answer, and follows with deeper questions based on the response.

Example:

```text
ARIA: What is deadlock?
Learner: [answer]

ARIA: Why are all four Coffman conditions necessary?
Learner: [answer]

ARIA: What changes if mutual exclusion is removed?
```

The final evaluation may summarize conceptual knowledge, reasoning, terminology, and application ability.

This can support viva preparation, interviews, oral revision, and other conversational assessments.

---

# 13. Core Use Case — Learn From Personal Resources

### Scenario

A learner has:

```text
PDF notes
YouTube playlist
Documentation
Course
Personal notes
Articles
```

Instead of treating these as unrelated bookmarks, ARIA associates them with goals, roadmap topics, or concepts.

The learner can study from relevant resources, generate notes, create assessments, and later revisit the material through revision.

Where technically possible, ARIA should preserve source provenance so the learner can distinguish information grounded in supplied material from additional model knowledge.

---

# 14. Core Use Case — Multiple Simultaneous Goals

### Scenario

The learner has:

```text
Goal 1 — University DBMS exam
Deadline: Friday

Goal 2 — Learn Agentic AI
Long-term

Goal 3 — Cloud certification
Deadline: later
```

ARIA should not treat these as three completely isolated calendars.

As the DBMS exam approaches, the planner may temporarily prioritize it.

After the exam, available learning capacity can shift back toward the long-term goals.

### Product implication

ARIA needs a learner-level planning layer above individual roadmaps.

---

# 15. Core Use Case — Continue After Time Away

### Scenario

The learner stops using ARIA for two weeks.

When they return, they should not need to remember:

- which roadmap step they reached;
- what they struggled with;
- which resources they were using;
- what revisions were due;
- what the previous plan looked like.

ARIA should reconstruct a useful continuation state and propose what to do next.

This is one of the reasons persistent learner state matters.

---

# 16. Core Use Case — Correct ARIA

### Scenario

ARIA concludes:

> "You appear to struggle with recursion."

The learner believes the actual problem is backtracking.

The system should eventually support interactions such as:

```text
Why does ARIA think this?
Correct
Forget
```

The learner can inspect the evidence and correct important personalization errors.

### Product implication

Human-in-the-loop behaviour is part of ARIA's product design, not only a backend reliability mechanism.

---

# 17. Secondary User Situations

ARIA's architecture may eventually support additional learner groups without changing its fundamental model.

Examples include:

### Career transition learners

People learning a new professional field over several months.

### Interview preparation

Learners combining topic roadmaps, practice, revision, and oral questioning.

### Independent lifelong learners

People learning without an external exam or certification.

### Research-heavy learners

People learning a topic through papers, articles, notes, and source-grounded discussion.

These remain compatible with the goal-driven learner model.

---

# 18. Users ARIA Is Not Initially Optimized For

The product vision should remain broad without becoming undefined.

ARIA is not initially designed primarily for:

### Young children

This introduces substantially different safety, parental-control, pedagogy, and UX requirements.

### Teachers managing classrooms

Teacher dashboards, grading administration, attendance, and class management move toward LMS territory.

### Schools or universities administering courses

ARIA is currently learner-centric rather than institution-centric.

### Corporate learning administrators

Enterprise training introduces different buyers, reporting requirements, permissions, and integrations.

### Users seeking assignment completion rather than learning

ARIA should support understanding and productive struggle rather than optimize for replacing the learner's intellectual work.

These areas may be reconsidered later, but they should not distort the initial product architecture.

---

# 19. What ARIA Should Optimize

ARIA should not primarily optimize for:

- number of messages sent;
- number of notes generated;
- PDFs uploaded;
- time spent inside the app;
- artificial streak maintenance;
- raw content consumption.

These may provide useful secondary signals but are not the product objective.

ARIA should optimize toward **meaningful progress toward a learning goal**.

Potential future indicators include:

- roadmap progress backed by evidence;
- improvement across assessments;
- retention after time intervals;
- reduction in recurring misconceptions;
- prerequisite gaps resolved;
- goal milestones completed;
- successful plan recovery;
- improved exam readiness where measurable.

ARIA should avoid pretending that any single metric perfectly measures learning.

---

# 20. Automation Principle

The defining product experience is:

> **The learner should spend more effort learning and less effort managing the machinery around learning.**

Today the learner often acts as the orchestrator:

```text
AI tutor
   ↕ manual coordination
Notes
   ↕ manual coordination
Calendar
   ↕ manual coordination
Flashcards
   ↕ manual coordination
Resources
   ↕ manual coordination
Assessments
```

ARIA's intended model is:

```text
                   Learner
                      ↓
                    ARIA
                      ↓
              Shared learner state
                      ↓
     ┌────────────────┼────────────────┐
     ↓                ↓                ↓
   Study           Roadmap          Planner
     ↓                ↓                ↓
   Notes          Resources         Revision
     ↓                ↓                ↓
   Audio           Exams           Progress
     └────────────────┼────────────────┘
                      ↓
                  Evidence
                      ↓
                Learner Model
                      ↓
                  Adaptation
```

---

# 21. Design Implications

The target-user work produces several requirements for later phases.

### ARIA must support multiple goals

A single learner cannot be assumed to have one subject or one deadline.

### Onboarding must remain lightweight

ARIA should not attempt to learn everything about a user before they have used the product. Personalization should improve through actual interaction and evidence.

### Subjects must not be hardcoded

Resources, roadmaps, dashboards, and recommendations must be generated from the learner's goals and state.

### The planner must operate across goals

Planning cannot live entirely inside an individual roadmap.

### Learning state must persist across sessions

Returning users should be able to continue rather than reconstruct context.

### Assessment results must be reusable

Evaluation data should be capable of influencing roadmap, revision, progress, recommendations, and future study.

### Automation requires human control

Significant changes should be inspectable and correctable.

### Audio must be learning-aware

Audio should eventually support personalized revision based on learning state, not only static source conversion.

### External resources should remain first-class

ARIA should coordinate specialist learning platforms rather than unnecessarily rebuild all of them.

---

# 22. Primary End-to-End Journey

Across different user types, the fundamental ARIA journey remains:

```text
                 I WANT TO ACHIEVE X
                          ↓
                   Define the goal
                          ↓
              Understand starting state
                          ↓
                       Roadmap
                          ↓
                        Plan
                          ↓
                       Learn
                          ↓
                 Resources / Notes
                          ↓
                 Practice / Retrieve
                          ↓
                       Assess
                          ↓
                      Evaluate
                          ↓
                       Evidence
                          ↓
                   Learner Model
                          ↓
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
       Roadmap          Planner          Study
       adapts           adapts           adapts
          ↓               ↓               ↓
          └────────── Revision ───────────┘
                          ↓
                     Re-assess
                          ↓
                          ↺
                          ↓
                     GOAL PROGRESS
```

The exact interface changes with the learner's situation. The underlying learning loop remains consistent.

---

# 23. Step 4 Conclusion

ARIA should not be defined as an application for one demographic or one subject.

Its primary audience is:

> **Goal-driven learners.**

Its optimization target is:

> **Meaningful progress toward the learner's goal.**

Its first product priority is:

> **Reduce the manual coordination burden by connecting and adapting the learning workflow around the learner.**

This user definition is broad enough to support ARIA's long-term Learning OS vision while specific enough to guide product decisions: the user must be actively trying to learn or prepare for something, and ARIA exists to help that learning journey function as one connected system.

---

# 24. Next Phase 0 Step

**Step 5 — Complete Feature Scope**

The next task is to turn the vision and use cases into a structured product feature map.

Step 5 should define:

- every major user-facing system;
- capabilities inside each system;
- cross-feature automation behaviours;
- shared intelligence/services;
- dependencies between features;
- what belongs in the complete ARIA product versus what is outside scope.

This becomes the bridge between product research and the later PRD.