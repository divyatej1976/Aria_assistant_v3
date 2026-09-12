"use client";

import { useEffect, useState } from "react";
import { Icon, type IconName } from "@/components/icons";
import { api } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { ErrorState, Loading } from "@/components/states";

type Consistency = {
  current_streak: number;
  longest_streak: number;
  active_this_week: number;
  active_this_month: number;
  today_active: boolean;
  heatmap: { date: string; count: number }[];
};
type Badge = { code: string; label: string; earned: boolean; earned_at: string | null };
type Activity = { id: string; activity_type: string; occurred_on: string };
type ConceptState = { state: string };

const BADGE_META: Record<string, { icon: IconName; gradient: string }> = {
  first_assessment: { icon: "clipboard", gradient: "linear-gradient(135deg,#fbbf24,#f97316)" },
  first_study: { icon: "book", gradient: "linear-gradient(135deg,#34d399,#0ea5e9)" },
  first_revision: { icon: "refresh", gradient: "linear-gradient(135deg,#38bdf8,#6366f1)" },
  first_planned_task: { icon: "check", gradient: "linear-gradient(135deg,#a78bfa,#ec4899)" },
  streak_3: { icon: "flame", gradient: "linear-gradient(135deg,#fb923c,#ef4444)" },
  streak_7: { icon: "flame", gradient: "linear-gradient(135deg,#fb7185,#dc2626)" },
  streak_30: { icon: "crown", gradient: "linear-gradient(135deg,#e2b93b,#d97706)" },
  concept_supported: { icon: "lightbulb", gradient: "linear-gradient(135deg,#a78bfa,#ec4899)" },
};

const ACTIVITY_META: Record<string, { label: string; icon: IconName }> = {
  assessment: { label: "Assessment", icon: "clipboard" },
  study: { label: "Study session", icon: "book" },
  revision: { label: "Revision", icon: "refresh" },
  planned_task: { label: "Planned task completed", icon: "check" },
};

function heatLevel(count: number): number {
  if (count <= 0) return 0;
  if (count === 1) return 1;
  if (count === 2) return 2;
  if (count <= 4) return 3;
  return 4;
}

