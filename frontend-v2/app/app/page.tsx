"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/lib/toast";
import { useActiveContext, type ActiveContext } from "@/components/use-active-context";
import { pickNextAction } from "@/lib/next-action";

import { DashboardView, type WeekItem } from "@/components/dashboard-view";
import { milestonesPerWeek } from "@/lib/roadmap";

type Upcoming = { id: string; title: string; due_at: string };
type Chat = { id: string; title?: string | null; message_count?: number; last_message_at?: string | null; created_at: string };
type RoadmapDetail = { hours_per_week?: number | null; tiers: { topics: { id: string; title: string; ticked: boolean }[] }[] };

export default function HomePage() {
  const { context } = useActiveContext();
  return <ContextDashboard key={context?.id ?? "empty"} context={context} />;
}

function ContextDashboard({ context }: { context: ActiveContext | null }) {
  const [streak, setStreak] = useState<{ current_streak: number; today_active: boolean } | null>(null);
  const [overdue, setOverdue] = useState<{ id: string; title: string } | null>(null);
  const [dueNotes, setDueNotes] = useState<{ id: string; title: string }[]>([]);
  const [focusDecision, setFocusDecision] = useState<{ reason: string; concept?: string } | null>(null);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [upcoming, setUpcoming] = useState<{ id: string; title: string; due_at: string }[]>([]);
  const [lastChat, setLastChat] = useState<{ id: string; title: string } | null>(null);
  const [milestones, setMilestones] = useState<WeekItem[]>([]);
  const [progress, setProgress] = useState<{ contextId: string; pct: number } | null>(null);
  const [progressError, setProgressError] = useState(false);
  const [retryNonce, setRetryNonce] = useState(0);
  const [firstSteps, setFirstSteps] = useState<{ learned: boolean | null; reviewCreated: boolean | null; reviewTaken: boolean | null; noteSaved: boolean | null; materialAdded: boolean | null }>();

  useEffect(() => {
    if (!context) return;
    let cancelled = false;
    Promise.allSettled([
      api<Chat[]>(`/api/v1/study/sessions?context_id=${context.id}`),
      api<{ submitted_attempt_count?: number }[]>(`/api/v1/assessments?context_id=${context.id}`),
      api<unknown[]>(`/api/v1/notes?context_id=${context.id}`),
      api<{ processing_status: string }[]>(`/api/v1/resources?context_id=${context.id}`),
    ]).then(([sessions, assessments, notes, resources]) => {
      if (cancelled) return;
      if (sessions.status === "fulfilled") {
        const chats = sessions.value.filter((item) => (item.message_count ?? 0) > 0)
          .sort((a, b) => (b.last_message_at ?? b.created_at).localeCompare(a.last_message_at ?? a.created_at));
        setLastChat(chats[0] ? { id: chats[0].id, title: chats[0].title ?? "Your last chat" } : null);
      }
      setFirstSteps({
        learned: sessions.status === "fulfilled" ? sessions.value.some(item => (item.message_count ?? 0) > 0) : null,
        reviewCreated: assessments.status === "fulfilled" ? assessments.value.length > 0 : null,
        reviewTaken: assessments.status !== "fulfilled" ? null
          : assessments.value.some(item => (item.submitted_attempt_count ?? 0) > 0) ? true
          : assessments.value.every(item => item.submitted_attempt_count !== undefined) ? false : null,
        noteSaved: notes.status === "fulfilled" ? notes.value.length > 0 : null,
        materialAdded: resources.status === "fulfilled" ? resources.value.some(item => item.processing_status === "READY") : null,
      });
    });
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
    // This week: the next milestones of the newest roadmap, paced by its weekly time.
    api<{ id: string }[]>(`/api/v1/roadmaps?context_id=${context.id}`)
      .then(async (list) => {
        if (!list[0]) return;
        const detail = await api<RoadmapDetail>(`/api/v1/roadmaps/${list[0].id}`);
        if (cancelled) return;
        const open = detail.tiers.flatMap((tier) => tier.topics).filter((topic) => !topic.ticked);
        setMilestones(open.slice(0, milestonesPerWeek(detail.hours_per_week))
          .map((topic) => ({ key: topic.id, title: topic.title, kind: "milestone" as const })));
      })
      .catch(() => {});
    api<{ states: { concept_name?: string; state: string }[]; decisions: { decision_type: string; reason: string; concept_id?: string | null }[] }>(
      `/api/v1/contexts/${context.id}/adaptation`,
    )
      .then((s) => {
        if (cancelled) return;
        setProgressError(false);
        const focus = s.decisions.filter((d) => d.decision_type === "FOCUS_STUDY")[0];
        setProgress({ contextId: context.id, pct:
          s.states.length
            ? Math.round((s.states.filter((x) => x.state === "SUPPORTED").length / s.states.length) * 100)
            : 0,
        });
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
      .catch(() => { if (!cancelled) setProgressError(true); });
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
  }, [context, retryNonce]);


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

  const review = async (id: string, outcome: "again" | "good") => {
    try {
      await api(`/api/v1/notes/${id}/review`, { method: "POST", body: JSON.stringify({ outcome }) });
      setDueNotes(prev => prev.filter(note => note.id !== id));
    } catch (error) {
      toast(error instanceof ApiError ? error.message : "Could not record the review.", "error");
    }
  };

  const week: WeekItem[] = [
    ...upcoming.filter((item) => new Date(item.due_at).getTime() - nowMs <= 7 * 86_400_000)
      .map((item) => ({ key: item.id, title: item.title, kind: "deadline" as const, due: item.due_at })),
    ...milestones,
  ];

  return <DashboardView title={context?.title ?? "Start learning"}
    pct={progress?.contextId === context?.id ? progress?.pct ?? null : null}
    nextAction={nextAction} streak={streak} week={week} lastChat={lastChat}
    dueNotes={dueNotes} onReview={review}
    progressError={progressError} onRetry={() => setRetryNonce(n => n + 1)} firstSteps={firstSteps} />;
}
