# ARIA — Phase 0 Research

## 01 — Market & User Problem Research

**Project:** ARIA — Your AI Learning Operating System  
**Phase:** Phase 0 — Research  
**Status:** Step 1 Complete  
**Purpose:** Understand how learners study, where current workflows fail, and which problems are worth investigating before defining ARIA's product requirements.

> Evidence note: Reddit discussions are treated as qualitative signals, not statistically representative evidence. Academic research is used separately to test learning-science assumptions. Founder experience, user evidence, product observations, and academic evidence are intentionally distinguished throughout this document.

---

## 1. Research Objective

This research does not attempt to prove that ARIA is a good idea. Its purpose is to understand real learning behaviours and test the assumptions behind the product.

The central questions are:

- How do learners currently study and revise?
- How are students using generative AI for learning?
- Where do study plans and learning workflows break down?
- Do learners use AI for active recall and self-testing?
- Is source-based learning audio useful outside the original founder use case?
- What problems arise when AI is used as a tutor?
- Which ARIA hypotheses have support from learning science?
- Which assumptions remain uncertain and require further validation?

---

## 2. Founder Problem Hypothesis

ARIA originated from personal learning problems rather than from a predetermined technology stack.

The initial problem hypothesis is that learners often use disconnected systems for:

- understanding concepts;
- organizing learning goals;
- maintaining study plans;
- storing notes and resources;
- revising material;
- testing themselves;
- tracking progress;
- identifying weak areas.

A particularly important use case is revision. Before an assessment, a learner may already possess notes and learning material but need an active revision companion that can ask questions, test recall, explain forgotten concepts, and convert existing material into audio that can be listened to when looking at a screen is inconvenient.

The broader hypothesis is therefore not simply that students need another chatbot. It is that a learning system could maintain continuity across the learning journey: organize what the learner wants to achieve, support studying, transform material into useful formats, evaluate understanding, remember progress, and adapt what happens next.

This remains a hypothesis rather than a confirmed product requirement.

---

## 3. Initial User Evidence

### 3.1 Attitudes toward AI-assisted studying

Initial student discussions revealed substantially different attitudes toward AI.

Some learners actively avoid AI and prefer textbooks, office hours, problem solving, and study groups. Their concern is that AI can replace the thinking required to actually learn.

Other learners use AI as a supplementary tutor. One particularly useful distinction from the research was the idea of using AI as a **tutor rather than a teacher**: the learner studies independently, attempts the problem, and uses AI to verify assumptions, clarify uncertainty, or deepen understanding.

### Implication

ARIA should investigate designs that support thinking rather than automatically replacing it. Possible interaction patterns include hints, questioning, active recall, attempts before solutions, and feedback after an answer.

This should be validated further rather than treated as a mandatory interaction model for every user.

---

## 4. Existing Student Discussion Research

Existing Reddit discussions were reviewed to avoid depending solely on responses to newly created research posts.

### Finding 1 — Study plans frequently collapse after disruption

Students repeatedly described creating schedules that become difficult to follow after missing tasks or losing a few days. In some cases, the effort required to maintain the planning system itself became another source of stress.

**Problem:** Static schedules do not adapt well when real life changes.

**ARIA hypothesis:** A planner or roadmap could redistribute unfinished work, reprioritize tasks, and adapt to changing progress.

**Important caution:** Automatic planning must reduce management overhead rather than create additional micromanagement.

**Sources:**

- r/GetStudying — missed days causing the study plan to collapse: https://www.reddit.com/r/GetStudying/comments/1s5awpq/i_missed_2_days_of_studying_and_my_entire_plan/
- r/GetStudying — discussion of falling behind and abandoning a study system: https://www.reddit.com/r/GetStudying/comments/m8dd0g/
- r/GetStudying — adaptive study-planning project, useful both as problem evidence and possible competition: https://www.reddit.com/r/GetStudying/comments/1v2x2cz/stop_making_study_plan_you_quit_by_day_3_i_will/
- r/GetStudying — simpler planning approaches and concern about micromanagement: https://www.reddit.com/r/GetStudying/comments/1iyqn6j/

