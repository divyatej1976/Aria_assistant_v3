"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { api } from "../../lib/api";
import { useActiveContext } from "../../components/use-active-context";

type ConceptState = {
  concept_id: string;
  concept_name: string;
  state: string;
  confidence: number;
  reason: string;
};

type Decision = { concept_id: string | null; decision_type: string; reason: string };

type CycleSummary = { states: ConceptState[]; decisions: Decision[] };

function stateChip(state: string): { label: string; cls: string; pulse?: boolean } {
  switch (state) {
    case "SUPPORTED":
      return { label: "Strong", cls: "bg-tertiary-container text-on-tertiary-container" };
    case "NEEDS_REVIEW":
      return { label: "Attention Needed", cls: "bg-error-container text-on-error-container" };
    case "DEVELOPING":
      return { label: "Learning", cls: "bg-surface-variant text-on-surface-variant", pulse: true };
    default:
      return { label: "Not enough evidence", cls: "bg-surface-variant text-on-surface-variant/70" };
  }
}

export default function DashboardPage() {
  const { context: active, contexts, loading, setActiveContextId } = useActiveContext();
  const [summary, setSummary] = useState<CycleSummary | null>(null);
  const [consistency, setConsistency] = useState<{
    current_streak: number;
    today_active: boolean;
  } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ current_streak: number; today_active: boolean }>("/api/v1/progress/consistency")
      .then(setConsistency)
      .catch(() => {
        // Consistency is optional for rendering.
      });
    if (!active) return;
    api<CycleSummary>(`/api/v1/contexts/${active.id}/adaptation`)
      .then(setSummary)
      .catch((requestError: unknown) =>
        setError(requestError instanceof Error ? requestError.message : "Unable to load progress")
      );
  }, [active]);

  const mastery =
    summary && summary.states.length > 0
      ? Math.round(
          summary.states.reduce((total, state) => total + state.confidence, 0) / summary.states.length,
        )
      : 0;
  const focus = summary?.decisions.filter((d) => d.decision_type === "FOCUS_STUDY") ?? [];
  const insight = summary?.decisions.find((d) => d.decision_type === "RETEST_TARGETED")?.reason;

  if (loading) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <p className="text-body-md text-on-surface-variant">Loading your workspace…</p>
      </div>
    );
  }

  if (!active) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <div className="bg-surface shadow-extruded rounded-3xl p-8 max-w-xl">
          <p className="text-label-md text-secondary uppercase tracking-widest mb-2">Home</p>
          <h2 className="text-headline-md text-on-surface mb-4">Start with your learning material</h2>
          <p className="text-body-md text-on-surface-variant mb-6">
            Add a PDF or paste text so ARIA can use your material during Study.
          </p>
          <Link
            href="/onboarding"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-xl shadow-extruded btn-extruded bg-surface text-label-md text-secondary"
          >
            Add material
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </Link>
        </div>
        {error && <p className="text-label-md text-error mt-4" role="alert">{error}</p>}
      </div>
    );
  }

  return (
    <div className="p-container-padding md:p-section-margin w-full max-w-7xl mx-auto flex flex-col gap-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-headline-xl text-on-background">Mission Control</h2>
          <p className="text-body-lg text-on-surface-variant mt-2">
            Active Goal: <span className="font-semibold text-on-surface">{active.title}</span>
          </p>
        </div>
        {contexts.length > 1 && (
          <label className="flex flex-col gap-1 min-w-[220px]">
            <span className="text-label-sm text-on-surface-variant">Learning context</span>
            <select
              className="h-12 bg-surface rounded-xl input-injected px-4 text-label-md text-on-surface"
              value={active.id}
              onChange={(event) => setActiveContextId(event.target.value)}
            >
              {contexts.map((context) => (
                <option key={context?.id} value={context?.id}>{context?.title}</option>
              ))}
            </select>
          </label>
        )}
      </div>

      {/* Consistency strip */}
      {consistency && (
        <div className="bg-surface shadow-extruded rounded-3xl p-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-secondary ms-fill">local_fire_department</span>
            <span className="text-body-md text-on-background">
              {consistency.current_streak}-day learning streak
            </span>
          </div>
          <span className={`px-4 py-2 rounded-full text-label-md ${consistency.today_active ? "bg-tertiary-container text-on-tertiary-container" : "bg-surface-container-low text-on-surface-variant"}`}>
            {consistency.today_active ? "Active today" : "Study today to keep it alive"}
          </span>
        </div>
      )}

      {/* Bento grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
        {/* Overall Mastery */}
        <div className="col-span-1 md:col-span-8 bg-surface rounded-3xl p-8 shadow-extruded flex flex-col justify-between">
          <div>
            <h3 className="text-headline-md text-on-background flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">donut_large</span>
              Overall Mastery
            </h3>
            <p className="text-body-md text-on-surface-variant mt-1">
              {summary?.states.length
                ? "Aggregated from your current concept confidence."
                : "Complete an assessment to give ARIA evidence to work with."}
            </p>
          </div>
          <div className="mt-8">
            <div className="flex justify-between items-end mb-2">
              <span className="text-headline-lg text-secondary">{mastery}%</span>
              <span className="text-label-sm text-on-surface-variant uppercase tracking-wider">
                {summary?.states.length ?? 0} concept{summary?.states.length === 1 ? "" : "s"}
              </span>
            </div>
            <div className="w-full h-4 rounded-full shadow-injected bg-surface relative overflow-hidden">
              <div className="absolute top-0 left-0 h-full bg-secondary rounded-full shadow-extruded transition-all duration-1000 ease-out" style={{ width: `${mastery}%` }} />
            </div>
          </div>
        </div>

        {/* Primary action */}
        <div className="col-span-1 md:col-span-4 bg-surface rounded-3xl p-8 shadow-extruded flex flex-col items-center justify-center text-center">
          <div className="w-24 h-24 rounded-full shadow-injected bg-surface flex items-center justify-center mb-6">
            <span className="material-symbols-outlined text-4xl text-secondary ms-fill">play_arrow</span>
          </div>
          <h3 className="text-headline-md text-on-background mb-2">Ready for more?</h3>
          <Link
            href="/app/learn"
            className="mt-4 px-8 py-4 w-full rounded-xl shadow-extruded btn-extruded bg-secondary text-on-secondary text-label-md border border-secondary-container"
          >
            Continue Learning
          </Link>
        </div>

        {/* Concept Mastery */}
        <div className="col-span-1 md:col-span-6 bg-surface rounded-3xl p-8 shadow-extruded">
          <h3 className="text-headline-md text-on-background mb-6 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary">psychology</span>
            Concept Mastery
          </h3>
          {summary && summary.states.length > 0 ? (
            <ul className="flex flex-col gap-4">
              {summary.states.map((state) => {
                const chip = stateChip(state.state);
                return (
                  <li key={state.concept_id} className="flex justify-between items-center p-4 rounded-lg bg-surface shadow-injected">
                    <span className="text-body-md text-on-background">{state.concept_name}</span>
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold shadow-extruded flex items-center gap-1 ${chip.cls}`}>
                      {chip.pulse && <span className="w-2 h-2 rounded-full bg-secondary shadow-extruded animate-pulse"></span>}
                      {chip.label}
                    </span>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="text-body-md text-on-surface-variant">
              No learning signal yet. Complete an assessment to give ARIA evidence to work with.
            </p>
          )}
        </div>

        {/* Insights & Actions */}
        <div className="col-span-1 md:col-span-6 bg-surface rounded-3xl p-8 shadow-extruded relative overflow-hidden">
          <div className="absolute -right-8 -bottom-8 w-48 h-48 bg-secondary-fixed opacity-20 rounded-full blur-3xl"></div>
          <h3 className="text-headline-md text-on-background mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-tertiary">lightbulb</span>
            Insights &amp; Actions
          </h3>
          {focus.length > 0 ? (
            <div className="p-6 rounded-xl bg-surface-container-low border border-surface-variant shadow-injected mt-4">
              <p className="text-body-md text-on-background leading-relaxed">{focus[0].reason}</p>
              <Link
                href="/app/progress"
                className="mt-4 px-6 py-2 rounded-lg shadow-extruded btn-extruded bg-surface text-secondary text-label-sm inline-flex items-center gap-2"
              >
                Review
                <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
              </Link>
            </div>
          ) : (
            <p className="text-body-md text-on-surface-variant mt-4">
              {insight ?? "ARIA will adapt Study when the evidence supports a useful change."}
            </p>
          )}
        </div>
      </div>

      {error && <p className="text-label-md text-error" role="alert">{error}</p>}
    </div>
  );
}
