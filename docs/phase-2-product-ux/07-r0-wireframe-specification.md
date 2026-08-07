# ARIA — Phase 2: Product & UX Design

## Step 7 — R0 Wireframe Specification

**Product:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 2 — Product & UX Design  
**Status:** Step 7 complete  
**Inputs:** Frozen Phase 1 PRD + Phase 2 Steps 1–6

---

# 1. Purpose

This document converts the R0 information architecture, user flows, Study/adaptation contract, assessment/evidence contract and recovery rules into low-fidelity structural wireframes.

These wireframes define:

- route-level screen structure;
- information hierarchy;
- primary and secondary actions;
- responsive behaviour;
- critical states;
- transitions between the core R0 surfaces.

They intentionally do **not** define final branding, colours, typography, illustration style or animation.

---

# 2. R0 Product Shell

Desktop conceptual shell:

```text
┌────────────────────────────────────────────────────────────────────┐
│ ARIA                                             Account / Profile │
├───────────────┬────────────────────────────────────────────────────┤
│               │                                                    │
│ Home          │                                                    │
│ Study         │                 Active route                       │
│ Resources     │                                                    │
│ Assessments   │                                                    │
│               │                                                    │
│────────────── │                                                    │
│ Current Goal  │                                                    │
│ DBMS          │                                                    │
│               │                                                    │
├───────────────┴────────────────────────────────────────────────────┤
│ Optional global status / offline / recovery region                │
└────────────────────────────────────────────────────────────────────┘
```

R0 keeps top-level navigation intentionally small. Roadmap, Planner, Notes, Audio and mature Progress surfaces belong to later releases.

---

# 3. Mobile Product Shell

```text
┌─────────────────────────────┐
│ ARIA                 ☰ / 👤 │
├─────────────────────────────┤
│                             │
│       Active screen         │
│                             │
│                             │
├─────────────────────────────┤
│ Home  Study  Test  Resources│
└─────────────────────────────┘
```

Exact mobile navigation pattern may become bottom navigation or a compact menu depending on implementation constraints, but core routes must remain quickly reachable.

---

# 4. Authentication — Sign In

```text
┌──────────────────────────────────────────┐
│                  ARIA                    │
│                                          │
│          Welcome back                    │
│                                          │
│ Email                                    │
│ [____________________________]           │
│                                          │
│ Password                                 │
│ [____________________________]           │
│                                          │
│ [ Sign in ]                              │
│                                          │
│ Don't have an account? Sign up           │
│                                          │
│ Error / auth status region               │
└──────────────────────────────────────────┘
```

Primary action: `Sign in`.

On session expiry, successful sign-in returns the learner to the authoritative resumable state rather than blindly restoring a stale page.

---

# 5. Authentication — Sign Up

```text
┌──────────────────────────────────────────┐
│                  ARIA                    │
│                                          │
│          Create your account             │
│                                          │
│ Name                                     │
│ [____________________________]           │
│ Email                                    │
│ [____________________________]           │
│ Password                                 │
│ [____________________________]           │
│                                          │
│ [ Create account ]                       │
│                                          │
│ Already have an account? Sign in         │
└──────────────────────────────────────────┘
```

Only account information required for R0 should be collected.

---

# 6. Initial Learning Context Setup

R0 is domain-constrained for validation, so setup is intentionally small.

```text
┌──────────────────────────────────────────────────────┐
│ Set up your learning context                         │
│                                                      │
│ R0 validation context                               │
│ Database Management Systems                         │
│                                                      │
│ What are you preparing for?                         │
│ [ Course / exam / placement context __________ ]    │
│                                                      │
│ Current focus (optional)                            │
│ [ Transactions / Serializability / ... ]            │
│                                                      │
│ [ Continue ]                                        │
└──────────────────────────────────────────────────────┘
```

This screen must not imply that R0 already supports every possible domain.

---

# 7. Home — First-Use Empty State