### Finding 2 — Students already use AI for active recall

Students described manually pasting notes into general-purpose AI tools and asking the AI to:

- quiz them one question at a time;
- identify missing parts of an answer;
- explain incorrect answers;
- generate questions from their own notes;
- simulate exam-style retrieval rather than passive rereading.

**Problem:** The workflow exists, but users repeatedly reconstruct it through prompts and disconnected conversations.

**ARIA hypothesis:** Source-grounded assessment could become a persistent learning workflow: material → questions → attempt → evaluation → weakness detection → revision.

**Sources:**

- r/BestAiTips — using notes with ChatGPT to generate revision questions: https://www.reddit.com/r/BestAiTips/comments/1npwztn/
- r/AIStudyHelp — one-question-at-a-time AI quizzing and feedback: https://www.reddit.com/r/AIStudyHelp/comments/1pl16g9/i_stopped_rereading_notes_and_just_let_ai_quiz_me/
- r/studying — medical-student workflow using questions, retrieval attempts, gap identification, and source review: https://www.reddit.com/r/studying/comments/1uup829/im_a_final_year_med_student_here_is_the_exact_4/

### Finding 3 — Large learning contexts create reliability problems

Users reported that general-purpose AI can perform well on smaller collections of notes but become less reliable as the amount of study material increases, including introducing information not present in the supplied material.

**Problem:** Simply placing large quantities of educational material into an LLM context is insufficient for a trustworthy learning system.

**ARIA implication:** Context management, retrieval, source grounding, and validation should be treated as architectural requirements rather than optional optimizations.

**Source:**

- r/ChatGPT — study-note workflow reporting problems as supplied context grows: https://www.reddit.com/r/ChatGPT/comments/11n1xs6/

### Finding 4 — Source-generated audio has real learning use cases

NotebookLM users described generating audio overviews from course slides, chapters, notes, and other learning resources. Some specifically described listening during commuting, walking, or other situations where reading is inconvenient.

This independently resembles one of ARIA's original use cases: turning a learner's own notes and resources into revision audio that can be consumed away from the screen.

**ARIA hypothesis:** Learning material could be transformed into purpose-built audio formats such as quick revision, detailed explanation, exam-oriented revision, or a conversational overview.

**Important safety constraint:** Listening may be useful during travel, but interactive study activities should not encourage distraction while operating a vehicle.

**Sources:**

- r/notebooklm — chapter podcasts generated from course material: https://www.reddit.com/r/notebooklm/comments/1ld1ay8/
- r/notebooklm — audio-based studying while commuting or walking: https://www.reddit.com/r/notebooklm/comments/1q51qxy/looking_for_notebooklm_alternatives_that_work/

### Finding 5 — Audio alone has limitations

Users also reported limitations in generated educational audio:

- insufficient depth;
- overly short summaries;
- difficulty following complex material by listening alone;
- desire for accompanying transcripts;
- occasional hallucinated information.

**ARIA implication:** Audio should not simply read notes aloud. It should be generated for a learning purpose, remain grounded in source material, allow the learner to control focus/detail, and ideally retain traceability to its sources.

**Sources:**

- r/notebooklm — desire for transcripts alongside generated audio: https://www.reddit.com/r/notebooklm/comments/1ofbnp4/
- r/notebooklm — audio depth and hallucination concerns: https://www.reddit.com/r/notebooklm/comments/1g9j9er/
- r/notebooklm — audio overview length and comprehensive exam-revision needs: https://www.reddit.com/r/notebooklm/comments/1q8ikix/audio_overviews_length_problem/

### Finding 6 — Different learners use different study methods

Students reported combinations of textbooks, practice problems, active recall, flashcards, handwritten notes, group study, daily task lists, detailed schedules, and AI-assisted tutoring.

No single workflow fits every learner.

