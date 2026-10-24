"""Web search for questions about current events, so the tutor answers from today's facts.

A time-sensitive question ("latest", "today", "who won", "this year", prices, news...) or the
learner's 🌐 button triggers one grounded search. OpenAI's web search tool is used when
OPENAI_API_KEY is set, else Gemini's Google Search grounding. The findings and their sources go
into the tutor's prompt; the sources are shown under the answer. Any failure means no web
results, and the tutor says it could not check the latest information.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Cues that the answer depends on what is true now, not on textbook knowledge.
FRESH_RE = re.compile(
    r"\b(today|tonight|yesterday|tomorrow|this (?:week|month|year|season)|last (?:week|month|night)|"
    r"latest|newest|most recent|recent(?:ly)?|right now|as of now|currently|these days|"
    r"news|headlines?|breaking|current (?:affairs|events|news|president|prime minister|pm|ceo|"
    r"champion|leader|price|rate|status|version|situation|government|chief minister|cm)|"
    r"who (?:won|is winning|leads)|score(?:s|card)?|standings|live|"
    r"price of|stock|share price|exchange rate|weather|forecast|election|"
    r"released|launch(?:ed)?|announced|trending|upcoming|20(?:2[5-9]|[3-9]\d))\b",
    re.IGNORECASE,
)


def needs_fresh_info(question: str) -> bool:
    return bool(FRESH_RE.search(question or ""))


@dataclass
class WebFindings:
    text: str
    sources: list[tuple[str, str]] = field(default_factory=list)  # (title, url)
    searched_on: str = ""


def today_label() -> str:
    return datetime.now(UTC).strftime("%d %B %Y").lstrip("0")


def _prompt(question: str) -> str:
    return (f"Today is {today_label()}. Search the web and report the up-to-date facts needed to answer "
            f"this question: {question}\n"
            "Give the key facts with dates and numbers in a few short bullet points, newest first, and "
            "say which source reports what. If sources disagree or nothing recent is found, say so.")


async def search_web(question: str) -> WebFindings | None:
    """One grounded search; None when no provider is configured or the search fails."""
    settings = get_settings()
    try:
        if getattr(settings, "openai_api_key", None):
            return await _openai(question, key=settings.openai_api_key, model=settings.aria_openai_search_model)
        if getattr(settings, "gemini_api_key", None):
            return await _gemini(question, key=settings.gemini_api_key, model=settings.aria_gemini_search_model)
    except Exception as exc:  # noqa: BLE001 - search is optional; the tutor says it could not check
        logger.warning("web search failed error_type=%s", type(exc).__name__)
    return None


def _unique(sources: list[tuple[str, str]], limit: int = 6) -> list[tuple[str, str]]:
    seen, out = set(), []
    for title, url in sources:
        if url and url not in seen:
            seen.add(url)
            out.append(((title or url)[:120], url))
    return out[:limit]


async def _openai(question: str, *, key: str, model: str) -> WebFindings | None:
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "tools": [{"type": "web_search"}], "input": _prompt(question)},
        )
    response.raise_for_status()
    texts, sources = [], []
    for item in response.json().get("output", []):
        for part in item.get("content", []) if item.get("type") == "message" else []:
            if part.get("type") == "output_text":
                texts.append(part.get("text", ""))
                sources += [(a.get("title", ""), a.get("url", "")) for a in part.get("annotations", [])
                            if a.get("type") == "url_citation"]
    text = "\n".join(texts).strip()
    return WebFindings(text, _unique(sources), today_label()) if text else None


async def _gemini(question: str, *, key: str, model: str) -> WebFindings | None:
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": key},
            json={"contents": [{"parts": [{"text": _prompt(question)}]}], "tools": [{"google_search": {}}],
                  "generationConfig": {"temperature": 0, "thinkingConfig": {"thinkingBudget": 0}}},
        )
    response.raise_for_status()
    candidate = (response.json().get("candidates") or [{}])[0]
    text = "".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", [])).strip()
    chunks = candidate.get("groundingMetadata", {}).get("groundingChunks", [])
    sources = [(chunk.get("web", {}).get("title", ""), chunk.get("web", {}).get("uri", "")) for chunk in chunks]
    if not text:
        return None
    return WebFindings(text, _unique(await _real_pages(sources)), today_label())


async def _real_pages(sources: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Google's grounding links are redirects that name only the website; follow each one so the
    learner sees (and opens) the exact page used. A link that cannot be resolved is kept as is."""
    import asyncio

    async def resolve(client: httpx.AsyncClient, title: str, url: str) -> tuple[str, str]:
        if "vertexaisearch.cloud.google.com" not in url:
            return title, url
        try:
            response = await client.get(url, follow_redirects=False)
            location = response.headers.get("location", "")
            return (title, location) if location.startswith("http") else (title, url)
        except httpx.HTTPError:
            return title, url

    async with httpx.AsyncClient(timeout=6) as client:
        return list(await asyncio.gather(*(resolve(client, title, url) for title, url in sources)))


def findings_block(findings: WebFindings) -> str:
    """The section the tutor reads; sources are numbered so the answer can name them."""
    lines = [f"Web results (searched {findings.searched_on}):", findings.text]
    if findings.sources:
        lines.append("Sources:")
        lines += [f"[{n}] {title}" for n, (title, _) in enumerate(findings.sources, start=1)]
    return "\n".join(lines)