```text
┌──────────────────────────────────────────────────────────────────┐
│ Home                                                             │
│                                                                  │
│ DBMS                                                             │
│ Your learning workspace                                         │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ Start with your learning material                           │ │
│ │                                                              │ │
│ │ Add a PDF or paste text so ARIA can use your material       │ │
│ │ during Study.                                                │ │
│ │                                                              │ │
│ │ [ Add material ]                                            │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ Learning signal                                                 │
│ No formal evidence yet                                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

The empty Home does not invent progress charts.

---

# 8. Home — Active Learner

```text
┌──────────────────────────────────────────────────────────────────┐
│ Home                                                             │
│                                                                  │
│ DBMS                                      Material: 1 ready       │
│                                                                  │
│ ┌──────────────────────────────────┐ ┌──────────────────────────┐ │
│ │ Continue learning                │ │ Current learning signal  │ │
│ │                                  │ │                          │ │
│ │ Conflict Serializability         │ │ Conflict detection       │ │
│ │ Focused review ready             │ │ Worth reviewing          │ │
│ │                                  │ │                          │ │
│ │ [ Continue ]                     │ │ [ Why this? ]            │ │
│ └──────────────────────────────────┘ └──────────────────────────┘ │
│                                                                  │
│ Recent cycle                                                     │
│ Assessment → Focused Review → Targeted Check                     │
│ [ View cycle ]                                                   │
│                                                                  │
│ Quick actions                                                    │
│ [ Study ] [ Create assessment ] [ Resources ]                    │
└──────────────────────────────────────────────────────────────────┘
```

Home prioritizes the **next meaningful action**, not a dashboard full of vanity metrics.

---

# 9. Home — Recovery State

```text
┌──────────────────────────────────────────────────────────────────┐
│ Home                                                             │
│                                                                  │
│ Action needed                                                    │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ Assessment evaluation needs attention                       │ │
│ │                                                              │ │
│ │ Your answers are saved, but evaluation did not finish.      │ │
│ │ No learning signal was changed.                             │ │
│ │                                                              │ │
│ │ [ Try evaluation again ]                                    │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ Other actions                                                    │
│ [ Study ] [ Resources ]                                         │
└──────────────────────────────────────────────────────────────────┘
```

Recovery takes precedence over unrelated recommendations when a consequential stage is incomplete.

---

# 10. Resources — Empty

```text
┌──────────────────────────────────────────────────────────────────┐
│ Resources                                                        │
│                                                                  │
│ No resources yet                                                 │
│                                                                  │
│ Add study material so ARIA can ground Study responses.           │
│                                                                  │
│ [ Upload PDF ]    [ Paste text ]                                 │
└──────────────────────────────────────────────────────────────────┘
```

---

# 11. Resources — Add PDF

```text
┌──────────────────────────────────────────────────────────────────┐
│ Add PDF                                                          │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ Drop PDF here or choose a file                              │ │
│ │                                                              │ │
│ │ [ Choose PDF ]                                              │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ Supported type / size guidance                                  │
│                                                                  │
│ [ Cancel ]                                                      │
└──────────────────────────────────────────────────────────────────┘
```

Validation errors appear near the upload region.

---

# 12. Resources — Paste Text

```text
┌──────────────────────────────────────────────────────────────────┐
│ Add text                                                         │
│                                                                  │
│ Title                                                            │
│ [____________________________________________]                   │
│                                                                  │
│ Study text                                                       │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │                                                              │ │
│ │                                                              │ │
│ │                                                              │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ [ Add material ]                                                │
└──────────────────────────────────────────────────────────────────┘
```

---

# 13. Resources — Processing

```text
┌──────────────────────────────────────────────────────────────────┐
│ Resources                                                        │
│                                                                  │
│ DBMS Unit 4.pdf                                                  │
│ Processing…                                                      │
│ Preparing this material for Study.                              │
│                                                                  │
│ [ Return Home ]                                                  │
└──────────────────────────────────────────────────────────────────┘
```

Do not display fake percentage progress.

---

# 14. Resources — Ready List

```text
┌──────────────────────────────────────────────────────────────────┐
│ Resources                                      [ + Add material ]│
│                                                                  │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ DBMS Unit 4.pdf                                  Ready       │ │
│ │ PDF · added today                                           │ │
│ │ [ Use in Study ] [ More ]                                  │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ Serializability notes                            Ready       │ │
│ │ Pasted text                                                 │ │
│ │ [ Use in Study ] [ More ]                                  │ │
│ └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

# 15. Resources — Failed Item

