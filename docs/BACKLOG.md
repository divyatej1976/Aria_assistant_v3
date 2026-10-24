# ARIA backlog: from free demo to production

Prices are approximate and change often; check each provider's pricing page before committing.
"Effort" is for one developer working with Claude Code.

## Where ARIA stands today

| Area | Today | Problem at scale |
|---|---|---|
| AI answers | Groq free tier (gpt-oss-120b) | Per-minute and per-day caps; fails under real traffic |
| Current affairs | None: the model only knows its training data | Can't answer "what happened today" |
| Voices | Gemini free (~10/day for the whole site) + device-voice fallback | Not a real product voice |
| Hosting | Vercel Hobby (free) | Hobby is for non-commercial use; 5-min limit; low concurrency |
| Database | Supabase free (500 MB, pauses after 7 idle days) | Too small; connection limits; no backups SLA |
| Jobs | Postgres table queue, kicked over HTTP, timer every 5 min | Fine to ~thousands of users; needs a managed queue beyond |
| Email | Not configured | No password reset, no verification |
| Monitoring | Hooks for Sentry / Langfuse / metrics exist, all off | We learn about problems from users |
| Feedback | None | Users can't report issues |
| Mobile | Responsive website only | No installable app, no app-store presence |

---

## P0: Before inviting real users (1–2 weeks)