function dayLabel(value: string): string {
  return new Date(value.length === 10 ? value + "T00:00:00" : value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export default function ProgressPage() {
  const { context } = useActiveContext();
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [consistency, setConsistency] = useState<Consistency | null>(null);
  const [badges, setBadges] = useState<Badge[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [supportedPct, setSupportedPct] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const jobs: Promise<void>[] = [
        api<Consistency>("/api/v1/progress/consistency").then((c) => {
          if (!cancelled) setConsistency(c);
        }),
        api<Badge[]>("/api/v1/progress/badges").then((b) => {
          if (!cancelled) setBadges(b);
        }),
        api<Activity[]>("/api/v1/progress/activity").then((a) => {
          if (!cancelled) setActivity(a);
        }),
      ];
      if (context) {
        jobs.push(
          api<{ states: ConceptState[] }>(`/api/v1/contexts/${context.id}/adaptation`).then((s) => {
            if (cancelled) return;
            const supported = s.states.filter((x) => x.state === "SUPPORTED").length;
            setSupportedPct(s.states.length ? Math.round((supported / s.states.length) * 100) : 0);
          }),
        );
      }
      const results = await Promise.allSettled(jobs);
      if (!cancelled && results.some((r) => r.status === "rejected")) {
        setFailed(true);
      }
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [context]);

  if (loading && !consistency) {
    return <Loading label="your progress" />;
  }
  if (failed) {
    return <ErrorState message="This screen could not be loaded." onRetry={() => window.location.reload()} />;
  }

  const rangeLabel =
    consistency && consistency.heatmap.length
      ? `${dayLabel(consistency.heatmap[0].date)} – ${dayLabel(consistency.heatmap[consistency.heatmap.length - 1].date)}`
      : "Last 26 weeks";

  const rings = [
    { label: "Overall", v: supportedPct ?? 0 },
    { label: "Weekly", v: consistency ? Math.round((consistency.active_this_week / 7) * 100) : 0 },
    { label: "Monthly", v: consistency ? Math.round((consistency.active_this_month / 30) * 100) : 0 },
  ];

  return (
    <div>
      <div className="section-head">
        <div>
          <h1 className="pg-title">Your Progress</h1>
          <p className="pg-sub">See how far you&apos;ve come.</p>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "center", gap: 52, flexWrap: "wrap", marginBottom: 34 }}>
        {rings.map((m) => (
          <div key={m.label} style={{ textAlign: "center" }}>
            <div className="ring" style={{ "--p": m.v, "--r": "60px" } as React.CSSProperties}>
              <span className="r-n" style={{ color: "var(--accent)" }}>{m.v}%</span>
            </div>
            <div style={{ fontSize: 12, fontWeight: 800, color: "var(--text-2)", marginTop: 14, textTransform: "uppercase", letterSpacing: 1 }}>{m.label} Progress</div>
          </div>
        ))}
      </div>

      <div className="card card-pad" style={{ marginBottom: 26 }}>
        <div className="section-head">
          <h2 style={{ fontSize: 19, fontWeight: 800 }}>Learning Activity</h2>
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-2)" }}>{rangeLabel}</span>
        </div>
        <div style={{ display: "flex", gap: 44, margin: "8px 0 18px", flexWrap: "wrap" }}>
          <div className="stat-col"><div className="n">{consistency?.active_this_week ?? 0}</div><div className="l">Active Days · Week</div></div>
          <div className="stat-col"><div className="n">{consistency?.active_this_month ?? 0}</div><div className="l">Active Days · Month</div></div>
          <div className="stat-col"><div className="n" style={{ color: "var(--streak)", display: "flex", alignItems: "center", gap: 4 }}><Icon name="flame" size={22} /> {consistency?.current_streak ?? 0}</div><div className="l">Current Streak</div></div>
          <div className="stat-col"><div className="n" style={{ color: "var(--accent)" }}>{consistency?.longest_streak ?? 0}</div><div className="l">Longest Streak</div></div>
        </div>
        {consistency ? (
          <div className="heat-wrap">
            <div className="heat in">
              {consistency.heatmap.map((d) => (
                <div
                  key={d.date}
                  className={`cell l${heatLevel(d.count)}`}
                  title={`${dayLabel(d.date)} · ${d.count} ${d.count === 1 ? "session" : "sessions"}`}
                />
              ))}
            </div>
          </div>
        ) : (
          <p style={{ fontSize: 13, color: "var(--text-1)", margin: 0 }}>No activity data yet.</p>
        )}
      </div>

      <h2 style={{ fontSize: 19, fontWeight: 800, marginBottom: 16 }}>Achievements &amp; Badges</h2>
      {badges.length === 0 ? (
        <div className="empty-state">
          <Icon name="trophy" size={30} />
          <p style={{ margin: "10px 0 0", fontSize: 14, color: "var(--text-1)" }}>Earn badges by studying, taking assessments, and keeping streaks.</p>
        </div>
      ) : (
        <div className="badge-grid" style={{ marginBottom: 26 }}>
          {badges.map((b) => {
            const meta = BADGE_META[b.code] ?? { icon: "trophy" as IconName, gradient: "var(--accent-grad)" };
            return (
              <div className="badge-card" key={b.code}>
                <div
                  className="badge-ic"
                  style={b.earned ? { background: meta.gradient } : { background: "var(--bg-2)", border: "1px solid var(--border)" }}
                >
                  <Icon name={b.earned ? meta.icon : "lock"} size={26} />
                </div>
                <b style={{ fontSize: 13, display: "block" }}>{b.label}</b>
                <span style={{ fontSize: 10, color: "var(--text-1)", fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.8 }}>
                  {b.earned ? "Unlocked" : "Locked"}
                </span>
              </div>
            );
          })}
        </div>
      )}

      <div className="card card-pad">
        <h2 style={{ fontSize: 17, fontWeight: 800, marginBottom: 6 }}>Recent Activity</h2>
        {activity.length === 0 ? (
          <p style={{ fontSize: 13, color: "var(--text-1)", margin: 0 }}>
            No learning activity yet — start a study session or take an assessment.
          </p>
        ) : (
          activity.map((e) => {
            const meta = ACTIVITY_META[e.activity_type];
            return (
              <div className="kv" key={e.id}>
                <span className="k"><Icon name={meta?.icon ?? "activity"} size={16} /> {meta?.label ?? e.activity_type}</span>
                <span className="v">{dayLabel(e.occurred_on)}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}