**ARIA implication:** ARIA should not hardcode a particular subject, study methodology, exam type, or learning schedule. The product shell can remain consistent while its learning content and behaviour evolve from the individual user's activity.

**Sources:**

- r/college — textbook, homework, and review workflow: https://www.reddit.com/r/college/comments/1iq2zsj/
- r/medicalschool — discussion of active recall, flashcards, writing, group study, and practice questions: https://www.reddit.com/r/medicalschool/comments/1tinsqg/to_the_students_who_were_in_the_top_quartile_of/

### Finding 7 — AI dependence and learner agency are concerns

Some students expressed concern that using AI to complete work can bypass the process required to understand the material. Other discussions highlight tutoring-oriented AI behaviour such as checking understanding rather than simply supplying answers.

**ARIA implication:** ARIA should investigate tutoring patterns that preserve learner agency and encourage active participation.

**Sources:**

- University discussion about AI use and learning: https://www.reddit.com/r/UTSA/comments/1sgsro9/whats_the_deal_with_ai_here/
- r/ChatGPT — discussion of Study Mode and tutoring behaviour: https://www.reddit.com/r/ChatGPT/comments/1mgx3vw/

---

## 5. Initial Product Observations

These observations are experiential rather than formal competitor analysis. A deeper competitor study belongs to Phase 0 Step 2.

### ChatGPT

Strengths observed include strong conversation, reasoning, explanations, memory capabilities, and flexible tutoring. Relevant gaps include the difference between general conversation and a structured assessment/learning-progress system.

Product: https://chatgpt.com/

### Claude

Strengths observed include technical reasoning, architecture/system-design explanations, and detailed responses. Explanations can sometimes feel dense or advanced for the learner.

**ARIA lesson:** Explanation complexity should adapt to the learner rather than assuming one preferred response style.

Product: https://claude.ai/

### Gemini

Limited direct usage was observed compared with ChatGPT and Claude. No strong product conclusion is currently justified.

Product: https://gemini.google.com/

### NotebookLM

The most relevant observed capability is transforming source material into generated audio experiences.

**ARIA lesson:** Existing learning material can become reusable learning experiences rather than remaining static files.

Product: https://notebooklm.google.com/

### Perplexity

Primarily perceived as useful for research and source-oriented information retrieval. It is not currently considered central to ARIA's v1 learning workflow.

Product: https://www.perplexity.ai/

### Notion

Strong inspiration for organization and turning unstructured information into structured plans, databases, and workflows.

**ARIA lesson:** The roadmap/planning experience should make organization feel lightweight. ARIA should not attempt to recreate the entirety of Notion.

Product: https://www.notion.so/

### OneNote

Observed primarily as traditional digital note-taking. ARIA Notes should focus on learning-specific transformations and connections rather than competing as a general-purpose notebook.

Product: https://www.onenote.com/

### External learning and practice platforms

Specialized platforms such as coding-practice systems, course platforms, video platforms, and other learning resources should not automatically be recreated inside ARIA.

A stronger hypothesis is that ARIA can organize and track learning that occurs across external resources where technically and legally feasible.

Examples observed during research:

- LeetCode: https://leetcode.com/
- YouTube: https://www.youtube.com/

For an initial version, external resources can be user-added links/resources with manual completion or progress recording. Automatic synchronization should only be considered after researching each platform's APIs, permissions, and terms.

---

## 6. Learning-Science Evidence

### 6.1 Retrieval practice

Research on retrieval practice provides strong evidence that actively retrieving learned information can improve later retention compared with repeatedly restudying the same material.

**ARIA implication:** Assessment should be part of the learning loop, not merely a final score screen.

Potential loop: **Learn → Retrieve → Answer → Feedback → Revisit weakness → Retrieve again.**

**Sources:**

- Yang, Luo, Vadillo, Yu & Shanks — *Testing (quizzing) boosts classroom learning: A systematic and meta-analytic review*: https://pubmed.ncbi.nlm.nih.gov/33006925/
- Recent retrieval-practice/testing-effect meta-analysis (2026): https://pubmed.ncbi.nlm.nih.gov/42258276/

