# Portable learner export, schema version 2

Download `GET /api/v1/account/export` while signed in. The response is a JSON
attachment named `aria-data-export.json`. It exports the signed-in learner only.

`metadata.schema_version` is `2`. Collections contain original row IDs, owner
IDs, foreign IDs, timestamps and source fields. Related records are separate
collections: for example, `conversation_messages.study_session_id` points to
`study_sessions.id`, and `resource_chunks.resource_id` points to `resources.id`.
Assessment questions, attempts, answers and evaluations are included separately.
Do not identify records by title or by their order in the file.

`resources.raw_bytes` holds the original uploaded bytes as base64 when retained
by the app. Decode it to recover the original document or image.
`original_bytes_status` is `included`, `not_applicable` for a text resource, or
`unavailable` when an original binary is absent. `source_text` remains separate.

`audio_artifacts.audio_bytes` holds base64 audio loaded from file storage or
legacy database bytes. `audio_bytes_status` is `included`, `unavailable` for a
ready artifact whose bytes cannot be read, or `not_generated`. File storage is
read during export; files deleted concurrently may be reported unavailable even
though their database metadata is in the snapshot. Storage keys describe the
source installation and are not portable destinations for an importer.

All collections are uncapped. `record_counts` contains the exact number emitted
in each collection; `metadata.truncated` is false. HTTP serialization reads
bounded batches rather than building the account in memory. Binary records are
read one at a time. Closing the download releases the export's database session.
The database records use a consistent read snapshot (PostgreSQL repeatable read
or an explicit SQLite transaction).

Authentication secrets, active sessions, idempotency reservations, LLM key
plaintext/ciphertext and push authentication keys are excluded. The `llm_key`
collection contains identity and provider/model/hint metadata only. Derived
embedding vectors and transient audio claims are also excluded; regenerate
embeddings from the exported chunks. These exclusions are listed in
`metadata.omissions`. Global deployment configuration and aggregate operational
tables are outside a learner export.

This format supports reconstruction using original IDs and decoded binaries.
ARIA does not currently expose an import endpoint. It is also distinct from an
operational database backup, which must preserve deployment secrets and external
storage through the production recovery procedure.
