"""Audio: text-to-speech generation, playback, progress, review, and STT."""

import logging
import re
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from threading import Event, Thread
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.ai.providers import (
    ChainedTTSProvider,
    CloudSTTProvider,
    CloudTTSProvider,
    GeminiTTSProvider,
    GroqSTTProvider,
    GroqTTSProvider,
    LocalTTSProvider,
    VoiceQuotaExceeded,
    VoicesUnavailable,
)
from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.models import (
    AudioArtifact,
    AudioProgress,
    ConversationMessage,
    LearningContext,
    Note,
    Resource,
    ResourceChunk,
    StudySession,
)
from app.services.audio_storage import get_audio_storage
from app.services.progress import record_activity

logger = logging.getLogger(__name__)

NOTE = "NOTE"
RESOURCE = "RESOURCE"
# Guard against oversized `audio_artifacts.text`/binary rows and long
# synchronous TTS calls: sources above this many characters are rejected.
# Cloud providers segment the complete source within each request's limit.
MAX_AUDIO_CHARS = 20_000
# With the AI tutor the source is condensed into a lesson script first, so only
# reading a source aloud verbatim is held to MAX_AUDIO_CHARS.
MAX_SOURCE_CHARS = 400_000


class AudioSourceNotFound(ValidationError):
    """Owned source is absent; API adapters map this to a 404."""


async def generate_text_audio(db: Session, *, owner_id: UUID, context_id: UUID,
                              title: str, text: str, style: str = "explainer") -> AudioArtifact:
    from starlette.concurrency import run_in_threadpool

    from app.services.resource_ingestion import create_text_resource

    if not db.scalar(select(LearningContext).where(
        LearningContext.id == context_id, LearningContext.owner_id == owner_id,
    )):
        raise AudioSourceNotFound("Learning context not found")
    text, title = text.strip(), title.strip()
    if not text or not title:
        raise ValidationError("Enter a title and some text to create audio")
    if len(text) > MAX_SOURCE_CHARS:
        raise ValidationError("This is too long for one episode. Split it into a few parts.")
    resource = db.scalar(select(Resource).where(
        Resource.owner_id == owner_id, Resource.context_id == context_id,
        Resource.title == title, Resource.source_text == text, Resource.resource_type == "TEXT",
    ).order_by(Resource.created_at, Resource.id))
    if resource is None:
        resource = await create_text_resource(db, owner_id=owner_id,
            context_id=context_id, title=title, text=text)
    else:
        ready = db.scalar(select(AudioArtifact).where(
            AudioArtifact.owner_id == owner_id, AudioArtifact.source_type == RESOURCE,
            AudioArtifact.source_id == resource.id, AudioArtifact.status == "READY",
        ).order_by(AudioArtifact.created_at, AudioArtifact.id))
        if ready is not None and style == "explainer":
            return ready
    return await run_in_threadpool(start_audio, db, owner_id=owner_id,
                                  source_type=RESOURCE, source_id=resource.id, style=style)


def session_audio_source(db: Session, *, owner_id: UUID, session_id: UUID,
                         through_position: int | None = None) -> tuple[UUID, str, str, int]:
    session = db.scalar(select(StudySession).where(
        StudySession.id == session_id, StudySession.owner_id == owner_id,
    ))
    if session is None:
        raise AudioSourceNotFound("Conversation not found")
    query = select(ConversationMessage).where(
        ConversationMessage.study_session_id == session.id,
        ConversationMessage.owner_id == owner_id,
    )
    if through_position is not None:
        latest = db.scalar(select(func.max(ConversationMessage.position)).where(
            ConversationMessage.study_session_id == session.id, ConversationMessage.owner_id == owner_id,
        ))
        if through_position < 0 or latest is None or through_position > latest:
            raise ValidationError("Conversation cutoff must refer to existing messages")
        query = query.where(ConversationMessage.position <= through_position)
    messages = [m for m in db.scalars(query.order_by(ConversationMessage.position,
        ConversationMessage.created_at, ConversationMessage.id)).all() if not m.action]
    if not any(m.role in ("assistant", "aria") and m.content.strip() for m in messages):
        raise ValidationError("Get a tutor response before creating audio from this conversation")
    text = "\n\n".join(
        f"{'You' if m.role == 'user' else 'ARIA'}: {m.content.strip()}"
        for m in messages if m.role in ("user", "assistant", "aria") and m.content.strip()
    )
    from app.services.study import topic_title

    first_question = next((m.content for m in messages if m.role == "user"), "Tutor conversation")
    # The episode is named for what the chat taught, not the first thing typed.
    title = session.title or topic_title(first_question)
    return session.context_id, title[:200], text, max(m.position for m in messages)