### 6.2 Distributed / spaced practice

Research supports distributing learning and retrieval over time rather than relying entirely on massed practice.

**ARIA implication:** A topic should not necessarily become permanently "complete" after one session. ARIA can eventually use recency and assessment evidence to recommend revision.

**Source:**

- Meta-analysis of distributed practice in classroom learning (2025): https://pubmed.ncbi.nlm.nih.gov/40564553/

### 6.3 Dynamic personalization

Educational research suggests that personalization is more meaningful when relevant learner characteristics are measured during learning and used to adapt instruction, rather than relying only on a static profile created during onboarding.

**ARIA implication:** Onboarding should remain lightweight. The learning profile should evolve from actual behaviour, preferences, assessments, mistakes, and user corrections.

**Sources:**

- Educational Psychology Review — dynamically measuring learner characteristics for personalized education: https://link.springer.com/article/10.1007/s10648-020-09570-w
- Personalized-learning systematic review (2026): https://link.springer.com/article/10.1186/s40561-026-00440-6

### 6.4 Intelligent tutoring systems

Meta-analytic evidence suggests intelligent tutoring systems can improve educational outcomes, but results vary considerably across implementations and outcomes.

**Conclusion:** AI tutoring is promising, but "personalized AI" is not automatically effective.

**ARIA implication:** Personalization should support established learning behaviours such as retrieval, feedback, appropriate scaffolding, and revision rather than exist only as a product feature.

**Source:**

- Meta-analytic research on Intelligent Tutoring Systems (2025): https://www.sciencedirect.com/org/science/article/pii/S1539310025000031

### 6.5 Audio and multimodal learning

Learning research supports the usefulness of multiple modalities under appropriate circumstances, but audio should not be treated as inherently superior to written learning material.

**ARIA implication:** Audio is best understood as an alternative revision modality and accessibility/convenience format. Its value may be especially high when the learner cannot conveniently read from a screen.

**Sources:**

- Low & Sweller — *The Modality Principle in Multimedia Learning*: https://www.cambridge.org/core/books/cambridge-handbook-of-multimedia-learning/modality-principle-in-multimedia-learning/30769D7ADEE0EEE1C4CE5A01253C2819
- Mayer — Modality Principle and its boundary conditions: https://www.cambridge.org/core/books/abs/multimedia-learning/modality-principle/E5CD6E01CEA0B568CE260F66A3CD0D1F

### 6.6 Human agency, privacy, and responsible educational AI

Guidance on generative AI in education emphasizes human-centred use, learner agency, privacy, and responsible validation.

**ARIA implication:** The system should help the learner think, retrieve, practice, and understand rather than optimize purely for producing answers as quickly as possible.

**Sources:**

- UNESCO — *Guidance for Generative AI in Education and Research*: https://www.unesco.org/en/articles/guidance-generative-ai-education-and-research
- UNESCO full guidance document: https://unesdoc.unesco.org/ark:/48223/pf0000386693
- UNESCO — guidance on safeguards for generative AI in schools: https://www.unesco.org/en/articles/unesco-governments-must-quickly-regulate-generative-ai-schools

---

## 7. Major Risk — Hallucinations and Propagating Errors

Reliability is particularly important because ARIA's components may influence one another.

A generated error could propagate through the learning system:

1. incorrect information is generated;
2. an assessment contains the incorrect concept;
3. a correct student answer is evaluated incorrectly;
4. the learner model records a false weakness;
5. the roadmap prioritizes unnecessary revision;
6. future tutoring reinforces the original error.

Therefore source grounding and validation are not isolated "AI quality" concerns. They affect the integrity of the entire learning loop.

Future architecture research should investigate retrieval-grounded generation, structured outputs, validation stages, confidence/uncertainty handling, provenance, and Generate–Validate–Fix patterns.

---

## 8. Rethinking Mastery

A simple percentage such as "Topic Mastery: 73%" can imply more certainty than the system actually possesses.