```text
┌──────────────────────────────────────────────────────────────┐
│ DBMS Unit 4.pdf                                   Failed     │
│                                                              │
│ We couldn't prepare this PDF for Study.                     │
│                                                              │
│ [ Try processing again ] [ Replace ] [ Remove ]             │
└──────────────────────────────────────────────────────────────┘
```

A failed item must not look selectable as a ready grounding source.

---

# 16. Study — Baseline Empty Conversation

```text
┌──────────────────────────────────────────────────────────────────┐
│ Study                                                            │
│ DBMS / Serializability                  Using: DBMS Unit 4.pdf   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│                 What would you like to understand?               │
│                                                                  │
│ [ Explain serializability ]                                      │
│ [ Walk me through a schedule ]                                   │
│ [ Explain conflicts with an example ]                            │
│                                                                  │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│ Ask something…                                        [ Send ]   │
│                                                     [ Test me ]   │
└──────────────────────────────────────────────────────────────────┘
```

---

# 17. Study — Active Conversation

```text
┌──────────────────────────────────────────────────────────────────┐
│ Study                                                            │
│ DBMS / Serializability                  Using: DBMS Unit 4.pdf   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ YOU                                                              │
│ I don't understand conflict serializability.                     │
│                                                                  │
│ ARIA                                                             │
│ Let's break it into two ideas first...                           │
│                                                                  │
│ [ Based on: DBMS Unit 4.pdf · View source ]                      │
│                                                                  │
│ YOU                                                              │
│ Why does T1 before T2 matter?                                    │
│                                                                  │
│ ARIA                                                             │
│ Because the conflicting operations create an ordering edge...   │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│ Ask a follow-up…                                      [ Send ]   │
│                                                     [ Test me ]   │
└──────────────────────────────────────────────────────────────────┘
```

---

# 18. Study — Grounding Failure

```text
┌──────────────────────────────────────────────────────────────────┐
│ ARIA                                                             │
│                                                                  │
│ I couldn't retrieve the relevant part of your material right    │
│ now. I can retry, or explain the concept generally without      │
│ claiming it comes from your PDF.                                │
│                                                                  │
│ [ Retry with material ] [ Explain generally ] [ Resources ]     │
└──────────────────────────────────────────────────────────────────┘
```

---

# 19. Assessment Setup

```text
┌──────────────────────────────────────────────────────────────┐
│ Create assessment                                            │
│                                                              │
│ Topic                                                        │
│ [ Serializability                         ▼ ]                │
│                                                              │
│ Questions                                                    │
│ [ 5                                      ▼ ]                │
│                                                              │
│ Difficulty                                                   │
│ [ Medium                                 ▼ ]                │
│                                                              │
│ Timer                                                        │
│ [ Off                                    ▼ ]                │
│                                                              │
│ [ Generate assessment ]                                      │
└──────────────────────────────────────────────────────────────┘
```

---

# 20. Assessment Generation

```text
┌──────────────────────────────────────────────────────────────┐
│ Preparing your assessment…                                  │
│                                                              │
│ Serializability                                             │
│ 5 questions · Medium                                        │
│                                                              │
│ Creating and validating the questions.                      │
└──────────────────────────────────────────────────────────────┘
```

---

# 21. Assessment Start

```text
┌──────────────────────────────────────────────────────────────┐
│ Serializability Check                                       │
│                                                              │
│ 5 questions · Medium                                        │
│ No timer                                                     │
│                                                              │
│ Your submitted answers will be used as formal learning      │
│ evidence so ARIA can decide what to focus on next.          │
│                                                              │
│ [ Start ]                                                    │
└──────────────────────────────────────────────────────────────┘
```

---

# 22. Assessment Question

```text
┌──────────────────────────────────────────────────────────────────┐
│ Serializability               Question 2 of 5           08:42    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Which pair of operations conflicts?                              │
│                                                                  │
│ ○ R1(X), R2(X)                                                   │
│ ● W1(X), R2(X)                                                   │
│ ○ R1(X), W1(X)                                                   │
│ ○ R2(Y), W1(X)                                                   │
│                                                                  │
│                                                                  │
│ [ Previous ]                                      [ Next ]       │
│                                                                  │
│ Questions:  ✓1  ●2  3  4  5                                    │
└──────────────────────────────────────────────────────────────────┘
```

No correctness feedback appears before formal submission.

---

# 23. Submit Confirmation

