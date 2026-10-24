# ARIA production runbook: what can go wrong, how we notice, how we fix it

For each likely problem: the **symptom** users see, **how we notice** (often before users tell us),
the **immediate fix** (minutes) and the **permanent fix** (the backlog item that stops it recurring).
Keep this next to [BACKLOG.md](BACKLOG.md).

## How we notice problems

| Signal | Where | What it catches |
|---|---|---|
| Uptime check | GitHub → Actions → "Uptime" (every 10 min, emails on failure) | Site or API down |
| Error tracking | Sentry (once `ARIA_SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` are set) | Crashes in the website and API, with the user and page |
| User reports | `feedback` table (Supabase → Table editor), Sentry alert per report | Anything users hit, in their words |
| Answer ratings | `feedback` rows with `kind = answer`, `rating = down` | Wrong, outdated or too-long AI answers |
| Server logs | Vercel → Logs (1 hour on Hobby; add a log drain for longer) | Slow requests, provider errors, job failures |
| Database | Supabase → Reports (size, connections, slow queries) | Full disk, connection limits, slow pages |
| AI spend | OpenAI / Gemini usage dashboards; Langfuse once set up | Cost spikes, rate limits |

**Triage rule:** many users affected → fix now (rollback first if a deploy caused it);
one user → reply, reproduce, fix in the next release.

**Fastest fix for a bad deploy:** Vercel → Deployments → previous good deployment → "Promote to
Production" (instant rollback). Then fix calmly.

---

## 1. Availability and speed

| Problem | Symptom | How we notice | Immediate fix | Permanent fix |
|---|---|---|---|---|
| Site or API down | Page won't load; "Couldn't reach ARIA's server" | Uptime email; Vercel status page | Roll back the last deploy; check Vercel status | Staging environment; health checks in CI |
| Slow first request after idle (cold start) | First page load takes several seconds | Vercel logs show long first request | Already retried automatically for page loads | Vercel Pro (warmer instances); keep-warm ping |
| Database connections exhausted | Random "request failed" errors under load | Sentry `OperationalError`; Supabase connection graph at max | Restart traffic spike source; temporarily lower worker count | Supabase transaction pooler (port 6543); Pro plan; fewer long transactions |
| Database paused (free plan, 7 idle days) | Everything fails after a quiet week | Uptime email; Supabase shows "Paused" | Supabase → Restore project | Supabase Pro (never pauses) |
| Slow pages as data grows | Progress, Library or chat list slow | Supabase slow-query report; p95 latency | Add the missing index | Index review per release; read replica at 100k users |
| Request too large | Upload of a huge file fails | Error toast; 413 in logs | Ask user to split the file | Already uploads in 4 MB pieces up to 50 MB; raise per plan |

## 2. AI provider problems

| Problem | Symptom | How we notice | Immediate fix | Permanent fix |
|---|---|---|---|---|
| OpenAI outage or slowdown | Answers slow or "AI provider unavailable" | Logs: `llm provider failed, using backup`; status.openai.com | Nothing: requests retry on Gemini automatically | Keep both keys funded; add a third provider if needed |
| Rate limits (too many requests) | Slow answers, occasional failures at peak | Logs: `rate limited`; provider dashboard | Raise the provider's usage tier | Per-user limits; queue heavy work; negotiated limits |
| Bill / credits run out | All AI fails at once | Provider email; every request falls back | Top up; the backup provider carries traffic meanwhile | Billing alerts at 50/80/100% of budget; auto-recharge |
| Cost spike (abuse or a loop) | Unexpected invoice | Langfuse / provider usage graph | Disable the offending feature flag or account | Per-user daily budgets (`ARIA_LLM_PER_USER_BUDGET_USD`); bot protection on sign-up |
| Wrong or invented answers | Thumbs-down "wrong" | `feedback` ratings; user reports | Improve the prompt; add a test question | Answer-quality test set run before each release |
| Outdated current-affairs answers | Thumbs-down "outdated" | Ratings with reason `outdated` | Check the Sources list is present (search ran) | Tune the time-word detector and the tutor's search rule; 20-question current-affairs test set |
| Search not triggered when needed | Confident but stale answer, no Sources | Thumbs-down "outdated"; spot checks | Add the missing cue to the detector | Weekly review of answers without sources on news-like questions |
| Searching too often | Slow answers (~8 s) on ordinary questions; higher search bill | Logs count "Searching the web" per answer; provider usage | Narrow the detector words | Per-user daily search limit; cache popular searches for a few minutes |
| Search provider down or quota hit | Answer says it could not verify the latest information | Logs: `web search failed` | Switch provider (OpenAI ↔ Gemini) by key | Keep both providers funded; alert on failure rate |
| Unreliable or biased sources | Users question a source | Feedback reports | Remove/deny a domain | Domain allow/deny list; prefer official and major news sites |
| Model retired by the provider | Errors after a provider announcement | Sentry spike; provider deprecation email | Set `LLM_MODEL` to the replacement (no code change) | Track deprecation notices; pin models in settings |

