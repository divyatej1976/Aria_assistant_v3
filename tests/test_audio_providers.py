"""TTS/STT provider selection: cloud chain order and local fallback.

Regression for the production container finding: `auto` used to fall straight
to the local pyttsx3 provider, which cannot run in a headless container, so
every artifact failed. The chain now prefers Groq (GROQ_API_KEY), then the
OpenAI-compatible key, and keeps local as the last resort.
"""

import pytest

from app.ai.providers import (
    ChainedTTSProvider,
    CloudSTTProvider,
    CloudTTSProvider,
    GroqSTTProvider,
    GroqTTSProvider,
    LocalTTSProvider,
)
from app.core.errors import ValidationError


class _Settings:
    def __init__(
        self,
        *,
        groq: str | None = None,
        tts_key: str | None = None,
        stt_key: str | None = None,
        provider: str = "auto",
        tts_model: str = "tts-model",
        tts_voice: str = "voice",
        stt_model: str = "stt-model",
    ) -> None:
        self.groq_api_key = groq
        self.aria_tts_api_key = tts_key
        self.aria_stt_api_key = stt_key
        self.aria_tts_provider = provider
        self.aria_tts_model = tts_model
        self.aria_tts_voice = tts_voice
        self.aria_stt_model = stt_model


class _FakeProvider:
    def __init__(self, *, fail: bool = False, result: tuple = (b"A", "audio/wav", 1)) -> None:
        self.fail = fail
        self.result = result

    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        if self.fail:
            raise RuntimeError("boom")
        return self.result


def test_auto_chain_prefers_groq_then_openai_then_local(monkeypatch) -> None:
    from app.services import audio as audio_mod

    monkeypatch.setattr(audio_mod, "get_settings", lambda: _Settings(groq="g", tts_key="o"))
    provider = audio_mod.get_tts_provider()
    assert isinstance(provider, ChainedTTSProvider)
    assert [type(p) for p in provider.providers] == [
        GroqTTSProvider,
        CloudTTSProvider,
        LocalTTSProvider,
    ]


def test_auto_without_keys_is_local_only(monkeypatch) -> None:
    from app.services import audio as audio_mod

    monkeypatch.setattr(audio_mod, "get_settings", lambda: _Settings())
    provider = audio_mod.get_tts_provider()
    assert isinstance(provider, ChainedTTSProvider)
    assert [type(p) for p in provider.providers] == [LocalTTSProvider]


def test_explicit_local_ignores_cloud_keys(monkeypatch) -> None:
    from app.services import audio as audio_mod

    monkeypatch.setattr(
        audio_mod, "get_settings", lambda: _Settings(groq="g", tts_key="o", provider="local")
    )
    assert isinstance(audio_mod.get_tts_provider(), LocalTTSProvider)


def test_cloud_without_keys_falls_back_to_local(monkeypatch) -> None:
    from app.services import audio as audio_mod

    monkeypatch.setattr(audio_mod, "get_settings", lambda: _Settings(provider="cloud"))
    assert isinstance(audio_mod.get_tts_provider(), LocalTTSProvider)


def test_chain_first_success_wins() -> None:
    chain = ChainedTTSProvider([_FakeProvider(fail=True), _FakeProvider()])
    data, content_type, duration = chain.generate(text="hi")
    assert (data, content_type, duration) == (b"A", "audio/wav", 1)


def test_chain_raises_when_every_provider_fails() -> None:
    chain = ChainedTTSProvider([_FakeProvider(fail=True), _FakeProvider(fail=True)])
    with pytest.raises(RuntimeError, match="all TTS providers failed"):
        chain.generate(text="hi")


@pytest.mark.parametrize("fallback_succeeds", [True, False])
def test_chain_does_not_expose_provider_exception_body(caplog, fallback_succeeds):
    class PrivateFailure:
        def generate(self, *, text):
            raise RuntimeError(f"private learner prompt={text} token=private-provider-secret")

    providers = [PrivateFailure()]
    if fallback_succeeds:
        providers.append(_FakeProvider())
    chain = ChainedTTSProvider(providers)
    if fallback_succeeds:
        assert chain.generate(text="confidential study text") == (b"A", "audio/wav", 1)
    else:
        with pytest.raises(RuntimeError) as error:
            chain.generate(text="confidential study text")
        assert str(error.value) == "all TTS providers failed"
    assert "confidential study text" not in caplog.text
    assert "private-provider-secret" not in caplog.text
    assert "provider=PrivateFailure error_type=RuntimeError" in caplog.text


def test_stt_prefers_groq_then_openai_key(monkeypatch) -> None:
    from app.services import audio as audio_mod

    monkeypatch.setattr(audio_mod, "get_settings", lambda: _Settings(groq="g", stt_key="o"))
    assert isinstance(audio_mod.get_stt_provider(), GroqSTTProvider)

    monkeypatch.setattr(audio_mod, "get_settings", lambda: _Settings(stt_key="o"))
    assert isinstance(audio_mod.get_stt_provider(), CloudSTTProvider)


def test_stt_unconfigured_raises_validation_error(monkeypatch) -> None:
    from app.services import audio as audio_mod

    monkeypatch.setattr(audio_mod, "get_settings", lambda: _Settings())
    with pytest.raises(ValidationError):
        audio_mod.get_stt_provider()


@pytest.mark.parametrize("text", ["hello world", "- Learner: Explain caf\u00e9 notes", "--help"])
def test_local_tts_prefers_espeak_ng_subprocess(monkeypatch, text) -> None:
    """Container path: espeak-ng writes WAV headless, no pyttsx3 needed."""
    import shutil
    import subprocess

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/espeak-ng")

    class _Completed:
        returncode = 0

    def _fake_run(cmd, *, input=None, capture_output=False, timeout=None):
        assert cmd[0] == "/usr/bin/espeak-ng"
        assert cmd[-1] == "--stdin"
        assert input == text.encode("utf-8")
        assert text not in cmd
        with open(cmd[cmd.index("-w") + 1], "wb") as handle:
            import io
            import wave

            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as writer:
                writer.setnchannels(1)
                writer.setsampwidth(2)
                writer.setframerate(8000)
                writer.writeframes(b"\x00\x00" * 16000)
            handle.write(buffer.getvalue())
        return _Completed()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    data, content_type, duration = LocalTTSProvider().generate(text=text)
    assert data.startswith(b"RIFF")
    assert content_type == "audio/wav"
    assert duration == 2


def test_local_tts_without_binary_falls_back_with_clear_error(monkeypatch) -> None:
    """No espeak-ng and no pyttsx3: fail with an actionable message."""
    import shutil
    import sys

    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setitem(sys.modules, "pyttsx3", None)
    with pytest.raises(RuntimeError, match="espeak-ng"):
        LocalTTSProvider().generate(text="hi")


def test_local_tts_espeak_failure_falls_through(monkeypatch) -> None:
    """Non-zero espeak-ng exit must not produce empty audio silently."""
    import shutil
    import subprocess
    import sys

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/espeak-ng")

    class _Failed:
        returncode = 1

    def _fake_run(cmd, *, input=None, capture_output=False, timeout=None):
        return _Failed()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    monkeypatch.setitem(sys.modules, "pyttsx3", None)
    with pytest.raises(RuntimeError, match="espeak-ng"):
        LocalTTSProvider().generate(text="hi")