```text
┌──────────────────────────────────────────────┐
│ Submit assessment?                           │
│                                              │
│ Answered: 4 of 5                             │
│ Unanswered: 1                                │
│                                              │
│ After submission, answers cannot be changed. │
│                                              │
│ [ Continue assessment ]                      │
│ [ Submit ]                                   │
└──────────────────────────────────────────────┘
```

---

# 24. Submission Uncertain

```text
┌──────────────────────────────────────────────────────────────┐
│ Checking your submission                                    │
│                                                              │
│ The connection dropped while submitting.                    │
│ We'll verify whether your answers were received before      │
│ asking you to try again.                                    │
└──────────────────────────────────────────────────────────────┘
```

---

# 25. Evaluation Pending

```text
┌──────────────────────────────────────────────────────────────┐
│ Answers saved                                               │
│                                                              │
│ Evaluating your assessment…                                 │
│                                                              │
│ Your learning signal will update only after valid           │
│ evaluation and evidence processing.                         │
└──────────────────────────────────────────────────────────────┘
```

---

# 26. Results — Overview

```text
┌──────────────────────────────────────────────────────────────────┐
│ Assessment complete                                              │
│                                                                  │
│ 3 / 5 correct                                                    │
│ Serializability                                                  │
│                                                                  │
│ [ Review answers ]                                               │
│                                                                  │
│ Learning signals                                                 │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ Conflict detection                                          │ │
│ │ Worth reviewing                                             │ │
│ │                                                              │ │
│ │ Two separate questions showed difficulty identifying       │ │
│ │ conflicting operations.                                     │ │
│ │                                                              │ │
│ │ [ Why this? ] [ Start focused review ]                      │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ Precedence graph cycles                                     │ │
│ │ Still building confidence                                  │ │
│ │ [ Why this? ]                                              │ │
│ └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

Score and learner signal remain visually distinct.

---

# 27. Evidence Detail Drawer / Panel

```text
┌──────────────────────────────────────────────────────┐
│ Why ARIA shows "Worth reviewing"              [ × ] │
│                                                      │
│ Conflict detection                                   │
│                                                      │
│ Assessment                                           │
│ Question 2 — Incorrect                               │
│                                                      │
│ Assessment / distinct opportunity                    │
│ Question 1 — Incorrect                               │
│                                                      │
│ ARIA requires more than one aligned observation      │
│ before showing a strong review signal.               │
│                                                      │
│ [ Review answers ]                                   │
└──────────────────────────────────────────────────────┘
```

Desktop may use a side panel; mobile should use a sheet/full-screen detail view.

---

# 28. Answer Review

```text
┌──────────────────────────────────────────────────────────────────┐
│ Review answers                                                   │
│                                                                  │
│ Question 2                                      Incorrect         │
│                                                                  │
│ Which pair conflicts?                                            │
│                                                                  │
│ Your answer                                                     │
│ R1(X), R2(X)                                                     │
│                                                                  │
│ Correct answer                                                   │
│ W1(X), R2(X)                                                     │
│                                                                  │
│ Why                                                              │
│ Two reads do not conflict. At least one operation must be a     │
│ write.                                                           │
│                                                                  │
│ Concept: Conflict detection                                     │
│                                                                  │
│ [ This result looks wrong ]                                     │
└──────────────────────────────────────────────────────────────────┘
```

---

# 29. Challenge Result

```text
┌──────────────────────────────────────────────────────┐
│ Challenge this result?                               │
│                                                      │
│ ARIA will recheck the evaluation and concept         │
│ attribution for this answer.                         │
│                                                      │
│ Optional note                                        │
│ [_______________________________________________]    │
│                                                      │
│ [ Cancel ] [ Request recheck ]                       │
└──────────────────────────────────────────────────────┘
```

A failed recheck leaves the original result unchanged but may show that review is pending/failed.

---

# 30. Correction Propagation

```text
┌──────────────────────────────────────────────────────────────┐
│ Result corrected                                             │
│                                                              │
│ Updating your learning signal…                              │
│                                                              │
│ ✓ Evaluation corrected                                      │
│ ✓ Evidence updated                                          │
│ • Learning signal updating                                  │
│ • Adaptation will be reconsidered                           │
└──────────────────────────────────────────────────────────────┘
```

The progress indicators represent real stages, not fabricated percentage progress.

---

# 31. Adaptation Explanation

```text
┌──────────────────────────────────────────────────────────────────┐
│ Focused review                                                   │
│ Conflict detection                                              │
│                                                                  │
│ What I noticed                                                   │
│ You missed two different questions that required identifying    │
│ conflicts between transactions.                                 │
│                                                                  │
│ Current signal                                                   │
│ Worth reviewing                                                  │
│                                                                  │
│ What I'm changing                                                │
│ Instead of another definition, we'll work through one schedule  │
│ operation by operation.                                         │
│                                                                  │
│ After this                                                       │
│ You can take a new targeted check.                              │
│                                                                  │
│ [ Start focused review ]                                        │
│ [ Review evidence ] [ Continue normal Study ]                   │
└──────────────────────────────────────────────────────────────────┘
```

---

# 32. Adapted Study

```text
┌──────────────────────────────────────────────────────────────────┐
│ Focused Review                                                   │
│ DBMS / Conflict Serializability                                 │
│ Based on your latest assessment                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Step 1 — Forget the graph for a moment                          │
│                                                                  │
│ For two operations to conflict, check three conditions:         │
│ 1. different transactions                                      │
│ 2. same data item                                               │
│ 3. at least one is a write                                      │
│                                                                  │
│ Let's mark only the conflicts in this schedule.                 │
│                                                                  │
│ R1(X) W1(X) R2(X) W2(X)                                        │
│                                                                  │
│ [ Show a hint ]                                                 │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│ Ask something…                                       [ Send ]   │
│                                                                  │
│ [ Keep studying ]                [ Take targeted check ]         │
└──────────────────────────────────────────────────────────────────┘
```

The changed teaching strategy is visible, not merely claimed.

---

# 33. Insufficient-Evidence State

```text
┌──────────────────────────────────────────────────────────────────┐
│ Conflict detection                                              │
│ Still building confidence                                      │
│                                                                  │
│ I only have one usable result on this concept, so I don't have  │
│ enough evidence for a strong Study change yet.                  │
│                                                                  │
│ [ Take focused check ] [ Continue Study ]                       │
└──────────────────────────────────────────────────────────────────┘
```

---

# 34. Targeted Reassessment Start

```text
┌──────────────────────────────────────────────────────────────┐
│ Targeted check                                               │
│ Conflict detection                                          │
│                                                              │
│ 3 new questions · Medium                                    │
│                                                              │
│ These are new questions on the same concept so ARIA can     │
│ collect another signal rather than test whether you remember │
│ the previous answers.                                       │
│                                                              │
│ [ Start check ]                                             │
└──────────────────────────────────────────────────────────────┘
```

---

# 35. Targeted Reassessment Results

```text
┌──────────────────────────────────────────────────────────────────┐
│ Targeted check complete                                         │
│                                                                  │
│ Conflict detection                                              │
│                                                                  │
│ Previous signal                                                 │
│ Worth reviewing                                                 │
│                                                                  │
│ Current signal                                                  │
│ Still building confidence                                      │
│                                                                  │
│ Your latest check added new correct evidence. ARIA updated the  │
│ current signal accordingly.                                    │
│                                                                  │
│ [ View learning cycle ] [ Continue studying ]                   │
└──────────────────────────────────────────────────────────────────┘
```

No causal claim is made.

---

# 36. Learning Cycle Summary

```text
┌──────────────────────────────────────────────────────────────────┐
│ Learning cycle                                                   │
│ Conflict Serializability                                        │
│                                                                  │
│ ① Initial assessment                                            │
│    Repeated difficulty identifying conflicts                    │
│           │                                                      │
│           ▼                                                      │
│ ② ARIA changed Study                                            │
│    Worked schedule + more scaffolding                           │
│           │                                                      │
│           ▼                                                      │
│ ③ Targeted reassessment                                         │
│    New independent evidence collected                           │
│           │                                                      │
│           ▼                                                      │
│ ④ Current signal                                                │
│    Still building confidence                                   │
│                                                                  │
│ [ Review evidence ] [ Continue Study ]                          │
└──────────────────────────────────────────────────────────────────┘
```

This is the most direct learner-facing representation of the R0 thesis.

---

# 37. Evaluation Failure

```text
┌──────────────────────────────────────────────────────────────┐
│ Your answers are safe                                       │
│                                                              │
│ We couldn't evaluate this assessment right now.             │
│ No learning evidence or learning-signal change has been     │
│ created from this attempt yet.                              │
│                                                              │
│ [ Try evaluation again ]                                    │
│ [ Return Home ]                                             │
└──────────────────────────────────────────────────────────────┘
```

---

# 38. Learner-State Update Pending

```text
┌──────────────────────────────────────────────────────────────┐
│ Assessment scored                                           │
│ 3 / 5 correct                                               │
│                                                              │
│ Learning signal update pending                              │
│                                                              │
│ Your evidence is saved, but ARIA hasn't finished updating   │
│ the current concept signal.                                 │
│                                                              │
│ [ Try update again ] [ Review answers ]                     │
└──────────────────────────────────────────────────────────────┘
```

The UI does not pretend an older state includes the new evidence.

---

# 39. Adapted Study Generation Failure

```text
┌──────────────────────────────────────────────────────────────┐
│ Focused review couldn't be generated                        │
│                                                              │
│ Your assessment, evidence and current learning signal are   │
│ safely preserved.                                           │
│                                                              │
│ [ Try focused review again ]                                │
│ [ Review evidence ]                                         │
│ [ Continue normal Study ]                                   │
└──────────────────────────────────────────────────────────────┘
```

---

# 40. Offline Banner

```text
┌──────────────────────────────────────────────────────────────────┐
│ You're offline — some actions require a connection.             │
└──────────────────────────────────────────────────────────────────┘
```

The banner should not cover primary controls.

---

# 41. Session Expired

```text
┌──────────────────────────────────────────────┐
│ Your session expired                         │
│                                              │
│ Sign in again to continue.                   │
│                                              │
│ We'll restore the latest safely saved state. │
│                                              │
│ [ Sign in ]                                  │
└──────────────────────────────────────────────┘
```

Only show the preservation line when implementation guarantees it.

---

# 42. Unauthorized Item

```text
┌──────────────────────────────────────────────┐
│ You don't have access to this item.          │
│                                              │
│ [ Return to your learning workspace ]        │
└──────────────────────────────────────────────┘
```

No private object metadata is leaked.

---

# 43. Account / Profile — R0

```text
┌──────────────────────────────────────────────────────────────┐
│ Account                                                      │
│                                                              │
│ Name                                                         │
│ Divya                                                        │
│                                                              │
│ Email                                                        │
│ user@example.com                                             │
│                                                              │
│ Learning context                                             │
│ Database Management Systems                                  │
│                                                              │
│ [ Sign out ]                                                 │
└──────────────────────────────────────────────────────────────┘
```

R0 Account is intentionally minimal. It is not a settings center for future features.

---

# 44. Desktop Responsive Hierarchy

At larger widths:

```text
Navigation rail
     +
