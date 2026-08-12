from pydantic import BaseModel, Field, field_validator


class MCQItem(BaseModel):
    prompt: str = Field(min_length=10, max_length=2000)
    options: list[str] = Field(min_length=4, max_length=4)
    correct_option: str = Field(min_length=1, max_length=1)

    @field_validator("correct_option")
    @classmethod
    def validate_letter(cls, value: str) -> str:
        letter = value.strip().upper()
        if letter not in ("A", "B", "C", "D"):
            raise ValueError("correct_option must be one of A, B, C, D")
        return letter

    @field_validator("options")
    @classmethod
    def validate_options(cls, values: list[str]) -> list[str]:
        stripped = [value.strip() for value in values]
        if len(set(stripped)) != len(stripped):
            raise ValueError("All four options must be distinct")
        if any(not value for value in stripped):
            raise ValueError("Options cannot be empty")
        return stripped


class MCQSet(BaseModel):
    questions: list[MCQItem] = Field(min_length=1, max_length=20)


class ConceptSet(BaseModel):
    concepts: list[str] = Field(min_length=1, max_length=30)

    @field_validator("concepts")
    @classmethod
    def clean_concepts(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for value in values:
            name = value.strip().lower()
            if name and name not in seen:
                seen.add(name)
                cleaned.append(name)
        return cleaned
