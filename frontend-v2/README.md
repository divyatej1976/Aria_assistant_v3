This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Backend ports (do not mix these up)

- `8000` — the shared default in `lib/api.ts` (`NEXT_PUBLIC_API_URL`); what `npm run dev` talks to.
- `8010` — the isolated E2E backend used by Playwright **and** by `npm run api:types` (OpenAPI generation reads `http://127.0.0.1:8010/openapi.json`). Regenerating types therefore requires the E2E backend running: `python frontend-v2/tests/create_test_db.py e2e-smoke-v2.db && python -m uvicorn app.main:app --port 8010` (from the repo root, `PYTHONPATH=backend`), then `npm run api:types`. CI enforces freshness: the `frontend-v2-e2e` job regenerates `lib/api-types.d.ts` against a throwaway backend on port `8011` and fails on any drift.

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