Primary content column
     +
Optional contextual side panel
```

Side panels are appropriate for:

- evidence detail;
- source detail;
- question overview;
- contextual status.

The primary learning/task area must remain dominant.

---

# 45. Tablet Hierarchy

At intermediate widths:

- navigation may collapse;
- contextual panels become drawers;
- Study remains a single dominant column;
- results cards stack earlier than desktop;
- assessment controls remain large enough for touch.

---

# 46. Mobile Hierarchy

Mobile prioritizes one task at a time.

Example Study:

```text
Context header
Focused-review banner (if any)
Conversation
Source/evidence details via sheet
Input
Primary next action
```

Example Results:

```text
Score
Concept signal
Next action
Why-this disclosure
Answer review
```

Do not reproduce desktop side-by-side layouts at tiny widths.

---

# 47. Navigation Priority

R0 primary navigation:

```text
Home
Study
Assessments
Resources
Account
```

Possible mobile shortcut label:

`Test` may represent `Assessments` if clearer in the constrained navigation surface.

Future vision features must not appear as disabled navigation clutter in R0.

---

# 48. Primary CTA Rules

Each screen should normally have one dominant next action.

Examples:

| Screen | Primary CTA |
|---|---|
| Home empty | Add material |
| Resource ready | Use in Study |
| Study | Send / contextual Test me |
| Assessment setup | Generate assessment |
| Assessment start | Start |
| Question final step | Submit |
| Results with justified adaptation | Start focused review |
| Adapted Study | Continue learning / targeted check when ready |
| Evaluation failure | Try evaluation again |
| Cycle summary | Continue Study |

Secondary actions should not visually compete unnecessarily.

---

# 49. Persistent Context

Where useful, route headers should preserve:

```text
Learning context
Current concept
Grounding/resource status
Current workflow mode
```

Example:

```text
DBMS / Conflict Serializability
Focused Review · Based on latest assessment
```

This reduces the feeling of moving among unrelated mini-apps.

---

# 50. Evidence Visibility Rule

Evidence must be available without permanently occupying the main learning surface.

Pattern:

```text
Current signal
Short basis
[ Why this? ]
      ↓