async def generate_session_audio(db: Session, *, owner_id: UUID, session_id: UUID,
                                 through_position: int | None = None, style: str = "explainer") -> AudioArtifact:
    context_id, title, text, _ = session_audio_source(db, owner_id=owner_id,
        session_id=session_id, through_position=through_position)
    return await generate_text_audio(db, owner_id=owner_id, context_id=context_id, title=title, text=text,
                                     style=style)


def get_tts_provider():
    """Provider chain: OpenAI TTS (OPENAI_API_KEY) -> Groq TTS (GROQ_API_KEY) -> Gemini TTS
    (GEMINI_API_KEY) -> OpenAI TTS (ARIA_TTS_API_KEY) -> local.

    'auto' keeps the local pyttsx3 fallback as the last resort so audio
    generation still works in containers without cloud access; 'cloud'
    restricts to cloud providers only (local if none configured, as before).
    """
    settings = get_settings()
    cloud: list = []
    openai_key = getattr(settings, "openai_api_key", None)
    if openai_key:
        cloud.append(CloudTTSProvider(api_key=openai_key, model=settings.aria_openai_tts_model,
                                      voice=settings.aria_openai_tts_voice,
                                      learner_voice=settings.aria_openai_tts_voice_2))
    if settings.groq_api_key:
        cloud.append(
            GroqTTSProvider(
                api_key=settings.groq_api_key,
                model=settings.aria_tts_model,
                voice=settings.aria_tts_voice,
            )
        )
    if getattr(settings, "gemini_api_key", None):
        cloud.append(GeminiTTSProvider(api_key=settings.gemini_api_key, model=settings.aria_gemini_tts_model,
                                       voice=settings.aria_gemini_tts_voice,
                                       learner_voice=settings.aria_gemini_tts_voice_2))
    if settings.aria_tts_api_key:
        cloud.append(CloudTTSProvider(api_key=settings.aria_tts_api_key))
    if settings.aria_tts_provider == "local":
        return LocalTTSProvider()
    if settings.aria_tts_provider == "cloud":
        if not cloud:
            return LocalTTSProvider()
        if len(cloud) == 1:
            return cloud[0]
        return ChainedTTSProvider(cloud)
    return ChainedTTSProvider([*cloud, LocalTTSProvider()])


def get_stt_provider():
    settings = get_settings()
    if getattr(settings, "openai_api_key", None):
        return CloudSTTProvider(api_key=settings.openai_api_key, model=settings.aria_openai_stt_model)
    if settings.groq_api_key:
        return GroqSTTProvider(api_key=settings.groq_api_key, model=settings.aria_stt_model)
    if settings.aria_stt_api_key:
        return CloudSTTProvider(api_key=settings.aria_stt_api_key)
    raise ValidationError(
        "Speech-to-text is not configured. Set OPENAI_API_KEY, GROQ_API_KEY or ARIA_STT_API_KEY "
        "to enable voice questions."
    )


def _source_text(
    db: Session, *, owner_id: UUID, source_type: str, source_id: UUID
) -> tuple[str, str]:
    if source_type == NOTE:
        note = db.scalar(
            select(Note).where(Note.id == source_id, Note.owner_id == owner_id)
        )
        if note is None:
            raise ValidationError("Note not found")
        text = note.body
        label = f"Note: {note.title}"
    elif source_type == RESOURCE:
        resource = db.scalar(
            select(Resource).where(Resource.id == source_id, Resource.owner_id == owner_id)
        )
        if resource is None:
            raise ValidationError("Resource not found")
        chunks = db.scalars(
            select(ResourceChunk)
            .where(ResourceChunk.resource_id == resource.id)
            .order_by(ResourceChunk.chunk_index)
        ).all()
        from app.services.audio_script import PART_CHARS

        # A ready digest covers a medium file in a few thousand characters; files long enough
        # to become a series are split from the full text so every part keeps its detail.
        full = resource.source_text or ""
        text = full if len(full) > PART_CHARS else resource.digest or full
        if not text.strip():
            # Legacy resources may have only overlapping retrieval chunks.
            pieces: list[str] = []
            previous = ""
            for chunk in chunks:
                current = chunk.content
                overlap = next((
                    size for size in range(min(120, len(previous), len(current)), 0, -1)
                    if previous[-size:] == current[:size]
                ), 0)
                pieces.append(current[overlap:])
                previous = current
            text = "".join(pieces)
        label = f"Resource: {resource.title}"
    else:
        raise ValidationError("Unsupported audio source")
    if not text.strip():
        raise ValidationError("No readable text in this source")
    if len(text) > MAX_SOURCE_CHARS:
        # Guard against oversized rows; anything shorter is condensed into a script.
        raise ValidationError("This source is too long for one episode. Split it into a few parts.")
    return text, label