Time spent, number of chats, or completion of a lesson does not prove mastery.

A future mastery model may need to consider evidence such as:

- assessment performance;
- repeated retrieval success;
- question difficulty;
- recency;
- repeated mistakes;
- consistency across attempts;
- possibly learner confidence.

Even then, mastery should be represented as an estimate rather than unquestionable truth.

The exact model remains an open research and architecture question.

---

## 9. Current ARIA Product Hypothesis

Based on the founder experience, initial user evidence, existing student discussions, product observations, and learning-science research, ARIA's current hypothesis is:

> ARIA is a personalized learning system that helps a learner organize what they want to learn, study using their own and external resources, transform learning material into useful formats, actively retrieve and test knowledge, understand progress, and continuously adapt the learning journey.

A useful conceptual loop is:

**Learning Intent → Organize → Learn → Transform → Retrieve/Practice → Evaluate → Adapt → Repeat**

This is a research hypothesis, not the final product definition. Phase 1 will define the formal product vision after Phase 0 research is complete.

---

## 10. Current Feature Hypotheses

The following ideas currently have enough justification to continue investigating. They are **not yet final MVP requirements**.

### Study

A conversational learning environment that can use relevant learning context while adapting explanation depth and interaction style.

### Roadmaps

User-specific learning journeys generated from the learner's goals rather than hardcoded subjects or predefined tracks.

### Adaptive Planner

Planning that can respond when the learner falls behind or circumstances change.

### Notes

Learning-specific notes generated or organized from study sessions and resources, with the learner retaining editing control.

### Exams / Active Recall

Source-grounded assessment using the learner's material, roadmap topics, or selected resources.

### Evaluation

Feedback that identifies missing concepts and recurring errors rather than returning only a score.

### Learning Audio

NotebookLM-inspired transformation of selected notes/resources/material into purpose-built revision audio.

Potential modes to investigate include quick revision, detailed explanation, exam-focused revision, conversational/podcast-style overview, and custom focus. These modes require further validation and should not yet be considered final UI requirements.

### Progress / Learning Model

An evolving representation of learning progress and areas that may need attention, based primarily on meaningful learning evidence rather than superficial activity metrics.

### Resources

A user-specific library containing material relevant to that learner. Subjects and collections must not be hardcoded.

Potential resource types include notes, PDFs, URLs, videos, courses, external exercises, generated audio, and other learner-added material.

---

## 11. Personalization Principle

ARIA should begin with minimal assumptions.

The application shell may contain stable areas such as Study, Roadmaps, Exams, Notes, Audio, Planner, Progress, and Resources, but the content inside those areas should emerge from the user.

ARIA must not assume that a learner is preparing for DSA, AWS, university exams, certifications, medicine, programming, or any other particular subject.

Likewise, onboarding should not require a single universal exam deadline. Users may have no exam, one exam, or many unrelated deadlines.

The system should progressively learn relevant context as the learner uses it.

---

## 12. Learning Objects Hypothesis

One potentially useful system abstraction discovered during research is the idea of a **Learning Object**.

Possible learning objects include topic, note, PDF/document, URL, video/resource, conversation, generated audio, assessment, and external exercise.

ARIA could transform or connect these objects.

Examples:

- **PDF → Notes / Audio / Assessment**
- **Study conversation → Notes / Audio / Assessment**
- **External resource → Roadmap topic → Completion evidence → Assessment → Progress update**

This remains an architecture hypothesis and should be evaluated during later system-design research.

---

## 13. Current Risks

1. **Hallucinations:** Incorrect generated information can damage learning and propagate through assessments and personalization.
2. **Overdependence on AI:** ARIA could accidentally make learners less willing to think independently if it provides answers too quickly.
3. **False mastery:** The system may infer understanding from insufficient evidence.
4. **Planning overload:** An adaptive planner could become another productivity system the learner has to maintain.
5. **Feature overload:** Chat, notes, audio, exams, roadmaps, planning, resources, and analytics can create an unfocused product unless they support one coherent learning loop.
6. **Privacy:** Long-term personalization may require storing educational history, uploaded material, goals, mistakes, and preferences. Data minimization, transparency, access control, deletion, and user control must be considered during architecture design.
7. **Integration feasibility:** Automatic tracking from external platforms depends on APIs, permissions, authentication mechanisms, rate limits, and terms of service.

