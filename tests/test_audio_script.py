"""Audio episodes explain the material (one tutor, or tutor + learner) instead of reading it aloud."""

from tests.test_audio import MATERIAL, create_context, headers, register, tmp_audio_storage  # noqa: F401 (fixture)

from app.services.audio_script import parse_turns


def test_dialogue_is_split_into_speakers_and_merges_runs() -> None:
    script = "TUTOR: Locks protect data.\n**LEARNER:** Why two phases?\nLEARNER: And when do they end?\nTUTOR: At commit."
    assert parse_turns(script, "conversation") == [
        ("tutor", "Locks protect data."),
        ("learner", "Why two phases? And when do they end?"),
        ("tutor", "At commit."),
    ]
    assert parse_turns("  Just one voice.  ", "explainer") == [("tutor", "Just one voice.")]


def _wait_until_done(client, token: str, episode: dict) -> dict:
    """Episodes are written and voiced in the background; poll like the Audio page does."""
    import time

    for _ in range(200):
        episode = client.get(f"/api/v1/audio/{episode['id']}", headers=headers(token)).json()
        if episode["status"] in ("READY", "FAILED"):
            break
        time.sleep(0.1)
    return episode


class _ScriptWriter:
    def __init__(self, script: str) -> None:
        self.script = script
        self.prompts: list[str] = []

    async def generate_text(self, *, system: str, user: str, prompt_version=None, temperature=0.0) -> str:
        self.prompts.append(user)
        return self.script


