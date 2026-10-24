# ARIA backlog: from free demo to production

Prices are approximate and change often; check each provider's pricing page before committing.
"Effort" is for one developer working with Claude Code. Status: ✅ done · ⏳ waiting on you (keys,
accounts) · ⬜ to do.

What can go wrong in production, how we notice and how we fix it: [PRODUCTION-RUNBOOK.md](PRODUCTION-RUNBOOK.md).

## Where ARIA stands (24 Oct 2026)

| Area | Status | Notes |
|---|---|---|
| AI providers | ✅ code ready, ⏳ OpenAI key | OpenAI main + Gemini backup is built; today the live site still runs on Groq until the OpenAI key is added |
| Image reading | ✅ | OpenAI vision → Gemini vision → Tesseract |
| Voices / voice-to-text | ✅ code ready | OpenAI first when its key exists; device-voice fallback always works |
| Current affairs (web search) | ✅ | Automatic: time-sensitive questions search first, and the tutor itself asks for a search when unsure its knowledge is current; detailed Sources list under the answer |
| Storage | ✅ | Uploaded originals in Blob, not the database; unused vectors not stored; 300-file cap per account; old jobs cleaned |
| Feedback | ✅ | "Send feedback" (profile menu, phone menu, floating button on laptops), thumbs on answers, 1–5 star "How's ARIA?" prompt after a quiz, the 5th answer and at sign-out (once per 2 weeks) |
| Monitoring | ✅ built, ⏳ Sentry keys | Sentry (web + API), `/api/v1/health`, GitHub uptime check every 10 min |
| Mobile / navigation | ✅ installable (PWA) | Manifest + home-screen icons; bottom tab bar on every phone screen (Learn too); labeled Exit focus; native store apps are P2 |
| Hosting plans | ⏳ | Vercel Hobby + Supabase Free; upgrade before real users (P0 #6) |

---

## P0: Before inviting real users

### 1. AI keys ⏳ (code ✅)
**Decision: OpenAI is the main provider, Gemini the backup.** If an OpenAI request fails (outage,
rate limit, billing problem), ARIA retries it once on Gemini automatically, and the other way round.

| Setting (Vercel → Environment Variables) | Value |
|---|---|
| `OPENAI_API_KEY` | your OpenAI key |
| `ARIA_LLM_PROVIDER` | `openai` |
| `LLM_MODEL` | the current flagship or "mini" model name from OpenAI's models page |
| `GEMINI_API_KEY` | already set (backup + vision fallback) |
| `ARIA_OPENAI_FALLBACK_MODEL` / `ARIA_GEMINI_FALLBACK_MODEL` | optional, defaults `gpt-5-mini` / `gemini-2.5-flash` |

What uses which key once both are set:

| Feature | First | Then | Last resort |
|---|---|---|---|
| Chat, quizzes, notes, roadmaps, audio scripts | OpenAI (`LLM_MODEL`) | Gemini | built-in non-AI fallbacks |
| Image / handwriting reading | OpenAI vision | Gemini vision | Tesseract OCR |
| Audio voices | OpenAI TTS (nova / onyx) | Gemini, Groq | device voice |
| Voice-to-text (mic) | OpenAI transcription | Groq Whisper | — |

Groq can be removed once OpenAI is live (keep `GROQ_API_KEY` only if you want a third fallback).

### 2. Current affairs: web search in the tutor ✅
- Router check for questions needing fresh information (dates, "latest", "today", "news", "2026",
  prices, scores, people in the news); only those use search (slower, costs more).
- **OpenAI web search tool** when `OPENAI_API_KEY` is set, Google Search grounding via Gemini until then.
- **Automatic, no button:** obviously time-sensitive questions search first; for anything else the
  tutor answers from its own knowledge, or replies with a hidden search signal when it is unsure that
  knowledge is current, and ARIA searches and answers again.
- Under the answer: "Sources · web searched <date>", numbered like the answer's [1] [2], each with the
  exact page address (Google's redirect links are resolved) and the website; links open in a new tab.
- "Searching the web…" shows while it searches (about 8 seconds per answer).
- Prompt rule: never guess current facts; say so if search fails.
- ⬜ Next: a 20-question current-affairs test set; per-user daily search limit before launch.

### 3. Feedback ✅
- **Send feedback** from the profile menu, the phone menu (☰) or the floating button on laptops
  (text + page + browser attached).
- **"How's ARIA so far?"** 1–5 stars + comment, after a finished quiz, the 5th tutor answer and at
  sign-out; at most once every two weeks. Low ratings (1–2) alert like problem reports.
- 👍/👎 under every saved answer; 👎 asks what was wrong (wrong, too long, too short, outdated,
  ignored my file, other).
- Stored in the `feedback` table (status new → in_progress → fixed); with Sentry on, every report
  and thumbs-down raises an alert linked to the user.
- ⬜ Next: a small admin page to triage (today: Supabase table view).

### 5. Monitoring ✅ built, ⏳ keys
- ⏳ Create a free Sentry account → one project for the website, one for the API (or one for both) →
  set `NEXT_PUBLIC_SENTRY_DSN` and `ARIA_SENTRY_DSN` on Vercel, redeploy.
- ✅ `/api/v1/health` public; ✅ GitHub Action checks the site every 10 minutes and emails the repo
  owner on failure (check the Actions tab once to confirm it runs).
- ⬜ Langfuse keys for AI tracing (cost and latency per call); ⬜ Vercel log drain (Axiom / Better
  Stack) so logs are kept longer than an hour.

### 6. Hosting plans ⏳
- **Vercel Pro** ($20/month + usage): commercial use, more concurrency, longer requests.
- **Supabase Pro** ($25/month + usage): 8 GB database, daily backups, no pausing after a week idle.
- Vercel Blob on Pro: pay per GB stored / transferred (uploads and audio now live here).

---

## Storage: what changed and the limits now ✅

| Item | Before | Now |
|---|---|---|
| Uploaded PDFs / photos | Stored inside the database (6.6 MB of the 24 MB database) | Stored in Vercel Blob (`files/`); database keeps a pointer; falls back to the database only if Blob fails |
| Search vectors | 768 numbers stored twice per text chunk (~10 KB) even though unused | Not stored without a real embedding key; on Postgres only the native vector copy is kept |
| Finished jobs | Kept forever | Deleted after 7 days by the 5-minute timer |
| Upload pieces | Deleted after a day | Unchanged |
| Per account | No cap | 300 saved files (setting `ARIA_MAX_FILES_PER_USER`), clear message to delete some |
| Per file | 50 MB PDF, 25 MB image | Unchanged |
| Deleting a file / subject / account | Removed rows | Also removes the stored originals and audio |

⬜ Later: a storage meter in Account ("120 MB of 1 GB used"), per-plan quotas, moving existing
older uploads out of the database (only new uploads go to Blob).

---

## P1: Production-ready and scalable

### 7. Scale plan by user count

| Monthly active users | What changes |
|---|---|
| 100 – 1k | Paid keys + Vercel Pro + Supabase Pro. Current architecture is fine. |
| 10k | Supabase **transaction pooler** (port 6543) instead of session pooler; review indexes from slow-query logs; Redis (Upstash) for rate limits and caching; managed queue for jobs (Vercel Queues / QStash / Inngest) instead of HTTP kicks. |
| 100k | Read replica for Progress/history; cache repeated AI work; per-user AI budgets; load tests in CI. |
| 1M | Bigger Postgres compute or sharding by user; separate worker fleet; negotiated AI rate limits; on-call, SLOs (99.9%), incident runbooks. |

**The real limit at scale is AI cost and rate limits, not servers:**
`daily AI cost ≈ active users × questions per user per day × cost per answer`.

### 8. Reliability ⬜
- Load test with k6 (100 → 1,000 concurrent users on chat, uploads, quizzes).
- ✅ Reads retry after cold starts; ✅ provider backup (OpenAI ↔ Gemini); ⬜ circuit breakers.
- Database migrations in CI against a copy; tested restore from backup.
- Redis-backed rate limits per user and per IP; bot protection on sign-up.
- Feature flags to switch off expensive features (voices, Deep, search) under load.
- Staging environment that mirrors production.

### 9. Security and compliance ⬜
- Dependency and secret scanning; CSP review (Sentry now allowed).
- Privacy policy and terms (data export/delete already exist).
- Age rules if students under 13/16 use it.

---

## P2: Mobile app

| Step | Status | What |
|---|---|---|
| **PWA** (installable) | ✅ | Manifest, 192/512/maskable icons, Apple touch icon, theme colour. Android: "Install app"; iPhone: Share → Add to Home Screen. |
| **Capacitor** wrapper | ⬜ next | Same Next.js app inside a native shell → Play Store / App Store. API already accepts bearer tokens (`?bearer=true`), which native apps need. |
| Before Capacitor | ⬜ | Add `capacitor://localhost,https://localhost` to `ARIA_CORS_ORIGINS`; native mic/camera permissions; push via FCM/APNs; deep links. |
| Store accounts | ⏳ | Apple Developer ($99/year), Google Play ($25 once), store screenshots, privacy labels. |
| React Native rewrite | ⬜ only if needed | 2–3 months; only if the wrapped app feels slow. |

---

## P3: Product improvements

- Adaptive quizzes (level changes as you answer).
- Spaced-repetition calendar from "Needs work" topics.
- Meaning-based search with OpenAI embeddings (set `ARIA_EMBEDDING_API_KEY`).
- "Building your roadmap…" state on Plan right after sign-up.
- Feedback admin page; teacher/parent view; study groups.

---

## Suggested order from here

1. ⏳ Add `OPENAI_API_KEY` → switch `ARIA_LLM_PROVIDER=openai` (P0 #1)
2. ⏳ Sentry keys (P0 #5)
3. ✅ Web search for current affairs (P0 #2)
4. ⏳ Vercel Pro + Supabase Pro before real users (P0 #6)
5. ⬜ Capacitor store apps (P2)
6. ⬜ Load test → transaction pooler → Redis → managed queue (P1)
