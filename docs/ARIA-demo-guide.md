# ARIA: how it works (demo guide)

Live site: https://aria-study-os.vercel.app

## 1. The one-minute pitch

ARIA is an AI study companion. You chat with a tutor about anything (or about your own files),
it turns answers into study cards, makes quizzes at three levels, turns material into audio
lessons, plans what to study, and tracks which topics you have actually mastered.

The key idea: **a topic only turns "Strong" when your quiz answers prove it, not because you
chatted about it.** Chat teaches; quizzes are the evidence; Progress shows the evidence.

---

## 2. The big picture

```
 Browser (phone / laptop)
      │  https://aria-study-os.vercel.app
      ▼
 Vercel (one free project, two "services")
   ├── /            → Website: Next.js 16 + React 19 (the screens)
   └── /api/...     → API: Python FastAPI (all logic, AI calls, files, jobs)
                         │
        ┌────────────────┼──────────────────────┬────────────────────┐
        ▼                ▼                      ▼                    ▼
  Supabase Postgres   Vercel Blob          AI providers         Supabase pg_cron
  (all data + the     (audio files)        Groq: chat, quizzes,  (a timer that pings
   job queue)                               voice-to-text         the API every 5 min)
                                            Gemini: image reading,
                                            cloud voices
```

- The website and the API live under **one address**, so cookies "just work" and there are no
  cross-site problems.
- **Every** smart thing happens in the API: the website only shows screens and calls `/api/...`.

---

## 3. Features, screen by screen

### Home
- Greeting, a quote, a "What do you want to learn today?" box that opens a chat with your question.
- Four stats: day streak, % of topics strong, chats, quizzes taken.
- "Suggested next" (e.g. start your first session, or review a weak topic).
- On phones the top bar shows **Home, Learn, Practice, More**; everything else is under More.
- A first-visit guide points out each part; tap anywhere outside it to close.

### Learn (the chat tutor)
**What you can do**
- Ask anything; the answer **streams in** word by word (first words in about 2–3 seconds).
- **Depth**: Auto, Quick (2–4 lines), Balanced (clear explanation), Deep (a full lesson).
  - Auto guesses from your message: "briefly…" → Quick; "explain in detail…" → Deep;
    "explain this image" → Balanced.
- **Deep answers become study cards**: the answer is split into sections and labelled
  Definition, Core idea, How it works, Example, Watch out, Check yourself, Summary.
  - Section tabs on top; tap a tab to jump; the tabs follow as you swipe.
  - Phone: one full-width card at a time, swipe like photos. Laptop: three compact cards side by side.
  - Tap a card to flip it and read it; "Check yourself" cards hide the answer until flipped.
  - "Full text" shows the plain answer.
- Buttons under a reply: **Deeper**, **Shorter**, **Quick check** (a mini quiz on that answer).
- **Attach files** with "+": PDFs and photos. They are read and the tutor answers from them.
  Replies say "From your material" vs "Beyond your document", so it is honest about sources.
- **Speak instead of typing**: mic button → your voice is turned into text (Groq Whisper).
- Chats are saved under Recents and named from your first question. On phones: the list button.
- Focus mode hides everything except the conversation.
- The tutor never invents your subjects or schedule; if it needs a topic, it asks.

**How it works behind the scenes**
1. Your message goes to `/api/v1/study/...`.
2. ARIA finds the most relevant pieces of your files (see "Library" below for how files are stored).
   Ranking uses **BM25 keyword scoring** (rare matching words count more), boosted for topics you
   are weak in. (Meaning-based "embeddings" search is built in but switched off on the free setup.)
3. It builds the prompt: tutor rules + your learner state (strong/weak topics) + the last
   few messages + the relevant file excerpts + the depth/tone instruction.
4. It sends that to the AI model and **streams** the answer back to the screen.
5. The turn is saved; the chat gets a title.

**Limits**
- AI model on the live site: **gpt-oss-120b on Groq** (free tier). Groq's free tier caps how much
  text per minute; ARIA retries automatically if it is briefly rate-limited.
- ARIA limits each learner to about **10 AI requests per minute** (protects the free quota).
- "Explain this whole file": up to ~12,000 characters are read directly on Groq. Longer files
  use a **condensed digest** made in the background (see Jobs).

### Library (materials)
- Upload **PDFs (up to 50 MB)**, **photos/scans (up to 25 MB)**, or paste text. Files here are
  shared with every chat in the subject; files attached inside a chat stay in that chat.
- **Generate notes**: turns a chat or material into clean study notes; download as PDF;
  notes come back for spaced revision.