## 3. Background jobs (audio, long-file digests)

| Problem | Symptom | How we notice | Immediate fix | Permanent fix |
|---|---|---|---|---|
| Episode stuck on "Creating…" | Never finishes | `jobs` table: `running` with an old `lease_until` | The 5-minute timer restarts it; or set the job to `queued` | Managed queue (Vercel Queues / QStash) at 10k users |
| Timer not firing | Stuck jobs pile up, reminders missing | Supabase → Cron → `aria-tick` history | Re-enable the cron job; check `ARIA_CRON_SECRET` matches | Alert when no tick in 15 minutes |
| Voice quota used up | "Ready · device voice" instead of a recording | Logs: `cloud voices unavailable` | Expected fallback; raise the paid voice quota | Paid OpenAI TTS; per-user audio limits |
| Job fails repeatedly | Episode "Failed" with a reason | `jobs.status = failed`, `error` column | Fix the cause, then Retry from the card | Error alerts per job kind |

## 4. Storage

| Problem | Symptom | How we notice | Immediate fix | Permanent fix |
|---|---|---|---|---|
| Database near its size limit | Writes start failing | Supabase usage report | Delete old test accounts; vacuum | Pro plan; files already in Blob, not the database |
| Blob storage cost growing | Bill increases | Vercel usage | Delete orphaned files (the sweep runs automatically) | Per-plan storage quotas and a storage meter in Account |
| One account uploads too much | Their uploads stop | "You have 300 saved files" message | Raise `ARIA_MAX_FILES_PER_USER` for them or delete files | Storage quotas by plan |
| Upload fails to read | "Could not read this file" | Feedback; `resources.processing_status = FAILED` | Ask for a clearer scan / PDF with text | Better OCR; show the reason on the card |

## 5. Accounts and security

| Problem | Symptom | How we notice | Immediate fix | Permanent fix |
|---|---|---|---|---|
| Can't reset password | No email arrives | Feedback; logs show email not sent | Set SMTP / Resend keys | Email provider with delivery monitoring |
| Bot sign-ups / abuse | Many fake accounts, cost spike | Sign-up graph; AI cost spike | Block the IPs; lower rate limits | CAPTCHA (Turnstile) on sign-up; Vercel Firewall rules |
| Leaked key | Unexpected usage on a provider | Provider alert; secret scanner | **Rotate the key** at the provider, update Vercel env, redeploy | Secret scanning in CI; never paste keys in chat |
| Data deletion request | User asks to delete everything | Feedback / email | Account → Delete all my data (removes rows, files, audio) | Documented privacy process |
| Someone sees another user's data | Privacy incident | User report; Sentry | Take the feature offline, investigate immediately | Every query is owner-scoped; keep cross-owner tests passing |

## 6. Website and mobile

| Problem | Symptom | How we notice | Immediate fix | Permanent fix |
|---|---|---|---|---|
| Layout broken on a phone size | Overlapping or cut-off screens | Feedback with page + browser | Fix the CSS, deploy | Phone screenshots in the release checklist |
| Old app version cached | User sees an old screen after a deploy | Feedback mentions missing features | Ask user to refresh / reinstall the home-screen app | Version check that prompts "New version, reload" |
| Can't find a page | "How do I get back?" | Feedback | Bottom tab bar on every phone screen and labeled Exit focus (done); back buttons on detail views | Usability test with 5 new users per release |
| Feedback prompt annoys users | Low ratings mentioning popups | Ratings comments | Lengthen the interval (2 weeks today) | Ask only after positive moments; A/B the timing |
| Device voice silent | Play does nothing on some phones | Feedback with the browser name | Suggest Chrome / Safari | Paid cloud voices so device voice is rarely needed |

---

## Release checklist (prevents most of the above)

1. All tests pass (`python -m pytest tests`) and the website type-checks (`npx tsc --noEmit`).
2. Deploy to a **preview**, click through Home, Learn (Quick + Deep + web search), Practice, Audio,
   Library, Progress on a phone and a laptop.
3. Database migration applied to production **before** the deploy that needs it.
4. Promote to production; watch Sentry and the uptime check for 30 minutes.
5. If anything breaks: **roll back first**, investigate second.

## When a user reports a problem

1. Find their report in the `feedback` table (page, browser, time).
2. Find the matching error in Sentry (same user id and time) or Vercel logs.
3. Reproduce it on the same page and screen size.
4. Fix, add a test that would have caught it, deploy.
5. Set the report's `status` to `fixed`; reply to the user if they left contact details.