class _VoiceRecorder:
    """Records which voice spoke each line; returns tiny valid WAV clips."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def generate(self, *, text: str, voice: str | None = None) -> tuple[bytes, str, int]:
        import io
        import wave

        self.calls.append((text, voice))
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as clip:
            clip.setnchannels(1)
            clip.setsampwidth(2)
            clip.setframerate(8000)
            clip.writeframes(b"\x00\x00" * 800)
        return buffer.getvalue(), "audio/wav", 1


def test_conversation_episode_uses_two_voices_and_saves_the_script(client, monkeypatch, tmp_audio_storage) -> None:  # noqa: F811
    writer = _ScriptWriter("TUTOR: Two-phase locking has two phases.\nLEARNER: What happens at commit?\nTUTOR: Locks are released.")
    voices = _VoiceRecorder()
    monkeypatch.setattr("app.ai.registry.get_llm_provider_for_owner", lambda db, owner_id: writer)
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: voices)
    token = register(client, "dialogue-audio@example.com")["access_token"]
    cid = create_context(client, token)

    response = client.post("/api/v1/audio/text/generate", headers=headers(token),
                           json={"context_id": cid, "title": "Locking", "text": MATERIAL, "style": "conversation"})

    assert response.status_code == 201, response.text
    assert response.json()["status"] in ("PENDING", "PROCESSING", "READY")  # the request does not wait
    episode = _wait_until_done(client, token, response.json())
    assert episode["status"] == "READY", episode
    assert "Learner: What happens at commit?" in episode["text"]  # the transcript is the lesson, not the source
    assert "do not describe the file" in writer.prompts[-1]
    assert [voice for _, voice in voices.calls] == [None, "troy", None]  # learner lines use the second voice


def test_long_sources_are_condensed_before_scripting(client, monkeypatch, tmp_audio_storage) -> None:  # noqa: F811
    writer = _ScriptWriter("A short lesson.")
    monkeypatch.setattr("app.ai.registry.get_llm_provider_for_owner", lambda db, owner_id: writer)
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: _VoiceRecorder())
    token = register(client, "long-audio@example.com")["access_token"]
    cid = create_context(client, token)

    long_text = (MATERIAL + " ") * 100  # ~36k characters: past the old 20k wall, still one part
    response = client.post("/api/v1/audio/text/generate", headers=headers(token),
                           json={"context_id": cid, "title": "Long notes", "text": long_text})

    assert response.status_code == 201, response.text
    episode = response.json()
    assert episode["status"] in ("PENDING", "PROCESSING", "READY")  # long sources finish in the background
    import time

    for _ in range(100):
        episode = client.get(f"/api/v1/audio/{episode['id']}", headers=headers(token)).json()
        if episode["status"] in ("READY", "FAILED"):
            break
        time.sleep(0.1)
    assert episode["status"] == "READY", episode
    assert episode["text"] == "A short lesson."
    # Every 6k-character section is condensed (36k -> 6 sections), none skipped.
    assert sum("Write concise notes" in prompt for prompt in writer.prompts) >= 4


def test_split_parts_cuts_long_sources_at_paragraphs() -> None:
    from app.services.audio_script import MAX_PARTS, PART_CHARS, split_parts

    assert split_parts("short") == ["short"]
    text = "\n\n".join(f"Paragraph {i}. " + "x" * 900 for i in range(130))  # ~120k characters
    parts = split_parts(text)
    assert len(parts) == 3 and "".join(parts) == text  # nothing lost or duplicated
    assert all(part.startswith("Paragraph") for part in parts)  # cut at a paragraph break
    assert len(split_parts("y" * (PART_CHARS * 20))) == MAX_PARTS


def test_very_long_sources_become_a_series_of_parts(client, monkeypatch, tmp_audio_storage) -> None:  # noqa: F811
    writer = _ScriptWriter("A part of the lesson.")
    monkeypatch.setattr("app.ai.registry.get_llm_provider_for_owner", lambda db, owner_id: writer)
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: _VoiceRecorder())
    monkeypatch.setattr("app.services.condense.RETRY_WAITS", (0,))
    token = register(client, "series-audio@example.com")["access_token"]
    cid = create_context(client, token)

    long_text = "\n\n".join(f"Chapter {i}. " + MATERIAL for i in range(300))  # ~110k characters
    episode = client.post("/api/v1/audio/text/generate", headers=headers(token),
                          json={"context_id": cid, "title": "Big book", "text": long_text}).json()
    import time

    for _ in range(200):
        episode = client.get(f"/api/v1/audio/{episode['id']}", headers=headers(token)).json()
        if episode["status"] in ("READY", "FAILED"):
            break
        time.sleep(0.1)
    assert episode["status"] == "READY", episode
    assert episode["text"].startswith("[Part 1 of 3 · 0:00]\nA part of the lesson.")
    assert "[Part 3 of 3 · " in episode["text"]
    assert any("part 3 of 3" in prompt and "series is complete" in prompt for prompt in writer.prompts)
    # Part 1 previews part 2 from part 2's real opening, not a guess.
    part_one = next(prompt for prompt in writer.prompts if "part 1 of 3" in prompt)
    assert "part 2 picks up" in part_one and "'Chapter " in part_one
    listed = client.get(f"/api/v1/audio?context_id={cid}", headers=headers(token)).json()
    assert [part["part"] for part in listed[0]["parts"]] == [1, 2, 3]
    assert listed[0]["parts"][1]["start_seconds"] > 0  # later parts start later in the file


class _FailingWriter(_ScriptWriter):
    async def generate_text(self, **kwargs) -> str:
        raise RuntimeError("provider down")


def test_when_no_lesson_can_be_written_the_chat_is_not_read_aloud(client, monkeypatch, tmp_audio_storage) -> None:  # noqa: F811
    voices = _VoiceRecorder()
    monkeypatch.setattr("app.ai.registry.get_llm_provider_for_owner", lambda db, owner_id: _FailingWriter(""))
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: voices)
    monkeypatch.setattr("app.services.condense.RETRY_WAITS", (0,))
    token = register(client, "no-lesson@example.com")["access_token"]
    cid = create_context(client, token)

    response = client.post("/api/v1/audio/text/generate", headers=headers(token),
                           json={"context_id": cid, "title": "Locking", "text": MATERIAL})
    episode = _wait_until_done(client, token, response.json())

    assert episode["status"] == "FAILED"
    assert "couldn't write the lesson" in episode["error_detail"]
    assert voices.calls == []  # nothing was read aloud


def test_cancelled_episode_is_not_recreated(client, monkeypatch, tmp_audio_storage) -> None:  # noqa: F811
    import threading

    gate = threading.Event()

    class _SlowWriter(_ScriptWriter):
        async def generate_text(self, **kwargs) -> str:
            gate.wait(5)
            return "A lesson."

    monkeypatch.setattr("app.ai.registry.get_llm_provider_for_owner", lambda db, owner_id: _SlowWriter(""))
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: _VoiceRecorder())
    token = register(client, "cancel-audio@example.com")["access_token"]
    cid = create_context(client, token)

    episode = client.post("/api/v1/audio/text/generate", headers=headers(token),
                          json={"context_id": cid, "title": "Locking", "text": MATERIAL}).json()
    assert client.delete(f"/api/v1/audio/{episode['id']}", headers=headers(token)).status_code in (200, 204)
    gate.set()
    import time

    time.sleep(1.5)
    listed = client.get(f"/api/v1/audio?context_id={cid}", headers=headers(token)).json()
    assert listed == []  # cancelling removed it and the background job did not bring it back


def test_an_episode_handed_over_midway_resumes_without_re_recording(client, monkeypatch, tmp_audio_storage) -> None:  # noqa: F811
    from app.services import jobs

    script = " ".join(f"Sentence {i} explains one idea about locking in plain words." for i in range(60))  # ~3.5k chars
    voices = _VoiceRecorder()
    monkeypatch.setattr("app.ai.registry.get_llm_provider_for_owner", lambda db, owner_id: _ScriptWriter(script))
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: voices)
    handed_over = []
    real_check = jobs.Progress.check_time

    def check_time(self) -> None:
        if not handed_over and self.data.get("pieces"):
            handed_over.append(True)
            raise jobs.Continue()  # as if the worker's 5 minutes were up after the first piece
        real_check(self)
    monkeypatch.setattr(jobs.Progress, "check_time", check_time)
    token = register(client, "resume-audio@example.com")["access_token"]
    cid = create_context(client, token)

    episode = client.post("/api/v1/audio/text/generate", headers=headers(token),
                          json={"context_id": cid, "title": "Locking", "text": MATERIAL}).json()
    episode = _wait_until_done(client, token, episode)

    assert handed_over and episode["status"] == "READY", episode
    spoken = [text for text, _ in voices.calls]
    assert len(spoken) == len(set(spoken)) >= 3  # every piece recorded exactly once across both workers