**How a file is processed**
1. Big files are uploaded in **4 MB pieces** (Vercel accepts at most 4.5 MB per request), then joined.
2. Text is extracted:
   - PDFs with text → read directly (PyMuPDF).
   - Scanned PDF pages → OCR (Tesseract).
   - **Photos / handwriting → Gemini vision model**, which reads handwriting accurately
     (Tesseract stays as a backup if Gemini is unavailable).
3. The text is cut into **chunks** and stored, so the tutor can find the right part later.
4. Long files also get a **digest** (a condensed version) made by a background job.

### Audio studio
Turn a chat, a file, a note or pasted text into a spoken lesson.

**Single voice ("explainer")**: one friendly tutor explains the material: what it is and why it
matters, key ideas one by one with an example each, then a recap of the 3 main points.

**Two voices ("conversation")**: a TUTOR explains and a curious LEARNER asks the questions a
student would ask, gets confused, tries examples; it ends with the learner summarising.
Different voices for tutor and learner (cloud: Kore and Puck; device voice: two system voices).

**How an episode is made (step by step)**
1. You press Convert → the episode appears at once as "Creating…" and a **background job** starts.
2. **Writing**: the AI writes the script. Long material is split into **parts** (up to 8),
   and the card shows "Writing part 1 of 3".
3. **Recording**: the script is voiced in ~1,200-character pieces (~80 s of audio each); each
   piece is saved as soon as it is made, and the card shows "Recording 45%".
4. Pieces are joined into one file, saved to Vercel Blob, and the card shows **Ready**, with
   "Part 1 / Part 2" jump buttons for long episodes.
5. You can leave the page; it keeps going. Cancel stops it.

**Why audio used to "not complete" (and what we did)**
- Cloud voices are slow: Gemini speaks at about 1.5× real time, so a 10-minute episode needs
  ~15 minutes of recording, while one Vercel request may run only **5 minutes**.
  → The job records in pieces, saves progress, and **hands over** to a fresh request before time
    runs out; the next run skips the pieces already recorded.
- **Gemini's free voice allows only ~10 requests per day for the whole site** (not per user),
  and Groq's voice model needs terms acceptance on the account.
  → When no cloud voice is available, ARIA **still writes the full episode** and marks it
  **"Ready · device voice"**: Play reads it aloud with the phone's or laptop's built-in voice
  (free, unlimited; best in Chrome, Edge, Safari).

### Practice (quizzes)
- Create a quiz from: **your library**, **chosen chats**, **a typed topic**, or **your weak spots**.
- Formats: multiple choice, true/false, short answer, or mixed. Presets: Quick practice (5),
  Topic test (10), Mock exam (20 questions, 30 minutes).
- **Levels**:
  - Basic = recall a definition or fact.
  - Medium = explain how/why, or apply to a simple new example.
  - Advanced = multi-step problems, edge cases, comparisons, spotting mistakes; wrong options
    are common misconceptions.
- Timer: none, total, or per question. Answers revealed as you go (practice) or at the end (exam).
- Full-screen, one question at a time; results show the score, explanations, and what to review.

