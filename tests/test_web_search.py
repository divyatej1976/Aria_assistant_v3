import asyncio

import httpx
import pytest

from app.services import web_search
from app.services.web_search import WebFindings, needs_fresh_info


@pytest.mark.parametrize("question", [
    "What is the latest news on the Mars mission?", "Who won the match yesterday?",
    "current prime minister of India", "price of gold today", "What happened in 2026 elections?",
])
def test_time_sensitive_questions_search_the_web(question):
    assert needs_fresh_info(question)


@pytest.mark.parametrize("question", [
    "Explain electric current in a circuit", "What is binary search?", "Teach me recursion with an example",
])
def test_textbook_questions_do_not(question):
    assert not needs_fresh_info(question)


_RealClient = httpx.AsyncClient


def _client_answering(body):
    def factory(**kwargs):
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
        return _RealClient(transport=transport, **kwargs)
    return factory


def test_gemini_grounded_search_returns_facts_and_sources(monkeypatch):
    body = {"candidates": [{"content": {"parts": [{"text": "- Launch moved to 3 Nov 2026."}]},
                            "groundingMetadata": {"groundingChunks": [
                                {"web": {"uri": "https://news.example/a", "title": "news.example"}},
                                {"web": {"uri": "https://news.example/a", "title": "dup"}}]}}]}
    monkeypatch.setattr(web_search.httpx, "AsyncClient", _client_answering(body))
    found = asyncio.run(web_search._gemini("When is the launch?", key="k", model="m"))
    assert found.text.startswith("- Launch moved") and found.sources == [("news.example", "https://news.example/a")]


def test_openai_web_search_returns_facts_and_sources(monkeypatch):
    body = {"output": [{"type": "web_search_call"}, {"type": "message", "content": [{
        "type": "output_text", "text": "Rates were cut on 22 Oct 2026.",
        "annotations": [{"type": "url_citation", "url": "https://bank.example/rates", "title": "Bank"}]}]}]}
    monkeypatch.setattr(web_search.httpx, "AsyncClient", _client_answering(body))
    found = asyncio.run(web_search._openai("Latest interest rate?", key="k", model="m"))
    assert found.sources == [("Bank", "https://bank.example/rates")] and "22 Oct 2026" in found.text


def test_tutor_answers_from_web_results_and_cites_them(client, monkeypatch, session_factory):
    from app.services import study

    prompts = []

    class Provider:
        async def generate_text(self, *, system, user, **kwargs):
            prompts.append(user)
            return "According to [1], the launch moved to 3 November 2026."

    async def fake_search(question):
        return WebFindings("- Launch moved to 3 Nov 2026.", [("Space News", "https://space.example/x")], "24 October 2026")

    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: Provider())
    monkeypatch.setattr(web_search, "search_web", fake_search)
    from uuid import uuid4

    from app.db.models import LearningContext
    with session_factory() as db:
        owner = uuid4()
        context = LearningContext(owner_id=owner, title="Space")
        db.add(context)
        db.commit()
        statuses = []
        result = asyncio.run(study.answer_question(db, owner_id=owner, context_id=context.id,
                                                   question="What is the latest on the launch?",
                                                   on_status=statuses.append))
        assert statuses == ["Searching the web…"]
        assert "Web results (searched 24 October 2026)" in prompts[0] and "Today's date:" in prompts[0]
        assert [(s.source_title, s.url, s.resource_id) for s in result.sources] == [
            ("Space News", "https://space.example/x", "web:24 October 2026")]

        async def failing_search(question):
            return None

        monkeypatch.setattr(web_search, "search_web", failing_search)
        result = asyncio.run(study.answer_question(db, owner_id=owner, context_id=context.id,
                                                   question="Who won the match today?"))
        assert result.sources == [] and not result.fallback_used and "Web results" not in prompts[1]


def test_google_redirect_links_become_the_real_pages(monkeypatch):
    redirect = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc"

    def handler(request):
        if request.url.host == "vertexaisearch.cloud.google.com":
            return httpx.Response(302, headers={"location": "https://en.wikipedia.org/wiki/Prime_Minister"})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "- Facts."}]},
                                         "groundingMetadata": {"groundingChunks": [
                                             {"web": {"uri": redirect, "title": "wikipedia.org"}}]}}]})

    monkeypatch.setattr(web_search.httpx, "AsyncClient",
                        lambda **kwargs: _RealClient(transport=httpx.MockTransport(handler), **kwargs))
    found = asyncio.run(web_search._gemini("Who is PM?", key="k", model="m"))
    assert found.sources == [("wikipedia.org", "https://en.wikipedia.org/wiki/Prime_Minister")]