### 1. Paid AI keys: OpenAI as the main provider
**Decision: OpenAI replaces Groq** (newest models first; one key covers almost everything):
- Chat answers: latest GPT model for Deep/Balanced, its "mini" sibling for Quick and background work
  (pick current names from OpenAI's models page; ARIA reads them from `LLM_MODEL` settings).
- **Web search** for current affairs (OpenAI's built-in web search tool, see item 2).
- Image reading (vision), voices (TTS), voice-to-text (transcription), embeddings.

ARIA already supports OpenAI through LiteLLM (`ARIA_LLM_PROVIDER=openai`, `ARIA_LLM_API_KEY`,
`LLM_MODEL`). Today voice-to-text uses Groq Whisper and image reading/voices use Gemini; those three
need small code changes to use OpenAI too (about 1 day).

| Key | What for | Needed? | Rough cost |
|---|---|---|---|
| `OPENAI_API_KEY` (as `ARIA_LLM_API_KEY`) | Chat, web search, vision, voices, transcription, embeddings | **Yes** | Pay per token; mini models are a fraction of a cent per answer; web search billed per call |
| `GEMINI_API_KEY` | Optional backup provider | Optional | Free tier as backup |
| `RESEND_API_KEY` (or AWS SES) | Password reset, verification emails | **Yes** | Free tier ~3k emails/month, then ~$20/month |
| `SENTRY_DSN` | Error tracking (web + API) | **Yes** | Free developer tier; ~$26/month team plan |
| Langfuse keys | AI call tracing, cost per user | Recommended | Free cloud tier / self-host |
| Vercel Pro | Commercial hosting, longer functions, more concurrency | **Yes** | $20/user/month + usage |
| Supabase Pro | 8 GB DB, daily backups, no pausing | **Yes** | $25/month + usage |

Groq is dropped; its key can be removed once OpenAI handles transcription.
**Effort:** 1–2 days (keys, settings, move transcription/vision/voices to OpenAI, tests).

### 2. Current affairs: web search in the tutor
- Add a "needs fresh information" check to the router (dates, "latest", "today", "news", "2026",
  prices, scores, people in the news). Only those questions use search (it costs more and is slower).
- Use **OpenAI's web search tool**; show the sources as links under the answer
  ("From the web, 24 Oct 2026").
- Prompt rule: never guess current facts; if search fails, say so.
- **Effort:** 2–3 days. **Test:** 20 current-affairs questions with known answers.

### 3. Email that actually sends
- Resend (or Gmail SMTP for a small pilot); password reset + verification + reminders.
- **Effort:** half a day (the email code already exists; only keys and a sender domain).

### 4. Feedback system (built: report button, answer thumbs, Sentry alert per report)
- **"Send feedback" button** in the profile menu and on every error message: what happened
  (text), optional screenshot, and automatically attached page, browser, user id, last request id.
- **Thumbs up/down on every AI answer**, with an optional "what was wrong" (wrong, too long,
  didn't use my file, outdated).
- Stored in a `feedback` table; a simple **admin page** to triage (new → in progress → fixed);
  instant alert to email/Slack for new reports.
- Optional: Sentry's user-feedback widget links a report to the exact error trace.
- **Effort:** 2–3 days.

### 5. Observability and monitoring (built: Sentry wiring, `/api/v1/health`, GitHub uptime check; needs Sentry keys)
- **Errors:** turn on Sentry in the website and API (hooks exist); alerts on new errors.
- **AI tracing:** turn on Langfuse: every AI call with prompt version, latency, tokens, cost, user.
- **Logs:** Vercel log drain to Axiom or Better Stack (searchable for 30+ days instead of 1 hour).
- **Uptime:** expose `/api/v1/health` (today `/health` isn't reachable on Vercel) and add an
  uptime monitor (Better Stack / UptimeRobot) with SMS/email alerts.
- **Dashboards:** requests/min, error rate, p95 latency, AI cost per day, job queue length,
  failed jobs, sign-ups, daily active users.
- **Effort:** 2 days.

---

## P1: Production-ready and scalable (2–4 weeks)

### 6. Scale plan by user count

| Users (monthly active) | What changes |
|---|---|
| 100 – 1k | Paid keys + Vercel Pro + Supabase Pro. Current architecture is fine. |
| 10k | Database: Supabase **transaction pooler** (port 6543) instead of session pooler; indexes reviewed from slow-query logs; Redis (Upstash) for rate limits and caching; managed queue for jobs (Vercel Queues, Upstash QStash or Inngest) instead of HTTP kicks; audio files on CDN. |
| 100k | Read replica for Progress/history pages; cache repeated AI work (same file digest, same quiz material); per-user AI budgets; load tests in CI; multi-provider AI fallback (OpenAI → Gemini) for outages and rate limits. |
| 1M | Larger Postgres compute or sharding by user; separate worker fleet for jobs (Vercel Daemons / containers); enterprise AI rate limits negotiated; on-call rotation, SLOs (99.9%), incident runbooks. |

**The real limit at scale is AI cost and AI rate limits, not servers.** Rough model:
`daily AI cost ≈ active users × questions per user per day × cost per answer`.
With a Flash-class model at a fraction of a cent per answer, 100k daily users × 10 questions is
in the hundreds of dollars per day; voices and search add more. This decides pricing (free tier
limits, paid plan) more than any server choice.

### 7. Reliability ("never crashes")
- Load test with k6: 100 → 1,000 concurrent users on chat, uploads, quizzes; fix the slowest paths.
- Timeouts + retries + circuit breakers on every AI call (partly done); OpenAI → Gemini fallback; graceful messages when AI is down.
- Database migrations run in CI against a copy; daily backups + a tested restore.
- Rate limits per user and per IP backed by Redis; bot protection on sign-up (Vercel Firewall / Turnstile).
- Feature flags to switch off expensive features (voices, Deep, search) under load.
- Staging environment that mirrors production; every change goes through it.

### 8. Security and compliance
- Dependency scanning, secret scanning, Content Security Policy review.
- Privacy policy and terms; data export/delete already exist (GDPR-friendly).
- Age considerations if students under 13/16 use it.

---

## P2: Mobile app (2–6 weeks)

| Option | What it is | Effort | Verdict |
|---|---|---|---|
| **PWA** (installable website) | Add a web app manifest + icons; ARIA already has a service worker and push | 1–2 days | **Do first.** "Add to home screen" on Android and iPhone, offline shell, push notifications |
| **Capacitor** wrapper | The same Next.js app inside a native shell, published to Play Store / App Store | 1–2 weeks | **Do second.** Store presence, native mic/camera/notifications, one codebase |
| React Native / Expo rewrite | A separate native app using the same API | 2–3 months | Only if the web-based app feels too slow; the API is already ready for it |

Needs: Apple Developer ($99/year), Google Play ($25 once), app icons (the spark logo), store screenshots,
privacy labels.

---

## P3: Product improvements (ongoing)

- Adaptive quizzes: level goes up/down as you answer.
- Spaced repetition calendar driven by "Needs work" topics.
- Meaning-based search (OpenAI embeddings) once the paid key exists.
- Better voices (OpenAI TTS or ElevenLabs) with speed control and downloads.
- "Building your roadmap…" state on Plan right after sign-up.
- Teacher/parent view; shared study groups.

---

## Suggested order

1. Paid OpenAI key + Vercel Pro + Supabase Pro + email (P0 #1, #3)
2. Sentry + Langfuse + uptime + log drain (P0 #5)
3. Feedback button + answer thumbs (P0 #4)
4. Web search for current affairs (P0 #2)
5. PWA install (P2, quick win)
6. Load test → transaction pooler → Redis → managed queue (P1)
7. Capacitor store apps (P2)
