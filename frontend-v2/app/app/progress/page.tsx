"use client";

import { TopicList, type TopicState } from "@/components/topic-list";
import { useEffect, useState } from "react";
import { PageGuide } from "@/components/page-guide";
import { Icon, type IconName } from "@/components/icons";
import { api } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { ErrorState, Loading } from "@/components/states";
import { Reveal } from "@/components/motion-system";

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
type ConceptState = TopicState;

/** Topic states in teaching order, with the colour each one gets in the bar. */
const STATE_META: { state: string; label: string; tone: string }[] = [
  { state: "SUPPORTED", label: "Strong", tone: "strong" },
  { state: "DEVELOPING", label: "Developing", tone: "developing" },
  { state: "NEEDS_REVIEW", label: "Needs review", tone: "review" },
  { state: "NOT_STARTED", label: "Not started", tone: "new" },
];

function isoDay(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

const BADGE_META: Record<string, { icon: IconName; gradient: string }> = {
  first_assessment: { icon: "clipboard", gradient: "var(--badge-grad-milestone)" },
  first_study: { icon: "book", gradient: "var(--badge-grad-study)" },
  first_revision: { icon: "refresh", gradient: "var(--badge-grad-review)" },
  first_planned_task: { icon: "check", gradient: "var(--badge-grad-study)" },
  streak_3: { icon: "flame", gradient: "var(--badge-grad-streak)" },
  streak_7: { icon: "flame", gradient: "var(--badge-grad-streak)" },
  streak_30: { icon: "flame", gradient: "var(--badge-grad-milestone)" },
  concept_supported: { icon: "lightbulb", gradient: "var(--badge-grad-review)" },
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
  const [stateCounts, setStateCounts] = useState<Record<string, number> | null>(null);
  const [topics, setTopics] = useState<TopicState[]>([]);

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
            const counts: Record<string, number> = {};
            for (const item of s.states) {
              const key = STATE_META.some((meta) => meta.state === item.state) ? item.state : "NOT_STARTED";
              counts[key] = (counts[key] ?? 0) + 1;
            }
            setStateCounts(counts);
            setTopics(s.states);
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

  const totalTopics = stateCounts ? Object.values(stateCounts).reduce((sum, n) => sum + n, 0) : 0;
  const strongTopics = stateCounts?.SUPPORTED ?? 0;
  // Days studied, by date, from the activity heatmap.
  const studied = new Map((consistency?.heatmap ?? []).map((d) => [d.date.slice(0, 10), d.count]));
  const today = new Date();
  const monday = new Date(today);
  monday.setDate(today.getDate() - ((today.getDay() + 6) % 7));
  const week = Array.from({ length: 7 }, (_, i) => {
    const day = new Date(monday);
    day.setDate(monday.getDate() + i);
    return { key: isoDay(day), letter: day.toLocaleDateString(undefined, { weekday: "narrow" }), name: day.toLocaleDateString(undefined, { weekday: "long" }),
      count: studied.get(isoDay(day)) ?? 0, isToday: isoDay(day) === isoDay(today), future: day > today };
  });
  const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
  const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
  const month = Array.from({ length: daysInMonth }, (_, i) => {
    const day = new Date(today.getFullYear(), today.getMonth(), i + 1);
    return { key: isoDay(day), n: i + 1, count: studied.get(isoDay(day)) ?? 0, isToday: i + 1 === today.getDate(), future: day > today };
  });
  const monthName = today.toLocaleDateString(undefined, { month: "long" });

  // Month labels for the heatmap: the column where each new month first appears.
  const monthMarks: { col: number; label: string }[] = [];
  if (consistency) {
    let lastMonth = -1;
    consistency.heatmap.forEach((d, i) => {
      const date = new Date(d.date.length === 10 ? d.date + "T00:00:00" : d.date);
      const m = date.getMonth();
      if (m !== lastMonth) {
        const col = Math.floor(i / 7);
        // A partial first month leaves no room for its label; let the next month's label take its place.
        if (monthMarks.length && col - monthMarks[monthMarks.length - 1].col < 3) monthMarks.pop();
        monthMarks.push({ col, label: date.toLocaleDateString(undefined, { month: "short" }) });
        lastMonth = m;
      }
    });
  }
  const totalSessions = consistency?.heatmap.reduce((sum, d) => sum + d.count, 0) ?? 0;
  const heatCols = consistency ? Math.ceil(consistency.heatmap.length / 7) : 0;

  return (
    <div>
      <div className="section-head">
        <div>
          <h1 className="pg-title">Your progress</h1>
          <p className="pg-sub">See how far you&apos;ve come.</p>
        </div>
      </div>
      <PageGuide page="progress" />

      <Reveal>
        <div className="pg-overview">
          <section className="pg-card" aria-labelledby="pg-topics">
            <p className="pg-card-eyebrow" id="pg-topics">Topics</p>
            <p className="pg-big">{totalTopics ? <>{strongTopics}<span> of {totalTopics} strong</span></> : <span className="pg-none">No topics yet</span>}</p>
            {totalTopics > 0 ? <>
              <div className="pg-stack" role="img" aria-label={STATE_META.map((m) => `${stateCounts?.[m.state] ?? 0} ${m.label.toLowerCase()}`).join(", ")}>
                {STATE_META.map((m) => (stateCounts?.[m.state] ?? 0) > 0 && <span key={m.state} className={`pg-seg ${m.tone}`} style={{ flexGrow: stateCounts?.[m.state] ?? 0 }} />)}
              </div>
              <ul className="pg-legend">
                {STATE_META.map((m) => <li key={m.state}><i className={`pg-dot ${m.tone}`} />{m.label}<b>{stateCounts?.[m.state] ?? 0}</b></li>)}
              </ul>
            </> : <p className="pg-hint">Chat with ARIA and take a quiz; topics appear here and turn Strong as your answers show it.</p>}
          </section>

          <section className="pg-card pg-week" aria-labelledby="pg-week-title">
            <p className="pg-card-eyebrow" id="pg-week-title">This week</p>
            <p className="pg-big">{consistency?.active_this_week ?? 0}<span> of 7 days</span></p>
            <ol className="pg-days">
              {week.map((d) => (
                <li key={d.key} className={`${d.count ? "on" : ""}${d.isToday ? " today" : ""}${d.future ? " future" : ""}`} title={`${d.name}: ${d.count ? `${d.count} ${d.count === 1 ? "session" : "sessions"}` : "no study"}`}>
                  <span className="pg-day-dot">{d.count ? <Icon name="check" size={14} /> : null}</span>
                  <small>{d.letter}</small>
                </li>
              ))}
            </ol>
            <p className="pg-streak"><Icon name="flame" size={16} /> {consistency?.current_streak ?? 0}-day streak<span> · best {consistency?.longest_streak ?? 0}</span></p>
          </section>

          <section className="pg-card" aria-labelledby="pg-month-title">
            <p className="pg-card-eyebrow" id="pg-month-title">{monthName}</p>
            <p className="pg-big">{consistency?.active_this_month ?? 0}<span> {consistency?.active_this_month === 1 ? "day" : "days"} studied</span></p>
            <div className="pg-month" style={{ "--first": (monthStart.getDay() + 6) % 7 } as React.CSSProperties}>
              {month.map((d) => (
                <span key={d.key} className={`l${d.future ? "x" : heatLevel(d.count)}${d.isToday ? " today" : ""}`} title={`${monthName} ${d.n}: ${d.count} ${d.count === 1 ? "session" : "sessions"}`}>{d.n}</span>
              ))}
            </div>
          </section>
        </div>

        {/* Which topics are weak or strong, named, from quiz answers. */}
        <section className="pg-card pg-topics-list" aria-labelledby="pg-topics-list">
          <p className="pg-card-eyebrow" id="pg-topics-list">Your topics</p>
          <TopicList topics={topics} empty="Take a quiz: each topic it covers shows up here as Needs work, Getting there or Strong." />
        </section>
      </Reveal>

      <Reveal delay={60}>
      <div className="card card-pad" style={{ marginBottom: 26 }}>
        <div className="section-head">
          <h2 style={{ fontSize: 19, fontWeight: 800 }}>Learning activity</h2>
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-2)" }}>{rangeLabel}</span>
        </div>
        <div className="activity-block">
        <div className="pg-stats">
          <div className="stat-col"><div className="n">{consistency?.active_this_week ?? 0}</div><div className="l">Active days · Week</div></div>
          <div className="stat-col"><div className="n">{consistency?.active_this_month ?? 0}</div><div className="l">Active days · Month</div></div>
          <div className="stat-col"><div className="n" style={{ color: "var(--streak)", display: "flex", alignItems: "center", justifyContent: "center", gap: 4 }}><Icon name="flame" size={22} /> {consistency?.current_streak ?? 0}</div><div className="l">Current streak</div></div>
          <div className="stat-col"><div className="n" style={{ color: "var(--accent)" }}>{consistency?.longest_streak ?? 0}</div><div className="l">Longest streak</div></div>
        </div>
        {consistency ? (
          <>
          <div className="heat-wrap">
            <div className="heat-inner" style={{ "--heat-cols": heatCols } as React.CSSProperties}>
              <div className="heat-months">
                {monthMarks.map((m, i) => (
                  <span key={`${m.label}-${i}`} style={{ gridColumn: m.col + 1 }}>{m.label}</span>
                ))}
              </div>
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
          </div>
          <div className="heat-footer">
            <span>{totalSessions} {totalSessions === 1 ? "session" : "sessions"} in this range</span>
            <span className="heat-legend">Less
              <i className="cell l0" /><i className="cell l1" /><i className="cell l2" /><i className="cell l3" /><i className="cell l4" />
              More
            </span>
          </div>
          </>
        ) : (
          <p style={{ fontSize: 13, color: "var(--text-1)", margin: 0 }}>No activity data yet.</p>
        )}
        </div>
      </div>
      </Reveal>

      <Reveal delay={120}>
      <h2 style={{ fontSize: 19, fontWeight: 800, marginBottom: 16 }}>Achievements &amp; badges</h2>
      {badges.length === 0 ? (
        <div className="empty-state">
          <Icon name="trophy" size={30} />
          <p style={{ margin: "10px 0 0", fontSize: 14, color: "var(--text-1)" }}>Earn badges by studying, taking assessments, and keeping streaks.</p>
        </div>
      ) : (
        <div className="badge-grid" style={{ marginBottom: 26 }}>
          {badges.map((b) => {
            const meta = BADGE_META[b.code] ?? { icon: "trophy" as IconName, gradient: "var(--accent-grad)" };
            const streakTarget = Number(/^streak_(\d+)$/.exec(b.code)?.[1] ?? 0);
            return (
              <div className={`badge-card${b.earned ? " earned" : " locked"}`} key={b.code}>
                {b.earned && <span className="badge-check" aria-hidden="true"><Icon name="check" size={12} /></span>}
                <div className="badge-ic" style={b.earned ? { background: meta.gradient } : undefined}>
                  <Icon name={meta.icon} size={26} />
                </div>
                <b>{b.label}</b>
                <span className="badge-state">
                  {b.earned
                    ? b.earned_at
                      ? dayLabel(b.earned_at)
                      : "Unlocked"
                    : streakTarget
                      ? `${Math.min(consistency?.current_streak ?? 0, streakTarget)} / ${streakTarget} days`
                      : "Locked"}
                </span>
              </div>
            );
          })}
        </div>
      )}
      </Reveal>

      <Reveal delay={180}>
      <div className="card card-pad">
        <h2 className="card-heading">Recent activity</h2>
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
      </Reveal>
    </div>
  );
}