def list_audio(
    db: Session, *, owner_id: UUID, context_id: UUID | None = None
) -> list[dict]:
    """Durable artifact listing (replaces the frontend localStorage index).

    Owner-scoped always; optionally narrowed to one learning context by
    joining through the polymorphic NOTE/RESOURCE source.
    """
    note_rows = db.execute(
        select(AudioArtifact, Note.title, Note.context_id)
        .join(Note, Note.id == AudioArtifact.source_id)
        .where(
            AudioArtifact.owner_id == owner_id,
            AudioArtifact.source_type == NOTE,
        )
    ).all()
    resource_rows = db.execute(
        select(AudioArtifact, Resource.title, Resource.context_id)
        .join(Resource, Resource.id == AudioArtifact.source_id)
        .where(
            AudioArtifact.owner_id == owner_id,
            AudioArtifact.source_type == RESOURCE,
        )
    ).all()
    # One batched progress query instead of N+1.
    artifact_ids = [a.id for a, _, _ in [*note_rows, *resource_rows]]
    from app.db.models import Job

    # What the background job is doing right now, e.g. "Recording part 2 of 4".
    active = select(Job).where(Job.kind == "audio", Job.target_id.in_(artifact_ids),
                               Job.status.in_(["queued", "running"]))
    step = {job.target_id: (job.progress or {}).get("label") for job in db.scalars(active)} if artifact_ids else {}
    progress_map: dict[UUID, AudioProgress] = {}
    if artifact_ids:
        for progress in db.scalars(
            select(AudioProgress).where(
                AudioProgress.owner_id == owner_id,
                AudioProgress.artifact_id.in_(artifact_ids),
            )
        ):
            progress_map[progress.artifact_id] = progress
    items: list[dict] = []
    for artifact, title, ctx in [*note_rows, *resource_rows]:
        if context_id is not None and ctx != context_id:
            continue
        progress = progress_map.get(artifact.id)
        items.append(
            {
                "id": str(artifact.id),
                "source_type": artifact.source_type,
                "source_id": str(artifact.source_id),
                "title": title,
                "status": artifact.status,
                "content_type": artifact.content_type,
                "duration_seconds": artifact.duration_seconds,
                "parts": episode_parts(artifact.text) if artifact.status == "READY" else [],
                "step": step.get(artifact.id),
                "error_detail": artifact.error_detail if artifact.status == "FAILED" else None,
                "position_seconds": progress.position_seconds if progress else 0,
                "completed": progress.completed if progress else False,
                "created_at": artifact.created_at,
            }
        )
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return items


def get_owned_artifact(db: Session, *, owner_id: UUID, artifact_id: UUID) -> AudioArtifact:
    artifact = db.scalar(
        select(AudioArtifact).where(
            AudioArtifact.id == artifact_id, AudioArtifact.owner_id == owner_id
        )
    )
    if artifact is None:
        raise ValidationError("Audio not found")
    return artifact


LEASE_SECONDS = 120
MAX_RECOVERY_ATTEMPTS = 3


def _claimable(now):
    return or_(
        AudioArtifact.status != "PROCESSING",
        AudioArtifact.lease_until.is_(None),
        AudioArtifact.lease_until <= now,
    )


@contextmanager
def _renew_audio_lease(db: Session, artifact_id: UUID, token: UUID):
    """Renew using independent transactions while the provider blocks."""
    stop = Event()
    bind = db.get_bind()

    def renew():
        while not stop.wait(LEASE_SECONDS / 4):
            try:
                with Session(bind) as heartbeat:
                    result = heartbeat.execute(
                        update(AudioArtifact).where(
                            AudioArtifact.id == artifact_id,
                            AudioArtifact.generation_token == token,
                            AudioArtifact.status == "PROCESSING",
                        ).values(lease_until=datetime.now(UTC) + timedelta(seconds=LEASE_SECONDS))
                    )
                    heartbeat.commit()
                    if result.rowcount != 1:
                        return
            except Exception:
                logger.exception("audio lease renewal failed")
                # Without renewal the lease expires; fencing prevents stale writes.

    thread = Thread(target=renew, daemon=True, name="aria-audio-lease")
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=5)


