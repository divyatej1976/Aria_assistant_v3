"""Long files are condensed in full, and "summarize this" uses the whole-file digest."""

import asyncio
from uuid import UUID

from tests.test_chat_attachments import _CapturingProvider, _learner

from app.services.condense import condense


class _Counter:
    def __init__(self) -> None:
        self.calls = 0

    async def generate_text(self, *, system, user, prompt_version=None, temperature=0.0):
        self.calls += 1
        return "N" * 1500  # each section becomes ~1.5k characters of notes


def test_every_section_is_condensed_and_rounds_repeat_until_it_fits() -> None:
    writer = _Counter()
    text = "x" * 250_000  # 25 sections -> ~37k of notes -> a second round -> fits
    notes = asyncio.run(condense(writer, title="Big book", text=text))
    assert writer.calls >= 25 + 4
    assert len(notes) <= 12_000


def test_failed_sections_keep_an_excerpt_instead_of_vanishing(monkeypatch) -> None:
    import app.services.condense as condense_module

    monkeypatch.setattr(condense_module, "RETRY_WAITS", (0, 0, 0))
    class _Flaky:
        async def generate_text(self, *, system, user, prompt_version=None, temperature=0.0):
            if "part 2 of" in user:
                raise RuntimeError("rate limited")
            return "fine"

    size = condense_module.SECTION_CHARS
    notes = asyncio.run(condense(_Flaky(), title="t", text="a" * size + "SECOND" + "b" * (size - 6) + "c" * size))
    assert "SECOND" in notes and notes.count("fine") == 2


def test_summary_uses_the_digest_of_the_whole_file(client, session_factory, monkeypatch) -> None:
    import app.services.study as study
    from app.db.models import Resource
    from app.services.resource_ingestion import create_text_resource

    headers, context_id, first, _ = _learner(client)
    owner = UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])
    with session_factory() as db:
        resource = asyncio.run(create_text_resource(db, owner_id=owner, context_id=UUID(context_id),
                                                    title="Long book", text="chapter one. " * 3000,
                                                    study_session_id=UUID(first)))
        # Longer than one context chunk, so a per-chunk cut would drop the last chapter.
        db.get(Resource, resource.id).digest = "DIGEST: " + "chapter notes. " * 300 + "LAST-CHAPTER-ZEPHYR"
        db.commit()
    provider = _CapturingProvider()
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: provider)
    res = client.post(f"/api/v1/study/sessions/{first}/messages", headers=headers,
                      json={"content": "Summarize this document"})
    assert res.status_code == 200, res.text
    assert "DIGEST:" in provider.prompts[-1] and "LAST-CHAPTER-ZEPHYR" in provider.prompts[-1]