Drawer / panel / detail screen
```

This balances transparency with cognitive load.

---

# 51. Grounding Visibility Rule

Study responses grounded in learner material should expose source context through compact affordances:

```text
Using: DBMS Unit 4.pdf
```

and/or

```text
Based on: DBMS Unit 4.pdf · View source
```

General responses should not inherit the grounded badge.

---

# 52. Formal Evidence Boundary in UI

The interface must visually distinguish:

```text
Study practice
```

from:

```text
Formal assessment
Your submitted answers affect ARIA's learning signal
```

The learner should know when their answer becomes formal evidence.

---

# 53. State Language Consistency

Across Home, Results, Study and Cycle Summary, use the same learner-facing vocabulary:

```text
Not enough evidence yet
Still building confidence
Worth reviewing
Current results look solid
```

Do not alternate between these and stronger unsupported labels such as `Weak`, `Mastered`, `Bad`, `Expert`.

---

# 54. Wireframe Accessibility Rules

All final UI implementations derived from these wireframes must preserve:

- semantic headings and landmarks;
- keyboard navigation;
- visible focus;
- labels for inputs and answer controls;
- status/errors not communicated only by colour;
- readable line lengths;
- touch-friendly targets;
- accessible modal/drawer focus management;
- screen-reader-friendly asynchronous status where practical;
- no essential hover-only interactions.

---

# 55. Wireframe State Coverage Matrix

| Surface | Empty | Loading/Processing | Ready | Error/Recovery | Historical/Read-only |
|---|---:|---:|---:|---:|---:|
| Home | ✓ | ✓ | ✓ | ✓ | — |
| Resources | ✓ | ✓ | ✓ | ✓ | — |
| Study | ✓ | ✓ | ✓ | ✓ | ✓ conversation history |
| Assessment setup | ✓ | ✓ generation | ✓ | ✓ | — |
| Assessment attempt | — | ✓ load/save | ✓ | ✓ | ✓ submitted |
| Results | — | ✓ evaluation/state | ✓ | ✓ | ✓ |
| Evidence detail | ✓ | ✓ | ✓ | ✓ | ✓ |
| Adaptation | ✓/no adaptation | ✓ | ✓ | ✓ | ✓ |
| Reassessment | — | ✓ | ✓ | ✓ | ✓ |
| Cycle summary | — | ✓ | ✓ | ✓ | ✓ |

---

# 56. R0 Happy-Path Screen Sequence

```text
Sign up / Sign in
      ↓