---

## 14. Candidate Product Principles

1. **ARIA should support learning, not replace thinking.**
2. **Personalization should evolve from behaviour rather than rely on a large onboarding questionnaire.**
3. **User learning content must be dynamic; subjects and goals should not be hardcoded.**
4. **Assessment and retrieval are part of learning, not merely measurement.**
5. **Plans should adapt when reality changes.**
6. **Audio should transform material for revision rather than merely read text aloud.**
7. **ARIA should reduce learning-management overhead rather than create more of it.**
8. **Source grounding and validation are foundational requirements for educational AI.**
9. **External platforms should be complemented rather than unnecessarily rebuilt.**
10. **The learner should retain visibility and control over memory, plans, progress, and generated material.**

---

## 15. Evidence Summary

Three independent evidence streams currently converge on several ideas.

### Founder experience

- need for active revision;
- need for questions from personal learning material;
- desire for portable audio revision;
- difficulty maintaining evolving learning plans;
- desire for a system that remembers learning context over time.

### Student discussions

- study plans frequently break after disruption;
- students already use AI to quiz themselves from notes;
- generated learning audio is used during commuting/walking;
- learners are concerned about AI dependence and incorrect information;
- study methods vary significantly between individuals.

### Learning science

- retrieval practice is strongly supported;
- distributed practice is strongly supported;
- personalization can benefit from continuously updated learner information;
- intelligent tutoring is promising but not universally effective;
- multimodal/audio learning is context dependent;
- human agency and AI reliability remain important concerns.

---

## 16. Step 1 Conclusion

The evidence does **not** establish that ARIA has product-market fit, nor does it prove that every proposed feature should be built.

It does provide sufficient justification to continue investigating a coherent problem space:

> Learners need more than isolated answers. There is an opportunity to investigate a system that maintains continuity across learning — organizing goals and resources, supporting active learning, enabling revision in multiple formats, evaluating understanding, and adapting as the learner changes.

The strongest current hypotheses are:

- adaptive learning journeys;
- active recall and evaluation;
- persistent learning context;
- source-grounded learning;
- adaptive planning;
- learning-material transformation, including audio.

The strongest identified constraints are reliability, learner agency, accurate progress modelling, low management overhead, privacy, and controlled product scope.

**Phase 0 — Step 1: Market & User Problem Research is complete.**

---

## 17. Consolidated Sources & References

### Student discussions

1. Study-plan disruption: https://www.reddit.com/r/GetStudying/comments/1s5awpq/i_missed_2_days_of_studying_and_my_entire_plan/
2. Falling behind a study system: https://www.reddit.com/r/GetStudying/comments/m8dd0g/
3. Adaptive study-planning project: https://www.reddit.com/r/GetStudying/comments/1v2x2cz/stop_making_study_plan_you_quit_by_day_3_i_will/
4. Planning/micromanagement discussion: https://www.reddit.com/r/GetStudying/comments/1iyqn6j/
5. AI-generated revision questions: https://www.reddit.com/r/BestAiTips/comments/1npwztn/
6. AI one-question-at-a-time quizzing: https://www.reddit.com/r/AIStudyHelp/comments/1pl16g9/i_stopped_rereading_notes_and_just_let_ai_quiz_me/
7. Medical-student retrieval workflow: https://www.reddit.com/r/studying/comments/1uup829/im_a_final_year_med_student_here_is_the_exact_4/
8. Large-context study-note reliability discussion: https://www.reddit.com/r/ChatGPT/comments/11n1xs6/
9. AI and learning/academic-work discussion: https://www.reddit.com/r/UTSA/comments/1sgsro9/whats_the_deal_with_ai_here/
10. ChatGPT Study Mode discussion: https://www.reddit.com/r/ChatGPT/comments/1mgx3vw/
11. NotebookLM chapter podcasts: https://www.reddit.com/r/notebooklm/comments/1ld1ay8/
12. Audio studying while commuting/walking: https://www.reddit.com/r/notebooklm/comments/1q51qxy/looking_for_notebooklm_alternatives_that_work/
13. Audio transcripts request: https://www.reddit.com/r/notebooklm/comments/1ofbnp4/
14. Audio depth/hallucination discussion: https://www.reddit.com/r/notebooklm/comments/1g9j9er/
15. Audio overview length discussion: https://www.reddit.com/r/notebooklm/comments/1q8ikix/audio_overviews_length_problem/
16. College study workflow: https://www.reddit.com/r/college/comments/1iq2zsj/
17. Medical-school study-method discussion: https://www.reddit.com/r/medicalschool/comments/1tinsqg/to_the_students_who_were_in_the_top_quartile_of/

