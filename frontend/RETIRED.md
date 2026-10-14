# RETIRED — do not use

The legacy `frontend/` app is **frozen and no longer deployed**.

- Canonical app: `frontend-v2/` (see `frontend-v2/BUILD_PLAN.md` and its deploy
  section; prod builds `frontend-v2/Dockerfile.prod`).
- `Dockerfile.prod` was renamed to `Dockerfile.prod.RETIRED` so stale build
  commands fail loudly instead of shipping the wrong app.
- This directory is kept for reference only. Do not modify it.
