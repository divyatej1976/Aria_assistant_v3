"""Turn a document or chat into a spoken lesson instead of reading it aloud verbatim.

Long sources are condensed section by section first (map), then written as one
script (reduce). Sources too long for one episode become a series of parts in one
file, each part with its own full script, so later chapters get the same depth.
"""

import asyncio
import logging
import math
import re
from typing import Literal

logger = logging.getLogger(__name__)

Style = Literal["explainer", "conversation"]
Turn = tuple[Literal["tutor", "learner"], str]

PART_CHARS = 40_000  # more than this gets its own part, so no section is squeezed into a few lines
MAX_PARTS = 8

_STYLE_RULES = {
    "explainer": (
        "Write it as one friendly tutor talking to a student. Open by saying in one or two "
        "sentences what this material is about and why it matters, then explain the key ideas "
        "one at a time in plain language with a concrete example for each, connect them, and "
        "finish with a short recap of the three most important points."
    ),
    "conversation": (
        "Write it as a conversation between a TUTOR who explains and a curious LEARNER who asks "
        "the questions a student would actually ask, says when something is confusing, and tries "
        "examples. Start every line with 'TUTOR:' or 'LEARNER:'. The tutor does most of the "
        "explaining; end with the learner summarising the key points and the tutor confirming."
    ),
}


def split_parts(text: str) -> list[str]:
    """Cut a long source into near-equal parts, at a paragraph break when one is close."""
    if len(text) <= PART_CHARS:
        return [text]
    count = min(MAX_PARTS, math.ceil(len(text) / PART_CHARS))
    size = math.ceil(len(text) / count)
    parts: list[str] = []
    start = 0
    for _ in range(count - 1):
        target = start + size
        cut = text.rfind("\n\n", target - 2_000, target + 2_000)
        cut = cut + 2 if cut > start else target
        parts.append(text[start:cut])
        start = cut
    parts.append(text[start:])
    return [part for part in parts if part.strip()]


async def _write_script(provider, *, title: str, text: str, style: Style,
                        part: int = 1, parts: int = 1, next_start: str = "") -> str:
    from app.services.condense import condense, generate_with_retry

    # Every part of a long source is condensed first, so later chapters are covered too.
    material = await condense(provider, title=title, text=text)
    # Long sources earn a longer episode so every section gets airtime.
    length = "1200-1600" if len(text) > 12_000 else "700-1000"
    series = "" if parts == 1 else (
        f"This is part {part} of {parts} of a series on this material. Open by saying 'Part {part} of "
        f"{parts}' and what this part covers, recap earlier parts in at most one sentence, and "
        # The writer only sees this part, so the preview of the next one comes from its opening text.
        + ("end by saying the series is complete. " if part == parts
           else f"end with a one-sentence recap, then say that part {part + 1} picks up with a topic you name "
                "in a few words, taken from the excerpt that opens it. Never read the excerpt aloud or "
                f"guess beyond it. Excerpt: {next_start!r} ")
    )
    return await generate_with_retry(
        provider,
        system=("You write spoken study episodes. Output plain spoken sentences only: no markdown, "
                "no headings, no bullet symbols, no code blocks, no stage directions."),
        user=(f"Create an audio lesson of roughly {length} words teaching the material below (saved as '{title}'; "
              f"take the topic from the material, not that name). {series}"
              f"{_STYLE_RULES[style]} Cover every chapter or section of the material in order and give "
              "each its share: the last sections matter as much as the first, so never stop early or "
              "skip the end. Teach what the material says; do not describe the file, its layout, or "
              "that it is a photo or a document. If the material is a tutoring chat, teach the subject "
              "the tutor explained as a fresh lesson; never read out the chat or mention who asked what"
              f".\n\nMaterial:\n{material}"),
        prompt_version=f"audio_script:{style}:3",
    )


def parse_turns(script: str, style: Style) -> list[Turn]:
    """Split a dialogue into speaker turns; anything unlabelled belongs to the tutor."""
    if style == "explainer":
        return [("tutor", script.strip())] if script.strip() else []
    turns: list[Turn] = []
    for raw in script.splitlines():
        line = raw.strip().strip("*")
        if not line:
            continue
        match = re.match(r"^\**\s*(TUTOR|LEARNER)\s*\**\s*:\s*\**\s*(.*)$", line, re.IGNORECASE)
        speaker = match.group(1).lower() if match else "tutor"
        content = (match.group(2) if match else line).strip()
        if not content:
            continue
        if turns and turns[-1][0] == speaker:
            turns[-1] = (speaker, f"{turns[-1][1]} {content}")
        else:
            turns.append((speaker, content))  # type: ignore[arg-type]
    return turns


def script_parts(provider, *, title: str, text: str, style: Style,
                 cancelled=lambda: False, progress=None) -> list[list[Turn]] | None:
    """Blocking wrapper for the audio worker thread: one list of turns per part.

    None means no lesson could be written. `cancelled` is checked before each part so a
    cancelled episode stops spending AI calls.
    """
    if provider is None:
        return None
    sources = split_parts(text)

    # From a job, scripts written by an earlier worker are reused.
    saved = list(progress.data.get("scripts", []))[:len(sources)] if progress is not None else []

    async def write_all() -> list[str]:
        scripts = list(saved)
        # One part at a time: parts share the provider's per-minute limit.
        for index, source in enumerate(sources, start=1):
            if index <= len(scripts):
                continue
            if cancelled():
                raise RuntimeError("episode cancelled")
            scripts.append(await _write_script(provider, title=title, text=source, style=style,
                                               part=index, parts=len(sources),
                                               next_start=sources[index][:300] if index < len(sources) else ""))
            if progress is not None:
                progress.save(scripts=scripts, label=f"Writing part {index} of {len(sources)}")
                progress.check_time()
        return scripts

    from app.services.jobs import Continue

    try:
        scripts = asyncio.run(write_all())
    except Continue:
        raise  # out of time: the job resumes from the saved scripts
    except Exception:
        logger.warning("audio script generation failed; reading the source instead", exc_info=True)
        return None
    turns = [parse_turns(script, style) for script in scripts]
    return turns if all(turns) else None