def _speak(tts, turns) -> tuple[bytes, str, int]:
    """Voice each turn; the learner gets the second voice, falling back to the first."""
    from app.ai.speech_audio import assemble_wav

    second = get_settings().aria_tts_voice_2
    clips: list[tuple[bytes, str, int]] = []
    for speaker, line in turns:
        try:
            clips.append(tts.generate(text=line, **({"voice": second} if speaker == "learner" else {})))
        except Exception:
            if speaker != "learner":
                raise
            clips.append(tts.generate(text=line))
    if len(clips) == 1:
        return clips[0]
    data, duration = assemble_wav([clip[0] for clip in clips])
    return data, "audio/wav", duration


PART_MARK = re.compile(r"^\[Part (\d+) of (\d+) · (\d+):(\d\d)\]$", re.M)


# An episode with a script but no recording: the player reads it with the device's own voice.
DEVICE_VOICE = "text/plain"


def script_transcript(parts, *, conversation: bool) -> str:
    """The episode script as the player shows (and the device voice reads) it."""
    def turns_text(turns) -> str:
        if conversation:
            return "\n\n".join(f"{'Learner' if who == 'learner' else 'Tutor'}: {line}" for who, line in turns)
        return "\n\n".join(line for _, line in turns)
    return "\n\n".join(turns_text(turns) for turns in parts)


def _speak_parts(tts, parts, *, conversation: bool, progress=None, owner_id: UUID | None = None,
                 job_id: UUID | None = None) -> tuple[bytes, str, int, str]:
    """Voice each part into one file; the transcript marks where each part starts.

    From a job, each part's recording is stored as soon as it is made, so a resumed job only
    records the parts still missing.
    """

    from app.ai.speech_audio import assemble_wav

    def transcript(turns) -> str:
        if conversation:
            return "\n\n".join(f"{'Learner' if who == 'learner' else 'Tutor'}: {line}" for who, line in turns)
        return "\n\n".join(line for _, line in turns)

    if progress is not None and owner_id is not None and job_id is not None:
        return _speak_in_pieces(tts, parts, transcript, progress=progress, owner_id=owner_id, job_id=job_id)
    if len(parts) == 1:
        return (*_speak(tts, parts[0]), transcript(parts[0]))
    clips, sections, start = [], [], 0
    for index, turns in enumerate(parts, start=1):
        data, _, seconds = _speak(tts, turns)
        clips.append(data)
        sections.append(f"[Part {index} of {len(parts)} · {start // 60}:{start % 60:02d}]\n{transcript(turns)}")
        start += seconds
    data, duration = assemble_wav(clips)
    return data, "audio/wav", duration, "\n\n".join(sections)


# One saved piece of speech: about 80 s of audio, so even a voice slower than real time
# (Gemini is ~1.5x) finishes a piece well inside one serverless request.
SPEECH_PIECE_CHARS = 1200


def _speak_in_pieces(tts, parts, transcript, *, progress, owner_id: UUID, job_id: UUID) -> tuple[bytes, str, int, str]:
    """Voice an episode piece by piece, storing each piece at once; a resumed job skips the saved ones."""
    from uuid import NAMESPACE_URL, uuid5

    from app.ai.speech_audio import assemble_wav, speech_segments

    second = get_settings().aria_tts_voice_2
    pieces = [(index, speaker, text) for index, turns in enumerate(parts) for speaker, line in turns
              for text in speech_segments(line, limit=SPEECH_PIECE_CHARS)]
    storage = get_audio_storage()
    saved = list(progress.data.get("pieces", []))[:len(pieces)]
    for number, (index, speaker, text) in enumerate(pieces):
        if number < len(saved):
            continue
        try:
            data, _, seconds = tts.generate(text=text, **({"voice": second} if speaker == "learner" else {}))
        except Exception:
            if speaker != "learner":
                raise
            data, _, seconds = tts.generate(text=text)  # the second voice is optional
        key = storage.save(owner_id=owner_id, artifact_id=uuid5(NAMESPACE_URL, f"{job_id}:piece:{number}"),
                           content_type="audio/wav", data=data)
        saved.append({"key": key, "seconds": seconds, "part": index})
        where = f"part {index + 1} of {len(parts)}, " if len(parts) > 1 else ""
        progress.save(pieces=saved, label=f"Recording {where}{round(100 * (number + 1) / len(pieces))}%")
        if number < len(pieces) - 1:
            progress.check_time()
    clips = []
    for item in saved:
        data = storage.load(item["key"])
        if data is None:
            raise RuntimeError("a saved piece of this episode is missing")
        clips.append(data)
    data, duration = assemble_wav(clips)
    _remove_stored([item["key"] for item in saved])
    if len(parts) == 1:
        return data, "audio/wav", duration, transcript(parts[0])
    sections, start = [], 0
    for index, turns in enumerate(parts):
        sections.append(f"[Part {index + 1} of {len(parts)} · {start // 60}:{start % 60:02d}]\n{transcript(turns)}")
        start += sum(item["seconds"] for item in saved if item["part"] == index)
    return data, "audio/wav", duration, "\n\n".join(sections)


