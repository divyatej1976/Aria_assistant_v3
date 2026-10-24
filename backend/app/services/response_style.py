"""Choose how long and in what tone a tutor reply should be.

The learner picks a depth (or leaves it on auto) and the client reports its
screen size. Auto reads the question's tone with deterministic rules, so the
same question always gets the same depth and no LLM call is spent on it.
"""

import re
from dataclasses import dataclass
from typing import Literal

Depth = Literal["quick", "balanced", "deep"]
RequestedDepth = Literal["auto", "quick", "balanced", "deep"]
Screen = Literal["compact", "regular", "wide"]
Tone = Literal["casual", "confused", "neutral"]

DEEP_RE = re.compile(
    r"\b(in detail|detailed|deep ?dive|step[- ]by[- ]step|thoroughly|walk me through|"
    r"explain (?:everything|fully)|with examples|how does .+ work under the hood)\b",
    re.IGNORECASE,
)
# The tutor's last message ended by asking the learner something.
ASKED_RE = re.compile(r"\?[\s*\"”)]*$|reply with your answer|give it a try|try answering|your answer", re.IGNORECASE)
EXPLAIN_RE = re.compile(r"\b(explain|describe|teach|walk me through|break (?:it|this) down)\b", re.I)
QUICK_RE = re.compile(
    r"\b(quick(?:ly)?|briefly|short|tl;?dr|in one line|one[- ]liner|just tell me|"
    r"what(?:'s| is) (?:a|an|the)?\s*\w+\??$|define)\b",
    re.IGNORECASE,
)
CONFUSED_RE = re.compile(
    r"\b(i don'?t (?:get|understand)|confus(?:ed|ing)|lost|makes no sense|still not clear|"
    r"simpler|eli5|like i'?m (?:five|5|a beginner))\b",
    re.IGNORECASE,
)
CASUAL_RE = re.compile(r"^(hey|hi|hello|yo|ok|okay|so|hmm|btw)\b|!\s*$|\b(lol|pls|plz)\b", re.IGNORECASE)
SUMMARY_RE = re.compile(r"\b(summar(?:y|ise|ize)|overview|key points|main (?:points|ideas))", re.IGNORECASE)
# "Quiz me", "test me", "give me an interview question": the learner wants to answer, not read.
PRACTICE_RE = re.compile(
    r"\b(quiz me|test me|ask me|drill me|let me (?:try|answer|practi[cs]e)|"
    r"(?:give|show) me (?:a|an|one|some|\d+) (?:[\w-]+ ){0,3}(?:question|problem|exercise|challenge)s?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ResponseStyle:
    depth: Depth
    tone: Tone
    screen: Screen
    practice: bool = False
    grading: bool = False
    summary: bool = False

    def instruction(self) -> str:
        """The per-message style rules placed in the user prompt."""
        size = {
            "quick": "Reply in 2-4 short lines: the key point and at most one tiny example. No headings.",
            "balanced": "Give a clear, well-structured explanation of the key concepts with one or two "
                        "concrete examples, like a good textbook section on exactly this question. Use "
                        "'###' headings only if it has distinct parts.",
            # The app shows a Deep answer as study cards, one '###' section per card.
            "deep": "Give a thorough, in-depth explanation, written as 6-10 short sections that each fit on "
                    "one study card: a '###' heading, then about 60-150 words. Name each heading for what "
                    "it is (for example 'What is …', 'How … works', 'Example: …', 'Common mistakes'), "
                    "covering every main concept and sub-topic, definitions, the reasoning behind it, worked "
                    "examples (code or numbers where it fits), edge cases and how it connects to related "
                    "ideas. Split a big idea across several cards rather than writing one long section. "
                    "Finish with '### Key takeaways' (3-5 bullets) and then '### Check yourself': one "
                    "question, then a line starting 'Answer:' with the answer. Never cut it short.",
        }[self.depth]
        if self.summary:
            size = ("Write structured study notes covering the whole material: one '###' heading per main "
                    "topic in the material's order, key definitions in **bold**, the important points as "
                    "bullets, examples, and how the ideas connect. Cover every section, including the "
                    "last ones, and end with '### Key takeaways'.")
        if self.grading:
            size = ("The learner is answering the question you just asked. Open with a bold verdict: "
                    "'**Correct**', '**Partly right**' or '**Not quite**'. Then in 2-5 short lines say what "
                    "they got right, what is missing or wrong and why; add a tiny corrected example only "
                    "if needed. Finish by offering another question. No other block labels.")
        elif self.practice:
            size = ("The learner wants to practise. Ask the question(s) they asked for (one if they did "
                    "not say how many) and stop: do not answer it, do not give hints, and do not use "
                    "'Direct answer' or other block labels. End by inviting them to reply with their answer.")
        tone = {
            "casual": "Match the learner's relaxed tone: friendly and plain, no formal preamble.",
            "confused": "The learner is struggling: use simpler words, one everyday analogy, and "
                        "build up from what they already know. Do not just repeat the earlier answer.",
            "neutral": "Use a clear, warm, encouraging tone.",
        }[self.tone]
        screen = (
            " The learner is on a small screen: keep lines and code examples short and avoid wide tables."
            if self.screen == "compact" else ""
        )
        return f"Response style: {size} {tone}{screen}"


def detect_tone(question: str) -> Tone:
    text = question.strip()
    if CONFUSED_RE.search(text):
        return "confused"
    if CASUAL_RE.search(text):
        return "casual"
    return "neutral"


def auto_depth(question: str) -> Depth:
    text = question.strip()
    # "Summarize this" is short to type but asks for the whole document, not two lines.
    if DEEP_RE.search(text) or SUMMARY_RE.search(text):
        return "deep"
    # Short questions get short answers, but "explain this image" is short to type and asks
    # for a real explanation.
    if QUICK_RE.search(text) or (len(text.split()) <= 6 and not EXPLAIN_RE.search(text)):
        return "quick"
    return "balanced"


def resolve_style(
    question: str, requested: RequestedDepth = "auto", screen: Screen = "regular", last_tutor: str | None = None,
) -> ResponseStyle:
    depth: Depth = auto_depth(question) if requested == "auto" else requested
    # A reply of a few words ("ok thanks") is not an attempt at the question.
    grading = (bool(last_tutor) and len(question.split()) >= 3 and not question.rstrip().endswith("?")
               and bool(ASKED_RE.search(last_tutor[-300:])))
    return ResponseStyle(depth=depth, tone=detect_tone(question), screen=screen,
                         practice=bool(PRACTICE_RE.search(question)) and not grading, grading=grading,
                         summary=bool(SUMMARY_RE.search(question)) and not grading)
