"""Turn generated multiple-choice items into the question format the learner chose.

Every generator (LLM, library material, chat transcript) produces multiple-choice
items. Reshaping them here keeps one grounded source of questions while letting
the learner pick true/false, fill-in-the-blank, short answer, or a mix, and it
works the same with or without an LLM.
"""

import random
import re
from dataclasses import replace

from app.assessment.mcq import GeneratedMCQ

LETTERS = "ABCD"
QUESTION_FORMATS = ("mcq", "true_false", "short_answer", "mixed")
_BLANK_LINE = re.compile(r"“(?P<before>.*)____(?P<after>.*)”", re.DOTALL)


def correct_text(question: GeneratedMCQ) -> str:
    letter = question.correct_option
    if len(letter) == 1 and letter in LETTERS and LETTERS.index(letter) < len(question.options):
        return question.options[LETTERS.index(letter)]
    return letter


def to_true_false(question: GeneratedMCQ, rng: random.Random) -> GeneratedMCQ:
    answer = correct_text(question)
    wrong = [option for option in question.options if option != answer]
    statement = answer if not wrong or rng.random() < 0.5 else rng.choice(wrong)
    stem = question.prompt.strip()
    return replace(
        question,
        kind="true_false",
        prompt=f"{stem}\n\nProposed answer: “{statement}”\n\nIs the proposed answer correct?",
        options=["True", "False"],
        correct_option="A" if statement == answer else "B",
        explanation=question.explanation or f"The correct answer is: {answer}",
    )


def to_short_answer(question: GeneratedMCQ) -> GeneratedMCQ:
    """Fill-in-the-blank when the stem already has a blank, otherwise a typed answer."""
    answer = correct_text(question)
    blank = _BLANK_LINE.search(question.prompt)
    if blank and answer.startswith(blank["before"]) and answer.endswith(blank["after"]):
        missing = answer[len(blank["before"]):len(answer) - len(blank["after"])].strip()
        if missing:
            return replace(
                question,
                kind="short_answer",
                prompt=f"Fill in the missing word from your study material:\n“{blank['before']}____{blank['after']}”",
                options=[],
                correct_option=missing,
                explanation=question.explanation or f"The full sentence is: {answer}",
            )
    if question.prompt.startswith("Which statement matches this source quotation"):
        # A word-for-word recall stem cannot be answered by typing; keep the choices.
        return question
    return replace(
        question,
        kind="short_answer",
        options=[],
        correct_option=answer,
        explanation=question.explanation or f"A good answer: {answer}",
    )


def shape_questions(questions: list[GeneratedMCQ], question_format: str, seed: str) -> list[GeneratedMCQ]:
    rng = random.Random(seed)
    shaped: list[GeneratedMCQ] = []
    for index, question in enumerate(questions):
        target = question_format
        if question_format == "mixed":
            target = ("mcq", "true_false", "short_answer")[index % 3]
        if target == "true_false":
            shaped.append(to_true_false(question, rng))
        elif target == "short_answer":
            shaped.append(to_short_answer(question))
        else:
            shaped.append(question)
    return shaped


_ARTICLES = {"a", "an", "the"}


def _words(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in _ARTICLES]


def short_answer_matches(expected: str, given: str | None) -> bool:
    """Accept typed answers by meaning-bearing words, not exact spelling of the whole line.

    Single-word answers must match that word. Longer answers pass when most of the
    expected content words appear, so word order, articles and punctuation do not
    matter and "I don't know" never passes.
    """
    if not given or not given.strip():
        return False
    expected_words, given_words = _words(expected), set(_words(given))
    if not expected_words:
        return given.strip().lower() == expected.strip().lower()
    if len(expected_words) == 1:
        return expected_words[0] in given_words
    hits = sum(word in given_words for word in expected_words)
    return hits / len(expected_words) >= 0.7
