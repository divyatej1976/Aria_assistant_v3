"""What each background job kind does. Imported by workers before they run jobs."""

from app.db.models import AudioArtifact
from app.services.digest import build_digest
from app.services.jobs import handler

handler("digest")(build_digest)


@handler("audio")
def run_audio(db, job, progress) -> None:
    """Write and voice one episode; long ones save each part and resume."""
    from app.services.audio import generate_audio

    artifact = db.get(AudioArtifact, job.target_id)
    if artifact is None or artifact.status == "READY":
        return  # cancelled (deleted) or already made
    generate_audio(db, owner_id=artifact.owner_id, source_type=artifact.source_type,
                   source_id=artifact.source_id, style=artifact.style, progress=progress, job_id=job.id)