def episode_parts(text: str) -> list[dict]:
    """Part starts from the transcript markers, for the player's jump list."""
    return [{"part": int(m[1]), "start_seconds": int(m[3]) * 60 + int(m[4])} for m in PART_MARK.finditer(text or "")]


def start_audio(
    db: Session, *, owner_id: UUID, source_type: str, source_id: UUID, style: str = "explainer",
) -> AudioArtifact:
    """Return at once with a PENDING episode that is written and voiced in the background.

    Writing a lesson and voicing it takes minutes, longer than anyone should watch a dialog. The
    learner can leave the page; the Audio list polls until READY, deleting it cancels, and the
    audio queue recovers it if this process stops first. Without the AI tutor the source is only
    read aloud, which stays in the request.
    """
    from app.ai.registry import get_llm_provider_for_owner

    text, _ = _source_text(db, owner_id=owner_id, source_type=source_type, source_id=source_id)
    if get_llm_provider_for_owner(db, owner_id=owner_id) is None:
        return generate_audio(db, owner_id=owner_id, source_type=source_type, source_id=source_id, style=style)
    artifact = db.scalar(select(AudioArtifact).where(
        AudioArtifact.owner_id == owner_id, AudioArtifact.source_type == source_type,
        AudioArtifact.source_id == source_id,
    ).order_by(AudioArtifact.created_at, AudioArtifact.id))
    if artifact is None:
        artifact = AudioArtifact(owner_id=owner_id, source_type=source_type, source_id=source_id,
                                 text=text, status="PENDING", style=style)
        db.add(artifact)
    elif artifact.status != "PROCESSING":
        artifact.status, artifact.style, artifact.error_detail = "PENDING", style, None
    db.commit()
    db.refresh(artifact)
    from app.services import jobs

    # Any free worker makes it; several episodes are made side by side.
    jobs.enqueue(db, kind="audio", owner_id=owner_id, target_id=artifact.id)
    db.refresh(artifact)
    return artifact


