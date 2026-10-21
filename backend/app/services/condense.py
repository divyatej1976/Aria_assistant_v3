"""Shrink any long text into dense study notes, section by section, until it fits one prompt.

Every section is condensed (nothing is silently skipped), and the notes are condensed again
while they are still too long, so a whole textbook still fits one context.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

# First try, then retries spaced to outlast a per-minute provider limit.
RETRY_WAITS = (0, 15, 30, 60)

SECTION_CHARS = 6_000  # small enough that one section rarely spans many chapters
FITS_CHARS = 12_000
MAX_ROUNDS = 4


async def generate_with_retry(provider, **request) -> str:
    """generate_text, waiting out per-minute rate limits before giving up."""
    for attempt, wait in enumerate(RETRY_WAITS):
        if wait:
            await asyncio.sleep(wait)
        try:
            return await provider.generate_text(**request)
        except Exception:
            if attempt == len(RETRY_WAITS) - 1:
                raise
            logger.warning("generate_text failed; retrying in %ss", RETRY_WAITS[attempt + 1], exc_info=True)
    raise AssertionError("unreachable")


async def condense(provider, *, title: str, text: str, fits: int = FITS_CHARS) -> str:
    """Return notes covering all of `text` in at most `fits` characters (best effort)."""
    rounds = 0
    while len(text) > fits and rounds < MAX_ROUNDS:
        parts = [text[start:start + SECTION_CHARS] for start in range(0, len(text), SECTION_CHARS)]
        notes: list[str] = []
        for index, part in enumerate(parts, start=1):
            try:
                note = (await generate_with_retry(
                    provider,
                    system="You condense study material into dense, accurate study notes.",
                    user=(f"Write concise notes (at most 250 words) on part {index} of {len(parts)} of "
                          f"'{title}'. If it contains several chapters or headings, give each its own short "
                          "entry, in order, and never skip the later ones. Keep every key idea, definition, "
                          f"name, number and formula exactly.\n\n{part}"),
                    prompt_version="condense:2",
                )).strip()
            except Exception:
                logger.warning("condense: part %d/%d failed after retries", index, len(parts), exc_info=True)
                note = None
            # Keep an excerpt rather than dropping the section without trace.
            notes.append(note or part[:2000].strip())
        text = "\n\n".join(note for note in notes if note)
        rounds += 1
    return text[:fits] if len(text) > fits else text