**How grading and mastery work**
- Multiple choice / true-false: compared with the correct option.
- Short answer: accepted when most of the important words of the expected answer are present
  (order and punctuation don't matter; "I don't know" never passes).
- Every answer is saved as **evidence** for its topic. Topic states:
  - Untested → no answers yet.
  - Developing → some correct answers.
  - **Strong (Supported) → 2 correct answers in a row.**
  - Needs review → the latest answer was wrong.
- Confidence score = 10 + 20 per correct − 30 per wrong (0–100).

### Plan
- **Roadmap**: type a goal ("crack DSA interviews") → the AI builds milestones, each with
  sub-topics you tick off. "Refine" rebuilds it with your request ("less theory, more practice").
  Ticks also update from your quiz results.
- **Exams & deadlines**: add an exam date and topics; "What should I do today?" shows missed
  work, today's tasks and readiness; reminders arrive as notifications.

### Progress
- Overview: topics strong, this week's study days, streak, a calendar heatmap, badges.
- **Topic map**: your concepts as a constellation, showing which are strong, developing or need review.

### Account
- Change password (rules: 8+ characters, a letter, a number and a symbol), name and email.
- **Bring your own Groq key** (stored encrypted) if you want your own AI quota.
- Export all your data, delete a subject or everything, see and sign out other devices.

---

## 4. The backend in more detail

### Tech stack and why

| Part | What | Why we chose it |
|---|---|---|
| Website | **Next.js 16, React 19, TypeScript** | Most widely used React framework, first-class on Vercel, fast pages, type safety. Markdown + math (KaTeX) for answers, Motion for animations. |
| API | **Python + FastAPI** | AI, PDF and OCR libraries are best in Python. FastAPI is fast, async (good for streaming AI answers) and validates every request with Pydantic. |
| Database | **PostgreSQL on Supabase** (free) | Relational data (users, chats, quizzes, evidence) fits SQL; Postgres also powers the job queue (`SKIP LOCKED`), has pgvector for future semantic search, and Supabase adds a free timer (pg_cron). |
| DB access | SQLAlchemy 2 + Alembic | Typed models and versioned migrations (35 so far), so the schema changes safely. |
| AI | **Groq** (gpt-oss-120b, Whisper) via **LiteLLM** | Groq is free and very fast. LiteLLM lets us switch to Gemini or OpenAI with a setting, no code change. |
| Vision & voice | **Gemini** (2.5 Flash for images, Flash TTS for voices) | Reads handwriting well; free tier. |
| Files | **Vercel Blob** | Audio files can't live on a serverless machine's disk; Blob is free object storage. |
| Hosting | **Vercel** (free Hobby) | One project hosts both website and API, HTTPS and deploys included. |
| Tests | ~640 Python tests (pytest), Playwright browser tests | Each feature and every bug fix has a test. |

### Security basics
- Sign-in uses an **HttpOnly session cookie** (JavaScript can't read it) plus a CSRF check on changes.
- Passwords are hashed; every data query is scoped to the signed-in owner.
- Personal API keys are encrypted (Fernet) with a separate key.
- Rate limits on AI and sign-in routes; idempotency keys stop double submissions.

### Background jobs (why and how)
Some work takes longer than a web request should: writing and voicing audio, condensing long files.

- **Queue**: a `jobs` table in Postgres. A job has a kind (audio, digest), status
  (queued → running → done/failed), attempts, a lease, and saved progress.
- **Workers claim jobs safely**: `SELECT … FOR UPDATE SKIP LOCKED`, so several workers can run
  **in parallel** and never take the same job.
- **Starting a worker**: on Vercel a background thread would be killed when the request ends, so
  ARIA starts each worker as **its own request** to `/api/v1/internal/work` (protected by a secret).
- **Time budget + hand-over**: each run works up to ~4 minutes, saves progress (e.g. which audio
  pieces are done), and puts the job back in the queue; the next run continues from there.
- **Crash safety**: a lease (6 min) marks a job as taken; if a worker dies, the lease expires and
  another worker picks it up. Up to 4 crash retries, then the job is marked failed.
- **Timer**: Supabase **pg_cron** calls `/api/v1/internal/tick` every 5 minutes: it restarts
  stalled jobs, sends reminders, and cleans up leftover upload pieces.

### Free-tier limits (good to know before a demo)

| Limit | Value | Effect / what ARIA does |
|---|---|---|
| Vercel request time | 5 min | Jobs hand over before the limit. |
| Vercel request size | 4.5 MB | Uploads go in 4 MB pieces (files up to 50 MB). |
| Vercel idle sleep | first request after idle is slower | Page loads retry automatically. |
| Groq free tier | limited text per minute | Retries; whole-file reading capped at ~12k characters. |
| Gemini voices | ~10 per day for the whole site | Falls back to the device voice. |
| ARIA rate limit | ~10 AI requests/min per learner | Protects the shared free quota. |
| Supabase free | 500 MB database; **pauses after ~7 days with no activity** | Open the site within the week before a demo. |
| Email | not configured | Forgot-password / verify emails don't send yet; the app hides the verify prompt. |

---

## 5. Demo tips

1. **Warm it up**: open the site and sign in 5 minutes before (wakes the server and database).
2. **Learn**: ask "Explain binary search" with **Deep** → show the study cards, tabs and flipping.
3. **Image**: attach a clear photo of notes and ask "Explain this image" → it reads handwriting.
4. **Practice**: create an **Advanced** quiz from the chat → answer → show Progress topics updating.
5. **Audio**: convert a short text with **two voices** → show the steps ("Writing…", "Recording…")
   and Ready. If it says "device voice", explain the free daily voice limit and the fallback.
6. **Phone**: show the same account on a phone: four tabs, swipeable cards.

## 6. Questions you may get

- **"Is it just ChatGPT?"** No: it grounds answers in your files (with honest "from your document"
  labels), tracks mastery from quiz evidence, and plans/quizzes/audio all feed the same learner model.
- **"How do you know a topic is mastered?"** Two correct answers in a row on that topic; a wrong
  answer sends it back to review.
- **"Why not one big server?"** Serverless is free and scales to zero; long work is split into
  resumable jobs so the 5-minute limit doesn't matter.
- **"Can it switch AI providers?"** Yes, by a setting (Groq, Gemini or OpenAI) thanks to LiteLLM.
- **"What would you improve?"** Meaning-based search (embeddings), a paid voice for unlimited
  audio, email sending, and adaptive quizzes that change level as you answer.