def generate_audio(
    db: Session, *, owner_id: UUID, source_type: str, source_id: UUID,
    provider=None, recovery: bool = False, reuse_ready: bool = False, style: str | None = None,
    progress=None, job_id: UUID | None = None,
) -> AudioArtifact:
    """Claim one source atomically, synthesize outside its transaction, then fence publication.

    From a job (`progress`), each part is saved as it is finished; when the worker runs out of
    time the claim is handed back (PENDING) and the next worker resumes from the saved parts.
    """
    source_model = Note if source_type == NOTE else Resource if source_type == RESOURCE else None
    if source_model is None:
        raise ValidationError("Unsupported audio source")
    # A source-row write serializes first creation as well as existing claims
    # on SQLite/PostgreSQL. No source update is committed to learner content.
    locked = db.execute(update(source_model).where(
        source_model.id == source_id, source_model.owner_id == owner_id,
    ).values(updated_at=source_model.updated_at))
    if locked.rowcount != 1:
        db.rollback()
        raise ValidationError("Audio source not found")
    from app.ai.registry import get_llm_provider_for_owner

    try:
        text, label = _source_text(db, owner_id=owner_id, source_type=source_type, source_id=source_id)
        llm = get_llm_provider_for_owner(db, owner_id=owner_id)
        if llm is None and len(text) > MAX_AUDIO_CHARS:
            raise ValidationError(
                f"This is too long to read aloud (over {MAX_AUDIO_CHARS:,} characters) without the AI tutor, "
                "which condenses long sources. Add a Groq key or split it into parts."
            )
    except Exception:
        db.rollback()
        raise
    artifact = db.scalar(select(AudioArtifact).where(
        AudioArtifact.owner_id == owner_id,
        AudioArtifact.source_type == source_type,
        AudioArtifact.source_id == source_id,
    ).order_by(AudioArtifact.created_at, AudioArtifact.id).execution_options(populate_existing=True))
    if reuse_ready and artifact is not None and artifact.status == "READY":
        # Check after taking the source-row lock, closing the race between
        # an early READY lookup and another worker publishing the same source.
        db.commit()
        return artifact
    if artifact is None:
        artifact = AudioArtifact(owner_id=owner_id, source_type=source_type,
                                 source_id=source_id, text=text, status="PENDING")
        db.add(artifact)
        db.flush()
    style = style or artifact.style or "explainer"
    now = datetime.now(UTC)
    token = uuid4()
    eligibility = _claimable(now)
    if recovery:
        eligibility = and_(eligibility, AudioArtifact.status.in_(["PENDING", "PROCESSING"]))
        if artifact.generation_attempts >= MAX_RECOVERY_ATTEMPTS:
            db.execute(update(AudioArtifact).where(
                AudioArtifact.id == artifact.id, eligibility,
            ).values(status="FAILED", lease_until=None, generation_token=None,
                     error_detail="Audio recovery limit reached. Please retry manually."))
            db.commit()
            db.refresh(artifact)
            return artifact
    attempts = AudioArtifact.generation_attempts + 1 if recovery else 1
    claimed = db.execute(update(AudioArtifact).where(
        AudioArtifact.id == artifact.id, eligibility,
    ).values(status="PROCESSING", text=text, error_detail=None, style=style,
             generation_token=token, lease_until=now + timedelta(seconds=LEASE_SECONDS),
             generation_attempts=attempts).execution_options(synchronize_session=False))
    db.commit()
    db.refresh(artifact)
    if claimed.rowcount != 1:
        return artifact
    artifact_id = artifact.id
    old_key = artifact.storage_key
    new_key = None
    with _renew_audio_lease(db, artifact_id, token):
        from app.services.audio_script import script_parts

        # Explain the material like a lesson; without the AI tutor, read it aloud as before.
        title = label.split(": ", 1)[-1]
        from app.services.jobs import Continue

        try:
            parts = script_parts(llm, title=title, text=text,
                                 style="conversation" if style == "conversation" else "explainer",
                                 cancelled=lambda: db.get(AudioArtifact, artifact_id, populate_existing=True) is None,
                                 progress=progress)
            if parts is None and llm is not None:
                # Reading a chat or file aloud is not a lesson; fail clearly so the learner can retry.
                raise ValidationError("ARIA couldn't write the lesson just now (the AI is busy). "
                                      "Retry in a minute.")
            if parts is None and len(text) > MAX_AUDIO_CHARS:
                raise ValidationError("The lesson script could not be written and this is too long to read aloud.")
            parts = parts or [[("tutor", text)]]
            try:
                audio_bytes, content_type, duration, spoken = _speak_parts(
                    provider or get_tts_provider(), parts, conversation=style == "conversation",
                    progress=progress, owner_id=owner_id, job_id=job_id)
            except (VoiceQuotaExceeded, VoicesUnavailable) as exc:
                # No cloud voice today (the free tier allows only a few a day): keep the written
                # episode and let the learner's device read it aloud instead of failing it.
                logger.info("cloud voices unavailable, episode uses the device voice reason=%s", type(exc).__name__)
                spoken = script_transcript(parts, conversation=style == "conversation")
                audio_bytes, content_type = None, DEVICE_VOICE
                duration = max(1, round(len(spoken.split()) / 2.5))  # about 150 words a minute
        except Continue:
            # Out of time, not failed: hand the episode back so the next worker resumes it.
            db.rollback()
            db.execute(update(AudioArtifact).where(
                AudioArtifact.id == artifact_id, AudioArtifact.generation_token == token,
            ).values(status="PENDING", lease_until=None, generation_token=None))
            db.commit()
            raise
        except Exception as exc:
            db.rollback()
            logger.warning("audio generation failed error_type=%s", type(exc).__name__)
            db.execute(update(AudioArtifact).where(
                AudioArtifact.id == artifact_id, AudioArtifact.generation_token == token,
            ).values(status="FAILED", lease_until=None, generation_token=None,
                     error_detail=str(exc) if isinstance(exc, ValidationError)
                     else "Audio generation failed. Please retry or check audio setup."))
            db.commit()
        else:
            try:
                # A recovered/older worker cannot overwrite another generation's file.
                new_key = None if audio_bytes is None else get_audio_storage().save(
                    owner_id=owner_id, artifact_id=token, content_type=content_type, data=audio_bytes)
                fallback_bytes = None
            except Exception:
                logger.exception("audio storage failed; keeping bytes in DB")
                fallback_bytes = audio_bytes
            published = db.execute(update(AudioArtifact).where(
                AudioArtifact.id == artifact_id, AudioArtifact.generation_token == token,
            ).values(status="READY", lease_until=None, generation_token=None, text=spoken,
                     content_type=content_type, duration_seconds=duration,
                     storage_key=new_key, audio_bytes=fallback_bytes))
            db.commit()
            if published.rowcount == 1:
                if old_key != new_key:
                    _remove_stored([old_key])
            else:
                _remove_stored([new_key])
    current = db.get(AudioArtifact, artifact_id, populate_existing=True)
    if current is None:
        raise ValidationError("Audio source was deleted during generation")
    return current