### Academic and institutional sources

18. Yang, Luo, Vadillo, Yu & Shanks — retrieval-practice meta-analysis: https://pubmed.ncbi.nlm.nih.gov/33006925/
19. Retrieval-practice/testing-effect meta-analysis (2026): https://pubmed.ncbi.nlm.nih.gov/42258276/
20. Distributed-practice classroom meta-analysis (2025): https://pubmed.ncbi.nlm.nih.gov/40564553/
21. Dynamic learner characteristics and personalized education: https://link.springer.com/article/10.1007/s10648-020-09570-w
22. Personalized-learning systematic review (2026): https://link.springer.com/article/10.1186/s40561-026-00440-6
23. Intelligent Tutoring Systems meta-analytic research (2025): https://www.sciencedirect.com/org/science/article/pii/S1539310025000031
24. Low & Sweller — Modality Principle: https://www.cambridge.org/core/books/cambridge-handbook-of-multimedia-learning/modality-principle-in-multimedia-learning/30769D7ADEE0EEE1C4CE5A01253C2819
25. Mayer — Modality Principle: https://www.cambridge.org/core/books/abs/multimedia-learning/modality-principle/E5CD6E01CEA0B568CE260F66A3CD0D1F
26. UNESCO — Guidance for Generative AI in Education and Research: https://www.unesco.org/en/articles/guidance-generative-ai-education-and-research
27. UNESCO full guidance document: https://unesdoc.unesco.org/ark:/48223/pf0000386693
28. UNESCO — generative AI safeguards in schools: https://www.unesco.org/en/articles/unesco-governments-must-quickly-regulate-generative-ai-schools

### Products observed

29. ChatGPT: https://chatgpt.com/
30. Claude: https://claude.ai/
31. Gemini: https://gemini.google.com/
32. NotebookLM: https://notebooklm.google.com/
33. Perplexity: https://www.perplexity.ai/
34. Notion: https://www.notion.so/
35. Microsoft OneNote: https://www.onenote.com/
36. LeetCode: https://leetcode.com/
37. YouTube: https://www.youtube.com/

### Evidence-handling rules

- Reddit findings are qualitative signals, not population-level statistics.
- A single comment is never sufficient to establish a product requirement.
- Founder experience is separated from external validation.
- Academic research tests learning assumptions; it does not validate ARIA itself.
- Product observations remain preliminary until formal competitor analysis.
- Contradictory evidence should be preserved rather than discarded.
- Future Phase 0 documents should place sources near supported findings and maintain a consolidated reference section.

---

## Next Step

**Phase 0 — Step 2: Competitor Analysis**

The next research stage will systematically evaluate direct and indirect alternatives, including general AI assistants, source-grounded learning tools, organization/planning products, revision/assessment tools, and relevant learning platforms. The objective is not to copy their feature sets, but to understand what each product solves well, where workflows remain fragmented, and where ARIA could provide differentiated value.

---

## Next

Step 2 — Competitor Analysis.