Learning Context Setup
      ↓
Home
      ↓
Resources
      ↓
Resource Processing
      ↓
Study
      ↓
Assessment Setup
      ↓
Assessment
      ↓
Results
      ↓
Evidence / Learner Signal
      ↓
Adaptation Explanation
      ↓
Adapted Study
      ↓
Targeted Reassessment
      ↓
Reassessment Results
      ↓
Learning Cycle Summary
      ↓
Continue Study
```

---

# 57. R0 Validation Demo Sequence

For Gate A/demo purposes, the shortest convincing product walkthrough is:

```text
1. Open a ready DBMS learning context
2. Study Conflict Serializability
3. Take formal assessment
4. Produce repeated aligned difficulty evidence
5. Show "Worth reviewing" with inspectable evidence
6. Start focused review
7. Show materially changed teaching strategy
8. Take new targeted reassessment
9. Produce new independent evidence
10. Show updated learner signal
11. Show complete learning-cycle summary
```

This sequence demonstrates the thesis without requiring Roadmap, Planner, Notes, Audio or mature Progress.

---

# 58. Non-Happy Demo Sequence

Gate A should also demonstrate at least one consequential recovery path:

```text
Submit assessment
      ↓
Evaluation fails
      ↓
Answers remain saved
No evidence/state change
      ↓
