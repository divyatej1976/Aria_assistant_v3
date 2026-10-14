"use client";

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
            <div className="logo-mark" style={{ width: 38, height: 38, borderRadius: 12, background: "var(--accent-grad)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 17 }}>
              A
            </div>
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
      </div>
    </main>
  );
}
