# ARIA backend as a free Hugging Face Docker Space (2 vCPU, 16 GB RAM).
# The website runs on Vercel and proxies /api here, so the browser sees one origin.
# Same runtime as backend/Dockerfile.prod; Spaces listen on 7860 and run as uid 1000.
FROM python:3.12-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/backend \
    # Spaces wipe the disk on restart: audio files fall back to the database, the rest is scratch.
    ARIA_AUDIO_DIR=/tmp/aria-audio \
    ARIA_BRAIN_CHECKPOINT_PATH=/tmp/aria-brain-checkpoints.db \
    HOME=/tmp

WORKDIR /app

# espeak-ng lets the local text-to-speech fallback work without a sound card.
RUN apt-get update \
    && apt-get install -y --no-install-recommends espeak-ng \
    && rm -rf /var/lib/apt/lists/* \
    && speech_lib="$(find /usr/lib -name libespeak-ng.so.1 -print -quit)" \
    && test -n "$speech_lib" \
    && ln -s libespeak-ng.so.1 "$(dirname "$speech_lib")/libespeak.so.1"

COPY pyproject.toml alembic.ini /app/
COPY backend /app/backend
COPY database /app/database
RUN pip install --no-cache-dir "." && chmod -R a+rX /app

EXPOSE 7860

# Bring the database schema up to date, then serve. Vercel forwards requests, so trust its headers.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 7860 --proxy-headers --forwarded-allow-ips '*'"]
