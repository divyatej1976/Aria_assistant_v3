# ARIA frontend-v2 — the canonical learner UI

Next.js 16 + React 19. This is the **only frontend that ships**; the legacy
`frontend/` directory is frozen (see `frontend/RETIRED.md`).

## Ports (do not mix these up)

- `8000` — backend API default (`NEXT_PUBLIC_API_URL` fallback in `lib/api.ts`).
- `8010` — isolated E2E backend for Playwright **and** `npm run api:types`
  (OpenAPI generation reads `http://127.0.0.1:8010/openapi.json`).

## Develop

```bash
npm ci
npm run dev        # http://localhost:3000, talks to backend :8000
```

## Regenerate API types (required after any backend schema change)

```bash
# from the repo root:
python frontend-v2/tests/create_test_db.py e2e-smoke-v2.db
PYTHONPATH=backend python -m uvicorn app.main:app --port 8010
# then in frontend-v2:
npm run api:types
```

CI enforces freshness: the `frontend-v2-e2e` job regenerates
`lib/api-types.d.ts` against a throwaway backend on port `8011` and fails on
any drift (`git diff --exit-code`).

## Security model

- Session = HttpOnly `aria_session` cookie + readable `aria_csrf` double-submit
  token (`X-CSRF-Token` on mutations). No auth tokens in `localStorage`.
- Login/register default to `?bearer=true` for API clients; the web app passes
  `?bearer=false` (cookie-only) so no bearer copy enters browser JS memory.
- Security headers + CSP live in `next.config.ts` (`headers()`); never remove
  them without a replacement at the edge.
- Toasts render server text via `textContent`, never `innerHTML` (XSS).

## Prod deploy

Built via `Dockerfile.prod` (`NEXT_PUBLIC_API_URL` baked at build time —
changing the API origin requires `--build`). Served behind the Caddy proxy in
`docker-compose.prod.yml`; never `next start` directly in production.