def process_audio_queue(db: Session, *, limit: int = 5, provider=None) -> int:
    """Recover pending or expired work; active claims are never selected."""
    artifacts = list(db.scalars(select(AudioArtifact).where(
        AudioArtifact.status.in_(["PENDING", "PROCESSING"]),
        _claimable(datetime.now(UTC)),
    ).order_by(AudioArtifact.created_at).limit(limit)))
    processed = 0
    for artifact in artifacts:
        artifact_id, owner_id = artifact.id, artifact.owner_id
        source_type, source_id = artifact.source_type, artifact.source_id
        try:
            generate_audio(db, owner_id=owner_id, source_type=source_type,
                           source_id=source_id, provider=provider, recovery=True)
            processed += 1
        except ValidationError:
            db.rollback()
            # Clean up only actual orphans; oversized/invalid sources are failures.
            source_model = Note if source_type == NOTE else Resource
            source = db.scalar(select(source_model.id).where(
                source_model.id == source_id, source_model.owner_id == owner_id))
            if source is None:
                if db.get(AudioArtifact, artifact_id, populate_existing=True) is not None:
                    delete_audio(db, owner_id=owner_id, artifact_id=artifact_id)
            else:
                db.execute(update(AudioArtifact).where(
                    AudioArtifact.id == artifact_id, _claimable(datetime.now(UTC)),
                ).values(status="FAILED", error_detail="Audio source cannot be processed. Please check its content."))
                db.commit()
        except Exception:
            db.rollback()
            logger.exception("audio queue failed")
            # Do not overwrite an active claim. Its lease supports recovery.
    return processed


def load_audio_bytes(artifact: AudioArtifact) -> bytes | None:
    """Playback bytes: object storage first, legacy DB bytes as fallback."""
    if artifact.storage_key:
        data = get_audio_storage().load(artifact.storage_key)
        if data is not None:
            return data
    return artifact.audio_bytes


def _remove_stored(keys: list[str | None]) -> None:
    storage = get_audio_storage()
    for key in keys:
        if key:
            try:
                storage.delete(key)
            except Exception:
                logger.exception("audio storage delete failed")



def sweep_audio_files(db: Session, *, limit: int = 500, grace_seconds: int = 3600) -> dict:
    """Retry file cleanup after committed deletions and crash-created orphans.

    Unreferenced files are the durable cleanup work list. The grace period
    protects publication; active generation tokens protect long-running work.
    """
    storage = get_audio_storage()
    candidates = getattr(storage, "cleanup_candidates", None)
    result = {"scanned": 0, "deleted": 0, "failed": 0}
    if candidates is None:
        return result
    iterator = iter(candidates(before=datetime.now(UTC) - timedelta(seconds=max(3600, grace_seconds))))
    from itertools import islice

    while result["deleted"] < limit:
        batch = list(islice(iterator, 100))
        if not batch:
            break
        result["scanned"] += len(batch)
        tokens = [UUID(key.split("/")[1].rsplit(".", 1)[0]) for key in batch]
        rows = list(db.execute(select(
            AudioArtifact.storage_key, AudioArtifact.owner_id, AudioArtifact.generation_token,
        ).where(or_(AudioArtifact.storage_key.in_(batch), AudioArtifact.generation_token.in_(tokens)))))
        referenced = {key for key, _, _ in rows if key}
        active = {(str(owner), str(token)) for _, owner, token in rows if token}
        for key in batch:
            owner, file_name = key.split("/")
            token = file_name.rsplit(".", 1)[0]
            if key in referenced or (owner, token) in active:
                continue
            try:
                storage.delete(key)
                result["deleted"] += 1
            except Exception:
                result["failed"] += 1
                logger.exception("audio orphan cleanup failed")
            if result["deleted"] >= limit:
                break
    return result


