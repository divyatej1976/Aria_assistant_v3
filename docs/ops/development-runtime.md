# Local ARIA runtime

The development Compose stack serves the UI at http://localhost:3000 and the API at http://localhost:8000. From the repository root:

```powershell
docker compose config --quiet
docker compose up -d --build
Invoke-RestMethod http://localhost:8000/ready
# Keep this command running while editing frontend source:
docker compose watch --no-up frontend
```

The migration service waits for PostgreSQL health and must finish before the API starts. A failed migration prevents API startup. `/ready` checks database and required schema; provider configuration is not proof of successful cloud calls. Authenticated `/api/v1/settings/capabilities` reports the active learner credential source, permitted models and deployment-only speech configuration.

Compose explicitly forwards the optional settings from the repository `.env`: Groq, personal-key encryption, speech, embeddings, SMTP, push and observability. Personal keys need a valid dedicated encryption key. A learner tutor key does not configure speech providers. Frontend push additionally uses NEXT_PUBLIC_VAPID_PUBLIC_KEY. No secrets should be printed with a plain `docker compose config`; use `--quiet`.

Audio uses the audio-data named volume. Optional development backups use backup-data and default to disabled. Do not remove named volumes when preserving local data. The development image has been built and checked in a disposable container without network access: local speech generated valid WAV audio, PostgreSQL dump/restore tools reported version 16, and application imports/migration files passed. Isolated Compose startup, migration through 0025, real PostgreSQL API checks, encrypted backup/restore, and production-image readiness/speech have been verified; current browser batch results are in the review fix report.

The existing native preview on port 3101 is a separate mode. Its backend must allow that origin and its UI API URL must point to localhost:8000. Default development Compose CORS includes ports 3000, 3100 and 3101; ARIA_PUBLIC_URL should match the UI origin actually being used.

Frontend development uses native Compose source synchronization rather than a Windows bind mount. This avoids missed container file notifications and stale compiled forms. Run `docker compose watch --no-up frontend` after building/starting, or use `docker compose up --build --watch`. Dependencies and environment files are excluded from synchronization; package manifest changes rebuild the frontend image. Compose keeps its Next artifacts in a dedicated `.next-compose` volume. Source creation and edits were verified to render without a container restart. [Compose Watch reference](https://docs.docker.com/compose/how-tos/file-watch/).

The monthly budget settings track estimated text/structured LLM use. Admission reserves estimated cost and restricts completion length; returned usage settles against the original UTC month. Unknown transport billing retains the reservation. These are spending safeguards, not invoice guarantees; speech and embedding costs are outside this ledger. Production persistent-accounting failure blocks generation.
