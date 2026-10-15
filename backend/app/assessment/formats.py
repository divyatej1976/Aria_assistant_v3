from dataclasses import dataclass
from typing import Protocol

from app.core.errors import ValidationError


class AssessmentFormat(Protocol):
    name: str


@dataclass(frozen=True)
class FormatDefinition:
    name: str
    label: str
    generation_strategy: str
    evaluation_strategy: str


class FormatRegistry:
    def __init__(self) -> None:
        self._formats: dict[str, FormatDefinition] = {}

    def register(self, definition: FormatDefinition) -> None:
        self._formats[definition.name] = definition

    def get(self, name: str) -> FormatDefinition:
        try:
            return self._formats[name.lower()]
        except KeyError as exc:
            raise ValidationError(f"Unsupported assessment format: {name}") from exc

    def list(self) -> list[FormatDefinition]:
        return list(self._formats.values())


format_registry = FormatRegistry()
format_registry.register(
    FormatDefinition(
        name="mcq",
        label="Multiple choice",
        generation_strategy="mcq_generator",
        evaluation_strategy="deterministic_option_match",
    )
)
format_registry.register(FormatDefinition(
    name="true_false", label="True or false",
    generation_strategy="mcq_reshaped", evaluation_strategy="deterministic_option_match",
))
format_registry.register(FormatDefinition(
    name="short_answer", label="Short answer",
    generation_strategy="mcq_reshaped", evaluation_strategy="key_word_match",
))
format_registry.register(FormatDefinition(
    name="mixed", label="Mixed",
    generation_strategy="mcq_reshaped", evaluation_strategy="per_question",
))
