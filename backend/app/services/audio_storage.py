"""Audio byte storage behind an interface.

Local directory today; an S3-compatible backend can implement the same
`AudioStorage` protocol later without touching callers (architecture rule:
provider SDKs stay behind interfaces). Keys are derived from UUIDs only —
never from user input — so path traversal is impossible by construction.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID

logger = logging.getLogger(__name__)

_CONTENT_TYPE_EXTENSIONS = {
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/webm": "webm",
    "audio/mp4": "m4a",
    "audio/ogg": "ogg",
}


class AudioStorage(Protocol):
    def save(
        self,
        *,
        owner_id: UUID,
        artifact_id: UUID,
        content_type: str | None,
        data: bytes,
    ) -> str:
        """Persist bytes; return the opaque storage key."""
        ...

    def load(self, key: str) -> bytes | None:
        """Return bytes, or None when the key is missing/invalid."""
        ...

    def delete(self, key: str) -> None:
        """Remove bytes; missing keys are a no-op."""
        ...


def _extension(content_type: str | None) -> str:
    return _CONTENT_TYPE_EXTENSIONS.get((content_type or "").lower(), "bin")


class LocalAudioStorage:
    """Filesystem backend rooted at `aria_audio_dir` (volume in prod)."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()

    def _path(self, key: str) -> Path | None:
        try:
            owner_part, file_part = key.split("/")
            stem, ext = file_part.rsplit(".", 1)
            UUID(owner_part)
            UUID(stem)
        except (ValueError, AttributeError):
            logger.warning("rejected malformed audio storage key")
            return None
        if not ext.isalnum():
            return None
        candidate = self._root / owner_part / f"{stem}.{ext}"
        if candidate.is_symlink() or candidate.parent.is_symlink():
            return None
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self._root) or resolved.parent != candidate.parent:
            return None
        return candidate

    def save(
        self,
        *,
        owner_id: UUID,
        artifact_id: UUID,
        content_type: str | None,
        data: bytes,
    ) -> str:
        key = f"{owner_id}/{artifact_id}.{_extension(content_type)}"
        path = self._path(key)
        assert path is not None  # built from UUIDs above; always valid
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def load(self, key: str) -> bytes | None:
        path = self._path(key)
        if path is None or not path.is_file():
            return None
        try:
            return path.read_bytes()
        except OSError:
            logger.exception("audio storage read failed")
            return None

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path is None:
            return
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.exception("audio storage delete failed")
            raise

    def cleanup_candidates(self, *, before: datetime):
        """Only old, regular UUID files within this configured storage root."""
        if not self._root.is_dir():
            return
        for directory in self._root.iterdir():
            if directory.is_symlink() or not directory.is_dir():
                continue
            try:
                UUID(directory.name)
            except ValueError:
                continue
            for path in directory.iterdir():
                key = f"{directory.name}/{path.name}"
                valid = self._path(key)
                if valid is None or not valid.is_file():
                    continue
                try:
                    if datetime.fromtimestamp(valid.stat().st_mtime, UTC) < before:
                        yield key
                except OSError:
                    logger.exception("audio cleanup file inspection failed")


class BlobAudioStorage:
    """Vercel Blob: files survive serverless restarts and stay out of the database.

    The key is the blob's URL. Paths are UUIDs (unguessable), and playback still goes through
    ARIA's own signed-in audio endpoint, which reads the bytes here.
    """

    API = "https://blob.vercel-storage.com"

    def __init__(self, token: str) -> None:
        self._headers = {"authorization": f"Bearer {token}", "x-api-version": "7"}

    def save(self, *, owner_id: UUID, artifact_id: UUID, content_type: str | None, data: bytes) -> str:
        import httpx

        path = f"audio/{owner_id}/{artifact_id}.{_extension(content_type)}"
        response = httpx.put(f"{self.API}/{path}", content=data, timeout=120, headers={
            **self._headers, "x-content-type": content_type or "application/octet-stream",
            "x-add-random-suffix": "0", "x-allow-overwrite": "1"})
        response.raise_for_status()
        return response.json()["url"]

    @staticmethod
    def _ours(key: str) -> bool:
        return key.startswith("https://") and ".public.blob.vercel-storage.com/audio/" in key

    def load(self, key: str) -> bytes | None:
        import httpx

        if not self._ours(key):
            return None
        try:
            response = httpx.get(key, timeout=120)
        except httpx.HTTPError:
            logger.exception("blob audio read failed")
            return None
        return response.content if response.status_code == 200 else None

    def delete(self, key: str) -> None:
        import httpx

        if self._ours(key):
            httpx.post(f"{self.API}/delete", json={"urls": [key]}, headers=self._headers, timeout=60).raise_for_status()


def get_audio_storage() -> AudioStorage:
    from app.core.config import get_settings

    settings = get_settings()
    if settings.blob_read_write_token:
        return BlobAudioStorage(settings.blob_read_write_token)
    return LocalAudioStorage(settings.aria_audio_dir)
