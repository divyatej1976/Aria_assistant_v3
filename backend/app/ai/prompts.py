"""Versioned prompt registry.

Every AI generation point renders a prompt from a versioned template so the
exact prompt used for a given output is reproducible and auditable. The prompt
version is recorded in AI call logs and metrics.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptVersion:
    key: str
    version: int
    system: str
    template: str

    def render(self, **kwargs: object) -> str:
        return self.template.format(**kwargs)

    def label(self) -> str:
        return f"{self.key}:{self.version}"


_PROMPTS: dict[str, PromptVersion] = {
    "study_answer": PromptVersion(
        key="study_answer",
        # v5: short labelled blocks, per-message depth and tone ("Response style:"),
        # no sources footer. The live text is STUDY_SYSTEM_PROMPT in
        # app/services/context_assembly.py; this entry versions it for logs.
        version=5,
        system="See app.services.context_assembly.STUDY_SYSTEM_PROMPT.",
        template="Context:\n{context}\n\nQuestion: {question}",
    ),
    "concept_extraction": PromptVersion(
        key="concept_extraction",
        version=1,
        system="You produce only valid JSON matching the schema.",
        template=(
            "Extract the most important learning concepts from the supplied study material. "
            'Return JSON matching the schema: {{"concepts": ["concept one", "concept two"]}}. '
            "Produce up to {limit} concepts.\n\nStudy material:\n{material}"
        ),
    ),
    "note_draft": PromptVersion(
        key="note_draft",
        version=1,
        system="You produce only valid JSON matching the schema.",
        template=(
            "Write concise, factual study notes grounded only in the supplied material. "
            'Return JSON matching the schema: {{"title": "...", "body": "..."}}. '
            "The body should be clean prose or short sections.\n\nMaterial:\n{material}"
        ),
    ),
    "mcq_generation": PromptVersion(
        key="mcq_generation",
        version=4,
        system="You produce only valid JSON matching the schema.",
        template=(
            "Generate multiple-choice questions grounded only in the supplied study material. "
            "Each question must have exactly four distinct options and a correct_option letter "
            "of A, B, C, or D matching the correct option. Exactly one option may be correct: "
            "every other option must be clearly wrong, never an equivalent way of writing or "
            "saying the right answer. Return JSON matching the schema:\n"
            '{{"questions": [{{"prompt": "...", "options": ["...", "...", "...", "..."], '
            '"correct_option": "A", "explanation": "One sentence on why the answer is right.", '
            '"concept": "The topic it tests, 2-4 words, e.g. HAVING clause"}}]}}\n\n'
            "Difficulty: {difficulty}. Produce {count} questions.\n\nStudy material:\n{material}"
        ),
    ),
    "roadmap_tree_generation": PromptVersion(
        key="roadmap_tree_generation",
        version=2,
        system="You are an expert Curriculum Architect. You produce only valid JSON matching the schema.",
        template=(
            "Create a goal-oriented, progressive learning roadmap tree for a learner with the following goal:\n"
            "Goal: {goal}\n"
            "Target Level: {level}\n"
            "Target Date / Timeframe: {target_date}\n\n"
            "Rules:\n"
            "1. Organize the curriculum into 4 sequential phases: 'Foundations', 'Core "
            "Concepts', 'Advanced Topics', 'Mastery Track'.\n"
            "2. For each phase, generate 2 to 4 distinct, concrete milestones.\n"
            "3. Each milestone MUST have:\n"
            "   - 'title': concise topic title (e.g. 'Goroutines & Concurrency Channels')\n"
            "   - 'description': what this milestone covers and why it matters\n"
            "   - 'key_skills': list of 2 to 4 specific skills or concepts required to master "
            "it (e.g. ['channel buffering', 'select statement', 'race condition detection'])\n"
            "   - 'prerequisites': list of milestone titles that must be completed before starting this one\n"
            "   - 'outcome': one sentence on what the learner can do afterwards\n"
            "   - 'effort_hours': estimated study hours (a whole number), fitting the timeframe\n"
            "   - 'activity': one concrete way to learn it (an exercise, a small project, a reading)\n"
            "   - 'check': how understanding will be checked (e.g. a 5-question quiz, explaining it aloud)\n"
            "4. The output must strictly match the JSON schema:\n"
            '{{"goal": "{goal}", "level": "{level}", "phases": ['
            '{{"phase_name": "Foundations", "milestones": ['
            '{{"title": "...", "description": "...", "key_skills": ["..."], "prerequisites": [], '
            '"outcome": "...", "effort_hours": 3, "activity": "...", "check": "..."}}'
            ']}}'
            ']}}'
        ),
    ),
}


def get_prompt(key: str) -> PromptVersion:
    try:
        return _PROMPTS[key]
    except KeyError as exc:
        raise KeyError(f"Unknown prompt: {key}") from exc
