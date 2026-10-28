"use client";

import { LogoMark } from "@/components/logo-mark";
import Link from "next/link";
import { Icon } from "@/components/icons";
import { PaletteSwitcher } from "@/components/palette-switcher";
import { RotatingCaption } from "@/components/rotating-caption";
import { LandingRedirect } from "@/components/landing-redirect";
import { ConstellationWordmark, LearningPreview } from "@/components/landing-experience";

const CAPABILITIES = [
  { icon: "book" as const, title: "Learn", text: "Personalized AI conversations that break down any concept." },
  { icon: "clipboard" as const, title: "Assess", text: "Diagnostic assessments with automatic gap analysis." },
  { icon: "calendar" as const, title: "Plan", text: "Exams, deadlines, and multi-step tasks in Notion-style trackers." },
  { icon: "headphones" as const, title: "Listen", text: "Turn notes, chats, and syllabi into audio summaries." },
  { icon: "file" as const, title: "Create", text: "Cheat sheets, notes, and question banks on demand." },
  { icon: "activity" as const, title: "Track", text: "26-week heatmap, streaks, and milestone badges." },
];

const STEPS = [
  { icon: "file" as const, title: "Add your material", text: "Upload a PDF, a photo of your notes, or just name a topic." },
  { icon: "message" as const, title: "Learn with ARIA", text: "Ask anything. Answers come from your material first, with sources." },
  { icon: "clipboard" as const, title: "Test yourself", text: "Quick practice, topic tests or a timed mock exam built from what you study." },
  { icon: "target" as const, title: "Fix the gaps", text: "Wrong answers turn into a revision lesson and your weak spots get reviewed again." },
];

const FAQ = [
  { q: "What can I upload?", a: "PDFs, text and photos of notes or slides. ARIA reads them and uses them to answer and quiz you." },
  { q: "Does ARIA only use my notes?", a: "It answers from your material first and says clearly when it adds something from beyond it. For current events it searches the web and lists its sources." },
  { q: "Will it work on my phone?", a: "Yes. ARIA runs in the browser on phones, tablets and laptops, no install needed." },
];

const CAPTIONS = [
  "Learn smarter. Learn your way.",
  "Your goals. Your pace. Your learning journey.",
  "Learn. Practice. Assess. Improve.",
  "Turn your goals into a learning path.",
  "One AI companion for your entire learning journey.",
];

export default function LandingPage() {
  return (
    <main className="relative z-10">
      <LandingRedirect />
      <div className="wrap">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, fontWeight: 800 }}>
            <LogoMark size={38} />
            <div>
              <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: "-.5px", lineHeight: 1 }}>ARIA</div>
              <div style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1.6, color: "var(--text-3)" }}>AI Learning System</div>
            </div>
          </div>
          <PaletteSwitcher />
        </div>

        <div style={{ textAlign: "center", padding: "52px 10px 34px" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              background: "var(--accent-grad-soft)",
              border: "1px solid var(--border-hi)",
              padding: "7px 16px",
              borderRadius: 99,
              fontSize: 11,
              fontWeight: 800,
              color: "var(--accent)",
              marginBottom: 30,
              letterSpacing: 0.5,
            }}
          >
            <Icon name="sparkles" size={14} /> NEXT-GEN AI COMPANION
          </div>

          <ConstellationWordmark />

          <p
            style={{
              fontSize: "clamp(15px,2.2vw,20px)",
              fontWeight: 700,
              color: "var(--text-2)",
              margin: "22px auto 8px",
              maxWidth: 560,
            }}
          >
            AI-Powered Personalized Learning System
          </p>

          <div style={{ display: "block", fontSize: "clamp(16px,2.2vw,20px)", fontWeight: 700, color: "var(--text-2)", minHeight: 30, margin: "10px auto 30px" }}>
            <RotatingCaption phrases={CAPTIONS} />
          </div>

          <div style={{ display: "flex", justifyContent: "center", gap: 14, flexWrap: "wrap" }}>
            <Link href="/signup" className="btn btn-primary btn-lg">
              <span className="shine" />
              Sign Up <Icon name="arrow" />
            </Link>
            <Link href="/signin" className="btn btn-secondary btn-lg">
              Sign In
            </Link>
          </div>
        </div>

        <LearningPreview />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 270px), 1fr))", gap: 20, marginTop: 44 }}>
          {CAPABILITIES.map((c, i) => (
            <div className="card card-pad card-hover" key={c.title} style={{ animationDelay: `${i * 60}ms` }}>
              <div
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: 15,
                  background: "var(--accent-grad-soft)",
                  border: "1px solid transparent",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--accent)",
                  marginBottom: 14,
                }}
              >
                <Icon name={c.icon} size={22} />
              </div>
              <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 6 }}>{c.title}</h3>
              <p style={{ color: "var(--text-2)", fontSize: 13 }}>{c.text}</p>
            </div>
          ))}
        </div>

        <section className="landing-section" aria-labelledby="how-title">
          <p className="eyebrow">HOW IT WORKS</p>
          <h2 id="how-title">From your notes to exam-ready, in four steps.</h2>
          <ol className="landing-steps">
            {STEPS.map((s, i) => (
              <li className="card card-pad" key={s.title}>
                <span className="landing-step-n">{i + 1}</span>
                <Icon name={s.icon} size={20} />
                <h3>{s.title}</h3>
                <p>{s.text}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="landing-section" aria-labelledby="faq-title">
          <p className="eyebrow">QUESTIONS</p>
          <h2 id="faq-title">Good to know</h2>
          <div className="landing-faq">
            {FAQ.map((f) => (
              <details className="card card-pad" key={f.q}>
                <summary>{f.q}</summary>
                <p>{f.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="landing-section landing-cta">
          <h2>Ready to study smarter?</h2>
          <p>Bring your first PDF and take a quiz on it in under a minute.</p>
          <Link href="/signup" className="btn btn-primary btn-lg"><span className="shine" />Get started <Icon name="arrow" /></Link>
        </section>
      </div>
    </main>
  );
}