Retry evaluation
      ↓
Evaluation succeeds once
      ↓
Evidence/state pipeline continues
```

This proves that adaptive behaviour is not built on fragile hidden side effects.

---

# 59. Component Candidates Revealed by Wireframes

Without freezing a frontend library, repeated structures suggest reusable components such as:

```text
AppShell
RouteHeader
ContextBadge
ResourceCard
StatusBanner
EmptyState
ErrorState
ConversationMessage
SourceDisclosure
AssessmentConfigForm
QuestionCard
QuestionNavigator
SubmissionDialog
ScoreSummary
LearnerSignalCard
EvidenceDrawer
AnswerReviewCard
AdaptationCard
CycleTimeline
RecoveryCard
```

Formal component/API design belongs to implementation/system design, but the UX should avoid unnecessary one-off patterns.

---

# 60. Visual Design Deferred

Step 7 intentionally does not choose:

- primary colour;
- dark/light theme;
- font family;
- border radius system;
- shadows;
- gradients;
- icon family;
- logo treatment;
- illustration style;
- animation style.

Those choices should serve the validated structure rather than reshape product scope.

---

# 61. Anti-Patterns

Do not turn these wireframes into:

### Dashboard bloat

Adding charts/cards because Home looks visually empty.

### Future-feature placeholders

Showing Planner, Notes, Roadmap or Audio as disabled R0 navigation.

### ChatGPT clone layout

Making Study a generic blank chat screen with no learning context, grounding or adaptation visibility.

### Quiz-app isolation

Making Assessment feel disconnected from Study/evidence/adaptation.

### Hidden learner model

Changing Study while giving the learner no way to inspect why.

### Learner-model overload

Showing every evidence record and internal state on every screen.

### Desktop squeezed onto mobile

Preserving sidebars/panels when the mobile task needs one-column focus.

### Visual polish before structural validation

Spending Phase 2 on gradients and animations before confirming the learning loop is understandable.

---

# 62. Acceptance Criteria

Step 7 is complete only if the wireframes:

- cover the complete R0 happy path;
- cover authentication and initial setup;
- represent Home as next-action oriented;
- include resource upload/text/processing/failure states;
- distinguish baseline and adapted Study;
- expose grounding honestly;
- show formal assessment setup, attempt and submission;
- separate score from learner signal;
- make evidence inspectable;
- include challenge/correction propagation;
- show adaptation rationale before adapted Study;
- show targeted reassessment and cycle comparison;
- include consequential recovery states;
- define desktop/tablet/mobile hierarchy;
- maintain R0 scope boundaries;
- preserve accessibility requirements;
- provide a Gate A demo path.

---

# 63. Traceability

| Phase 2 input | Wireframe result |
|---|---|
| IA / route model | Product shell + navigation |
| Core user journeys | Happy-path sequence |
| Detailed state transitions | Processing/recovery screens |
| Study/adaptation UX | Baseline + adapted Study |
| Assessment/results/state UX | Assessment + Results + Evidence |
| Error/recovery UX | Recovery screens and stale-state rules |
| Gate A validation | Demo + failure-recovery sequence |
| R0 scope principle | No future-feature navigation bloat |

---

# 64. Scope Guardrail

This specification freezes the **structural UX contract**, not the final visual system.

It does not freeze:

- frontend framework;
- component library;
- exact breakpoint pixels;
- exact spacing tokens;
- final visual identity;
- final microcopy for every state;
- animation/motion;
- backend architecture;
- database/API design.

---

# 65. Step 7 Completion

**Phase 2 — Step 7 is complete.**

ARIA R0 now has low-fidelity structural wireframes covering the full adaptive-learning loop and its major recovery states.

Next:

# Step 8 — UX Consistency Review & Phase 2 Freeze

Step 8 will review all Phase 2 documents together against the frozen PRD and corrected VISION, identify contradictions, remove accidental scope creep, verify R0 route/state coverage, confirm Gate A/B usability requirements and produce the final Phase 2 handoff contract for Phase 3 system architecture.
---

## Next

Step 8 — UX Consistency Review & Phase 2 Freeze.
