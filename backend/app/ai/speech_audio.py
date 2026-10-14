"""Lossless speech segmentation and measured PCM WAV assembly."""

import io
import math
import wave


def speech_segments(text: str, *, limit: int = 4000) -> list[str]:
    if limit < 1:
        raise ValueError("Speech segment limit must be positive")
    segments: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary + 1
        segments.append(text[start:end])
        start = end
    return segments


def assemble_wav(parts: list[bytes]) -> tuple[bytes, int]:
    """Validate every segment; return one WAV and its actual rounded-up duration."""
    if not parts:
        raise RuntimeError("No audio was produced")
    frames: list[bytes] = []
    expected = None
    count = 0
    try:
        for data in parts:
            with wave.open(io.BytesIO(data), "rb") as reader:
                parameters = (reader.getnchannels(), reader.getsampwidth(), reader.getframerate())
                if reader.getcomptype() != "NONE" or min(parameters) <= 0:
                    raise ValueError("Unsupported WAV format")
                if expected is not None and parameters != expected:
                    raise ValueError("Inconsistent speech segment formats")
                expected = parameters
                raw = reader.readframes(reader.getnframes())
                frame_size = parameters[0] * parameters[1]
                if not raw or len(raw) != reader.getnframes() * frame_size:
                    raise ValueError("Incomplete WAV audio")
                frames.append(raw)
                count += len(raw) // frame_size
    except (wave.Error, EOFError, ValueError) as exc:
        raise RuntimeError("Speech provider returned invalid or incompatible WAV audio") from exc
    assert expected is not None
    output = io.BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setnchannels(expected[0])
        writer.setsampwidth(expected[1])
        writer.setframerate(expected[2])
        for raw in frames:
            writer.writeframes(raw)
    return output.getvalue(), max(1, math.ceil(count / expected[2]))