def requeue_missing_audio(db: Session) -> int:
    """Operator-requested recovery after restoring a database without its audio volume."""
    changed = 0
    artifacts = db.scalars(select(AudioArtifact).where(
        AudioArtifact.status == "READY", AudioArtifact.audio_bytes.is_(None),
    ).execution_options(yield_per=100))
    for artifact in artifacts:
        # Device-voice episodes never had a file.
        if artifact.content_type == DEVICE_VOICE or load_audio_bytes(artifact) is not None:
            continue
        result = db.execute(update(AudioArtifact).where(
            AudioArtifact.id == artifact.id, AudioArtifact.status == "READY",
            AudioArtifact.storage_key == artifact.storage_key,
        ).values(status="PENDING", generation_token=None, lease_until=None,
                 generation_attempts=0, error_detail="Audio file missing after restore; awaiting regeneration."))
        changed += result.rowcount
    db.commit()
    return changed

def delete_audio(db: Session, *, owner_id: UUID, artifact_id: UUID) -> None:
    artifact = get_owned_artifact(db, owner_id=owner_id, artifact_id=artifact_id)
    # Execute child deletion before scheduling the parent DELETE: without an
    # ORM relationship, the unit of work cannot infer this FK ordering.
    db.execute(delete(AudioProgress).where(AudioProgress.artifact_id == artifact.id))
    storage_key = artifact.storage_key
    db.delete(artifact)
    db.commit()
    _remove_stored([storage_key])


def delete_artifacts_for_source(
    db: Session, *, owner_id: UUID, source_type: str, source_id: UUID
) -> None:
    # Children first: AudioProgress.artifact_id -> audio_artifacts (RESTRICT).
    artifact_ids = select(AudioArtifact.id).where(
        AudioArtifact.owner_id == owner_id,
        AudioArtifact.source_type == source_type,
        AudioArtifact.source_id == source_id,
    )
    db.execute(delete(AudioProgress).where(AudioProgress.artifact_id.in_(artifact_ids)))
    artifacts = db.scalars(
        select(AudioArtifact).where(
            AudioArtifact.owner_id == owner_id,
            AudioArtifact.source_type == source_type,
            AudioArtifact.source_id == source_id,
        )
    ).all()
    keys = [artifact.storage_key for artifact in artifacts]
    for artifact in artifacts:
        db.delete(artifact)
    db.commit()
    _remove_stored(keys)


def get_progress(db: Session, *, owner_id: UUID, artifact_id: UUID) -> AudioProgress:
    artifact = get_owned_artifact(db, owner_id=owner_id, artifact_id=artifact_id)
    progress = db.scalar(
        select(AudioProgress).where(
            AudioProgress.owner_id == owner_id, AudioProgress.artifact_id == artifact.id
        )
    )
    if progress is None:
        progress = AudioProgress(owner_id=owner_id, artifact_id=artifact.id)
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress


def save_progress(
    db: Session, *, owner_id: UUID, artifact_id: UUID, position_seconds: int, completed: bool
) -> AudioProgress:
    get_owned_artifact(db, owner_id=owner_id, artifact_id=artifact_id)
    progress = db.scalar(
        select(AudioProgress).where(
            AudioProgress.owner_id == owner_id, AudioProgress.artifact_id == artifact_id
        )
    )
    if progress is None:
        progress = AudioProgress(
            owner_id=owner_id,
            artifact_id=artifact_id,
            position_seconds=position_seconds,
            completed=completed,
        )
        db.add(progress)
    else:
        progress.position_seconds = position_seconds
        progress.completed = completed
        db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


def mark_reviewed(db: Session, *, owner_id: UUID, artifact_id: UUID) -> AudioArtifact:
    artifact = get_owned_artifact(db, owner_id=owner_id, artifact_id=artifact_id)
    record_activity(db, owner_id=owner_id, activity_type="revision", source_id=artifact.id)
    return artifact


def transcribe_audio(*, audio: bytes, content_type: str, provider=None) -> str:
    stt = provider or get_stt_provider()
    return stt.transcribe(audio=audio, content_type=content_type)
