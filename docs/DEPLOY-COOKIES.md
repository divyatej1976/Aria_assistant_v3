# Production deployment: cookies, CSRF, and CORS

## The constraint

ARIA authenticates with an **HttpOnly session cookie** plus a **double-submit
CSRF token** stored in a readable (`HttpOnly=false`) cookie called `aria_csrf`.
The frontend's `lib/api.ts` reads that cookie with `document.cookie` and echoes
it back in the `X-CSRF-Token` header on every state-changing request.

`document.cookie` can only read cookies that belong to **the site serving the
JavaScript**. During development this works because both servers live on
`localhost`, and browsers scope cookies by host *ignoring the port*. In any
other topology the rule is:

> The API must be reachable on the **same registrable domain** as the frontend,
> either directly or through a reverse proxy.

## Supported topologies

### 1. Same origin (recommended)

```
https://app.example.com/         -> frontend (Next.js)
https://app.example.com/api/v1/* -> backend (reverse-proxied)
```

- The client already prefixes request paths with `/api/v1`, so
  `NEXT_PUBLIC_API_URL` must be the **origin only** — never append `/api/v1`
  (that would produce `/api/v1/api/v1/...`). Use `https://app.example.com`
  or, when the proxy serves the API at the site root, an empty string.
- Cookies are first-party; `SameSite=Strict` works; no CORS preflights.

Example nginx:

```nginx
location /api/v1/ {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
}
location / {
    proxy_pass http://frontend:3000;
}
```

Then run with:

```bash
export NEXT_PUBLIC_API_URL=https://app.example.com   # origin only, or ""
export ARIA_CORS_ORIGINS=https://app.example.com      # belt-and-braces; not needed same-origin
```

The production compose default already follows this pattern
(`NEXT_PUBLIC_API_URL` defaults to the frontend origin).

### 2. Sibling subdomains (works, needs care)

Frontend on `app.example.com`, API on `api.example.com`:

- Cookies for `example.com` are shared by subdomains — but ARIA sets its
  cookies without an explicit `Domain` attribute, which pins them to the API's
  exact host. As shipped, **split-subdomain deployments will fail the CSRF
  check**. Keep the reverse-proxy pattern above unless you also patch
  `app/security/csrf.py` to emit `Domain=example.com`.
- CORS stays enabled via `ARIA_CORS_ORIGINS` and requests use
  `credentials: "include"`, so the browser sends the session cookie.

### 3. Fully different domains (not supported)

`document.cookie` cannot read another site's cookies, so the double-submit
CSRF scheme cannot function. Do not deploy this way without reworking auth
(e.g., moving the CSRF token into a response body/header).

## Checklist

- [ ] `NEXT_PUBLIC_API_URL` points at the API **origin** the browser should
      call (no `/api/v1` suffix).
- [ ] `ARIA_CORS_ORIGINS` lists the exact frontend origin(s), when not
      same-origin — strict prod rejects `*`, `localhost`, placeholder `app.example.com`, non-https.
- [ ] `ARIA_PUBLIC_URL` is `https://<public-domain>` origin only, no path, not localhost/placeholder — used for email links.
- [ ] `ARIA_TRUSTED_HOSTS` contains `public-domain,localhost,127.0.0.1` (required superset, extras allowed) — strict rejects `*`, scheme, localhost-only.
- [ ] Frontend served over HTTPS so `Secure` cookies behave as intended.
- [ ] `ARIA_SESSION_SECRET` set to a long random value (compose prod enforces).
- [ ] Bundled PostgreSQL only: `POSTGRES_PASSWORD` is url-safe `^[A-Za-z0-9._~-]+$`, not `aria`, and `DATABASE_URL=postgresql+psycopg://aria:<same password>@db:5432/aria` contains `db:5432`. External DB not yet supported — do not advertise. Preflight verifies presence and `db:5432` target, not password equality (operator contract); URL-encode handling requires url-safe generation.
- [ ] `DATABASE_URL`, `ARIA_PUBLIC_URL`, `NEXT_PUBLIC_API_URL` all required (compose `:?`).
- [ ] VAPID keys generated (`scripts/generate_vapid.py`) only if `--push-enabled` (deferred for initial launch).
- [ ] For unrestricted prod, `SMTP_HOST`+`SMTP_FROM`+port and `GROQ_API_KEY` (`--ai-tutoring`) and embedding key (`--semantic-enabled`) required; Sentry/Langfuse warning-only.

## Preflight & health

```powershell
python scripts/check_prod_secrets.py --strict --ai-tutoring --semantic-enabled
docker compose -f docker-compose.prod.yml config --quiet  # never log output; --quiet avoids secret rendering
docker compose -f docker-compose.prod.yml up -d --build
curl http://localhost:8000/ready   # readiness DB check (bundled proxy routes /ready -> backend:8000)
curl http://localhost:8000/health  # liveness
```

Reverse proxy must route `public domain → frontend:3000`, `/api/* → backend:8000`; compose alone exposes `3000/8000`.