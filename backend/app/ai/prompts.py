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
        version=1,
        system=(
            "You are ARIA, a grounded study assistant. Answer using only the supplied "
            "context. If the context cannot support an answer, say so plainly and point "
            "to the closest excerpt."
        ),
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
        version=1,
        system="You produce only valid JSON matching the schema.",
        template=(
            "Generate multiple-choice questions grounded only in the supplied study material. "
            "Each question must have exactly four distinct options and a correct_option letter "
            "of A, B, C, or D matching the correct option. Return JSON matching the schema:\n"
            '{{"questions": [{{"prompt": "...", "options": ["...", "...", "...", "..."], '
            '"correct_option": "A"}}]}}\n\n'
            "Difficulty: {difficulty}. Produce {count} questions.\n\nStudy material:\n{material}"
        ),
    ),
}


def get_prompt(key: str) -> PromptVersion:
    try:
        return _PROMPTS[key]
    except KeyError as exc:
        raise KeyError(f"Unknown prompt: {key}") from exc
