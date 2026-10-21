import io
import wave

import httpx
import pytest

from app.ai.providers import CloudTTSProvider, GroqTTSProvider
from app.ai.speech_audio import assemble_wav, speech_segments


def wav_bytes(frames: int = 8000, *, sample_rate: int = 8000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(b"\x01\x00" * frames)
    return buffer.getvalue()


@pytest.mark.parametrize("provider", [
    CloudTTSProvider(api_key="test"),
    GroqTTSProvider(api_key="test", model="test", voice="test"),
])
def test_cloud_speech_contains_the_end_and_measures_all_segments(provider, monkeypatch):
    source = ("A complete sentence about binary search. " * 350) + "DISTINCTIVE FINAL SENTENCE."
    sent: list[str] = []
    def post(url, **kwargs):
        sent.append(kwargs["json"]["input"])
        assert kwargs["json"]["response_format"] == "wav"
        return httpx.Response(200, content=wav_bytes(), request=httpx.Request("POST", url))

    monkeypatch.setattr("app.ai.providers.httpx.post", post)
    data, content_type, duration = provider.generate(text=source)
    assert "".join(sent) == source
    assert all(0 < len(segment) <= 4000 for segment in sent)
    assert sent[-1].endswith("DISTINCTIVE FINAL SENTENCE.")
    assert content_type == "audio/wav"
    assert duration == len(sent)
    with wave.open(io.BytesIO(data), "rb") as reader:
        assert reader.getnframes() == len(sent) * 8000


def test_speech_does_not_return_partial_audio_after_a_later_failure(monkeypatch):
    calls = 0
    def post(url, **kwargs):
        nonlocal calls
        calls += 1
        status = 200 if calls == 1 else 503
        return httpx.Response(status, content=wav_bytes(), request=httpx.Request("POST", url))
    monkeypatch.setattr("app.ai.providers.httpx.post", post)
    with pytest.raises(httpx.HTTPStatusError):
        CloudTTSProvider(api_key="test").generate(text="long material " * 800)
    assert calls == 2


def test_speech_segments_preserve_offsets_even_without_word_boundaries():
    source = "x" * 9000
    segments = speech_segments(source)
    assert list(map(len, segments)) == [4000, 4000, 1000]
    assert "".join(segments) == source


def test_wav_assembly_rejects_invalid_or_inconsistent_audio():
    with pytest.raises(RuntimeError, match="WAV"):
        assemble_wav([b"invalid"])
    with pytest.raises(RuntimeError, match="WAV"):
        assemble_wav([wav_bytes(), wav_bytes(sample_rate=16000)])


def test_resource_speech_uses_original_text_without_chunk_overlap(client, monkeypatch):
    session = client.post("/api/v1/auth/register", json={
        "email": "speech-source@example.com", "password": "correct-horse-9", "display_name": "Learner",
    }).json()
    headers = {"Authorization": "Bearer " + session["access_token"]}
    context = client.post("/api/v1/contexts", headers=headers, json={"title": "Speech"}).json()
    source = "UNIQUE INTRO. " + ("The full resource should be spoken exactly once. " * 90) + "UNIQUE END."
    resource = client.post("/api/v1/resources/text", headers=headers, json={
        "context_id": context["id"], "title": "Complete source", "text": source,
    }).json()
    assert resource["chunk_count"] > 1
    captured = {}
    class TTS:
        def generate(self, *, text):
            captured["text"] = text
            return wav_bytes(), "audio/wav", 1
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: TTS())
    response = client.post(f"/api/v1/audio/resources/{resource['id']}/generate", headers=headers)
    assert response.status_code == 201
    assert response.json()["status"] == "READY"
    assert captured["text"] == source
