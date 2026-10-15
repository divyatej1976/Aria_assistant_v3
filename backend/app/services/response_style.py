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


@dataclass(frozen=True)
class ResponseStyle:
    depth: Depth
    tone: Tone
    screen: Screen

    def instruction(self) -> str:
        """The per-message style rules placed in the user prompt."""
        size = {
            "quick": "Reply in 2-4 short lines. Give the direct answer and at most one tiny example. "
                     "No headings.",
            "balanced": "Open with the direct answer in 1-2 lines, then up to 3 short blocks such as "
                        "'**What it means**', '**Example**' and '**Watch out**'. Keep each block to "
                        "2-4 lines and one small example.",
            "deep": "Open with the direct answer in 1-2 lines, then a step-by-step breakdown in short "
                    "blocks (each with a bold label), worked examples, common mistakes, and finish "
                    "with one '**Check yourself**' question.",
        }[self.depth]
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
    if DEEP_RE.search(text):
        return "deep"
    if QUICK_RE.search(text) or len(text.split()) <= 6:
        return "quick"
    return "balanced"


def resolve_style(question: str, requested: RequestedDepth = "auto", screen: Screen = "regular") -> ResponseStyle:
    depth: Depth = auto_depth(question) if requested == "auto" else requested
    return ResponseStyle(depth=depth, tone=detect_tone(question), screen=screen)
