"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { RotatingCaption } from "@/components/rotating-caption";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/lib/toast";
import { useActiveContext } from "@/components/use-active-context";
import { pickNextAction } from "@/lib/next-action";

const AGENTS = [
  { title: "LEARN", icon: "message" as const, desc: "Ask questions, understand concepts, and learn through personalized conversations.", href: "/app/learn", cta: "Learn" },
  { title: "ASSESS", icon: "clipboard" as const, desc: "Personalized assessments with instant gap analysis and adaptive difficulty.", href: "/app/assess", cta: "Assess" },
  { title: "AUDIO", icon: "headphones" as const, desc: "Turn learning content into beautiful audio summaries for revision anywhere.", href: "/app/audio", cta: "Listen" },
  { title: "ROADMAP", icon: "route" as const, desc: "Your path to mastery — step-by-step roadmaps from beginner to advanced.", href: "/app/roadmaps", cta: "Open" },
];

const CAPTIONS = [
  "Ready to make some progress?",
  "One step today is one step closer.",
  "Let's keep the streak alive.",
  "What will you learn today?",
];

type Upcoming = { id: string; title: string; due_at: string };

function dayLabel(dueAt: string): string {
  const due = new Date(dueAt);
  const now = new Date();
  const days = Math.round((due.getTime() - now.getTime()) / 86_400_000);
  if (days < 0) return "Overdue";
  if (days === 0) return "Today";
  if (days === 1) return "Tomorrow";
  return due.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function HomePage() {
  const { context } = useActiveContext();
  const [flipped, setFlipped] = useState<Record<number, boolean>>({});
  const [streak, setStreak] = useState<{ current_streak: number; today_active: boolean } | null>(null);
  const [overdue, setOverdue] = useState<{ id: string; title: string } | null>(null);
  const [dueNotes, setDueNotes] = useState<{ id: string; title: string }[]>([]);
  const [focusDecision, setFocusDecision] = useState<{ reason: string; concept?: string } | null>(null);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [upcoming, setUpcoming] = useState<Upcoming[]>([]);
  const [insight, setInsight] = useState<string>("");
  const [pct, setPct] = useState(0);

  useEffect(() => {
    if (!context) return;
    let cancelled = false;
    api<{ current_streak: number; today_active: boolean }>("/api/v1/progress/consistency")
      .then((c) => {
        if (!cancelled) {
          setStreak(c);
          setNowMs(Date.now());
        }
      })
      .catch(() => {});
    api<Upcoming[]>(`/api/v1/planner/upcoming?days=30&context_id=${context.id}`)
      .then((u) => !cancelled && setUpcoming(u.slice(0, 3)))
      .catch(() => {});
    api<{ states: { concept_name?: string; state: string }[]; decisions: { decision_type: string; reason: string; concept_id?: string | null }[] }>(
      `/api/v1/contexts/${context.id}/adaptation`,
    )
      .then((s) => {
        if (cancelled) return;
        const focus = s.decisions.filter((d) => d.decision_type === "FOCUS_STUDY")[0];
        setInsight(focus?.reason ?? "");
        setPct(
          s.states.length
            ? Math.round((s.states.filter((x) => x.state === "SUPPORTED").length / s.states.length) * 100)
            : 0,
        );
        const focusState =
          focus?.concept_id != null
            ? s.states.find((st) => (st as { concept_id?: string }).concept_id === focus.concept_id)
            : undefined;
        setFocusDecision(
          focus
            ? {
                reason: focus.reason,
                concept:
                  focusState?.concept_name ??
                  (focusState as { concept_name?: string } | undefined)?.concept_name ??
                  undefined,
              }
            : null,
        );
      })
      .catch(() => {});
    // inputs for the Next-Best-Action card
    api<{ id: string; title: string }[]>("/api/v1/planner/missed")
      .then((m) => !cancelled && setOverdue(m[0] ?? null))
      .catch(() => {});
    api<{ id: string; title: string }[]>(`/api/v1/notes/due?context_id=${context.id}`)
      .then((n) => !cancelled && setDueNotes(n.map((x) => ({ id: x.id, title: x.title }))))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [context]);

  const toggle = (i: number) => setFlipped((f) => ({ ...f, [i]: !f[i] }));

  const examDays =
    upcoming.length > 0
      ? Math.round((new Date(upcoming[0].due_at).getTime() - nowMs) / 86_400_000)
      : null;
  const nextAction = pickNextAction({
    overdueTask: overdue,
    dueNotesCount: dueNotes.length,
    focusDecision,
    nearestExamDaysLeft: examDays,
    nearestExamTitle: upcoming[0]?.title ?? null,
    hasLastSession: Boolean(context),
  });

  return (
    <div>
      <div style={{ textAlign: "center", padding: "22px 0 8px" }}>
        <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-2)", textTransform: "uppercase", letterSpacing: 2 }}>
          {(() => {
            const h = new Date().getHours();
            return `Good ${h < 12 ? "morning" : h < 18 ? "afternoon" : "evening"}${context ? " · " + context.title : ""}`;
          })()}
        </div>
        <div style={{ display: "block", fontSize: "clamp(22px,3.4vw,34px)", fontWeight: 800, letterSpacing: "-1px", color: "var(--text-1)", minHeight: 44, margin: "10px auto 8px" }}>
          <RotatingCaption phrases={CAPTIONS} interval={3600} />
        </div>
      </div>

      <div
        className="card card-pad"
        style={{ maxWidth: 760, margin: "0 auto 26px", display: "flex", gap: 14, alignItems: "flex-start", borderLeft: "4px solid var(--accent)" }}
      >
        <div className="fsq-ic">
          <Icon name={nextAction.icon} size={24} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: 1.4, color: "var(--accent-strong)", textTransform: "uppercase" }}>
            Next best action
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 800, margin: "2px 0 4px" }}>{nextAction.title}</h3>
          <p style={{ fontSize: 13, color: "var(--text-2)", margin: 0 }}>{nextAction.why}</p>
          <Link href={nextAction.href} className="btn btn-primary" style={{ marginTop: 10 }}>
            {nextAction.cta} <Icon name="arrow" />
          </Link>
        </div>
      </div>


      {dueNotes.length > 0 && (
        <div className="card card-pad" style={{ maxWidth: 760, margin: "0 auto 26px" }}>
          <div className="section-head" style={{ marginBottom: 10 }}>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: 0 }}>Due for review ({dueNotes.length})</h3>
            <Link href="/app/materials" style={{ fontSize: 12, fontWeight: 700, color: "var(--accent-strong)" }}>
              Open materials
            </Link>
          </div>
          {dueNotes.map((n) => (
            <div className="kv" key={n.id}>
              <span className="k"><Icon name="file" size={15} /> {n.title}</span>
              <span className="v" style={{ display: "flex", gap: 8 }}>
                <button
                  className="btn btn-ghost"
                  style={{ padding: "3px 8px", fontSize: 11 }}
                  aria-label={`Review again ${n.title}`}
                  onClick={async () => {
                    try {
                      await api(`/api/v1/notes/${n.id}/review`, { method: "POST", body: JSON.stringify({ outcome: "again" }) });
                      setDueNotes((prev) => prev.filter((x) => x.id !== n.id));
                    } catch (e) {
                      toast(e instanceof ApiError ? e.message : "Could not record the review.");
                    }
                  }}
                >
                  Again
                </button>
                <button
                  className="btn btn-primary"
                  style={{ padding: "3px 8px", fontSize: 11 }}
                  aria-label={`Review good ${n.title}`}
                  onClick={async () => {
                    try {
                      await api(`/api/v1/notes/${n.id}/review`, { method: "POST", body: JSON.stringify({ outcome: "good" }) });
                      setDueNotes((prev) => prev.filter((x) => x.id !== n.id));
                    } catch (e) {
                      toast(e instanceof ApiError ? e.message : "Could not record the review.");
                    }
                  }}
                >
                  Good
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
      <div style={{ display: "flex", justifyContent: "center", flexWrap: "wrap", gap: 30, margin: "20px 0 40px" }}>
        {AGENTS.map((a, i) => (
          <div key={a.title} className={`flip-square${flipped[i] ? " open" : ""}`} style={{ width: 200, height: 260 }}>
            <div className="flip-square-inner">
              <div className="fsq-face fsq-front">
                <div className="fsq-ic"><Icon name={a.icon} size={27} /></div>
                <div className="fsq-name">{a.title}</div>
                <button
                  type="button"
                  aria-expanded={!!flipped[i]}
                  aria-controls={`flip-desc-${i}`}
                  aria-label={`Show details for ${a.title}`}
                  onClick={() => toggle(i)}
                  className="btn btn-ghost"
                  style={{ marginTop: 8, padding: "4px 10px", fontSize: 11 }}
                >
                  Details
                </button>
              </div>
              <div className="fsq-face fsq-back" id={`flip-desc-${i}`}>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 800, display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ color: "var(--accent)", display: "inline-flex" }}><Icon name={a.icon} size={18} /></span> {a.title}
                  </div>
                  <div className="fsq-desc">{a.desc}</div>
                </div>
                <Link href={a.href} className="btn btn-primary" style={{ alignSelf: "stretch", justifyContent: "center" }}>
                  {a.cta} <Icon name="arrow" />
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        <div className="card card-pad">
          <div className="section-head" style={{ marginBottom: 14 }}>
            <div className="section-title">
              <span className="tick" style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)" }} /> Continue Learning
            </div>
            {streak && (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12, fontWeight: 800, color: "var(--streak-strong, var(--streak))" }}>
                <Icon name="flame" size={14} /> {streak.current_streak}-day streak {streak.today_active ? "· active today" : ""}
              </span>
            )}
          </div>
          <div style={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 16, padding: 18 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 10, fontWeight: 800, color: "var(--accent-strong)", textTransform: "uppercase", letterSpacing: 1.2 }}>Learning Vector</div>
                <h4 style={{ fontSize: 16, fontWeight: 800, marginTop: 3 }}>{context?.title ?? "Start learning"}</h4>
                <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 3 }}>{pct}% concepts supported</div>
              </div>
              <span style={{ fontWeight: 800, fontSize: 17, color: "var(--accent-strong)" }}>{pct}%</span>
            </div>
            <div className="bar" style={{ marginBottom: 14 }}><i style={{ width: `${pct}%` }} /></div>
            <Link href="/app/learn" className="btn btn-primary" style={{ padding: "9px 18px", fontSize: 13, marginLeft: "auto" }}>
              {pct > 0 ? "Continue" : "Start Learning"} <Icon name="arrow" />
            </Link>
          </div>
        </div>

        <div className="card card-pad">
          <div className="section-head" style={{ marginBottom: 14 }}>
            <div className="section-title"><span className="tick" style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)" }} /> Upcoming</div>
          </div>
          {upcoming.length === 0 ? (
            <div style={{ textAlign: "center", padding: "18px 0", color: "var(--text-3)", fontSize: 13 }}>
              No upcoming reminders yet.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 14 }}>
              {upcoming.map((u) => (
                <div key={u.id} className="ws-row" style={{ cursor: "default" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span style={{ color: "var(--accent)", display: "inline-flex" }}><Icon name="calendar" size={18} /></span>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>{u.title}</div>
                      <div style={{ fontSize: 12, color: "var(--text-3)" }}>{dayLabel(u.due_at)}</div>
                    </div>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 800, color: "#fff", background: "#92400e", padding: "4px 10px", borderRadius: 8 }}>{dayLabel(u.due_at)}</span>
                </div>
              ))}
            </div>
          )}
          <Link href="/app/planner" className="btn btn-secondary btn-block">View Planner <Icon name="arrow" /></Link>
        </div>
      </div>

      {insight && (
        <div className="banner" style={{ marginTop: 22 }}>
          <span style={{ color: "var(--accent)", display: "inline-flex", marginTop: 2 }}><Icon name="lightbulb" size={20} /></span>
          <div>
            <b>ARIA Recommendation</b>
            <p>{insight}</p>
          </div>
        </div>
      )}
    </div>
  );
}
