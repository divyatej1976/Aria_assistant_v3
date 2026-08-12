"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { api } from "../../../lib/api";
import { useActiveContext } from "../../../components/use-active-context";

type ConceptState = {
  concept_id: string;
  concept_name: string;
  state: string;
  confidence: number;
  reason: string;
};

type Decision = { concept_id: string | null; decision_type: string; reason: string };

type EvidenceRecord = {
  id: string;
  concept_id: string;
  concept_name: string;
  signal: string;
  valid: boolean;
  created_at: string;
};

type Point = { pct: number };

function buildSeries(evidence: EvidenceRecord[]): Point[] {
  let correct = 0;
  let total = 0;
  const points: Point[] = [];
  for (const item of evidence) {
    total += 1;
    if (item.signal === "CORRECT") correct += 1;
    points.push({ pct: total ? Math.round((correct / total) * 100) : 0 });
  }
  return points;
}

function TrajectoryChart({ points }: { points: Point[] }) {
  if (points.length < 2) return null;
  const coords = points.map((point, index) => ({
    x: (index / (points.length - 1)) * 100,
    y: 50 - (point.pct / 100) * 45,
  }));
  const line = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const area = `${line} L100,50 L0,50 Z`;
  return (
    <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 50">
      <defs>
        <linearGradient id="mastery-fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#4648d4"></stop>
          <stop offset="100%" stopColor="#f6f9ff" stopOpacity="0"></stop>
        </linearGradient>
      </defs>
      <path d={line} fill="none" stroke="#4648d4" strokeLinecap="round" strokeWidth="2"></path>
      <path d={area} fill="url(#mastery-fill)" opacity="0.2"></path>
      {coords.map((c, i) => (
        <circle key={i} cx={c.x.toFixed(1)} cy={c.y.toFixed(1)} r="1.5" fill="#f6f9ff" stroke="#4648d4" strokeWidth="1" />
      ))}
    </svg>
  );
}

export default function ProgressPage() {
  const { context, loading } = useActiveContext();
  const [states, setStates] = useState<ConceptState[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [evidence, setEvidence] = useState<EvidenceRecord[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!context) return;
    api<{ states: ConceptState[]; decisions: Decision[] }>(`/api/v1/contexts/${context.id}/adaptation`)
      .then((summary) => {
        setStates(summary.states);
        setDecisions(summary.decisions);
      })
      .catch((requestError: unknown) =>
        setError(requestError instanceof Error ? requestError.message : "Unable to load progress")
      );
    api<EvidenceRecord[]>(`/api/v1/contexts/${context.id}/evidence`)
      .then(setEvidence)
      .catch(() => {
        // Evidence is optional for rendering.
      });
  }, [context]);

  const series = buildSeries(evidence);
  const recommendation =
    decisions.find((d) => d.decision_type === "RETEST_TARGETED")?.reason ||
    decisions.find((d) => d.decision_type === "FOCUS_STUDY")?.reason ||
    "";

  async function invalidate(evidenceId: string, contextId: string) {
    setError("");
    try {
      await api(`/api/v1/contexts/${contextId}/evidence/${evidenceId}/invalidate`, {
        method: "POST",
      });
      const [summary, evidenceList] = await Promise.all([
        api<{ states: ConceptState[]; decisions: Decision[] }>(`/api/v1/contexts/${contextId}/adaptation`),
        api<EvidenceRecord[]>(`/api/v1/contexts/${contextId}/evidence`),
      ]);
      setStates(summary.states);
      setDecisions(summary.decisions);
      setEvidence(evidenceList);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update evidence");
    }
  }

  if (loading) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <p className="text-body-md text-on-surface-variant">Loading progress…</p>
      </div>
    );
  }

  if (!context) {
    return (
      <div className="p-container-padding md:p-section-margin">
        <div className="bg-surface shadow-extruded rounded-3xl p-8 max-w-xl">
          <h2 className="text-headline-md text-on-surface mb-4">No learning context yet</h2>
          <p className="text-body-md text-on-surface-variant mb-6">Set up your context to start tracking progress.</p>
          <Link href="/onboarding" className="inline-flex items-center gap-2 px-8 py-4 rounded-xl shadow-extruded btn-extruded bg-surface text-label-md text-secondary">
            Initialize learning journey
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-container-padding md:p-section-margin w-full max-w-7xl mx-auto flex flex-col gap-8">
      <div>
        <h2 className="text-headline-xl text-on-background">Progress &amp; Assessment</h2>
        <p className="text-body-lg text-on-surface-variant mt-2">{context.title}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Mastery trajectory */}
        <div className="lg:col-span-2 bg-surface rounded-3xl p-6 md:p-8 shadow-extruded flex flex-col min-h-[360px]">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h3 className="text-headline-md text-on-background">Mastery Trajectory</h3>
              <p className="text-body-md text-on-surface-variant">Correct-answer trend from your evidence</p>
            </div>
            <span className="px-4 py-2 rounded-full shadow-extruded bg-surface text-label-sm text-secondary flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]">calendar_month</span>
              {evidence.length} observations
            </span>
          </div>
          <div className="flex-1 bg-surface shadow-injected rounded-2xl relative p-4 overflow-hidden">
            {series.length >= 2 ? (
              <TrajectoryChart points={series} />
            ) : (
              <div className="h-full flex items-center justify-center">
                <p className="text-body-md text-on-surface-variant text-center px-6">
                  No learning signal yet. Complete an assessment to give ARIA evidence to chart.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Recommended action */}
        <div className="bg-surface rounded-3xl p-6 md:p-8 shadow-extruded flex flex-col justify-between">
          <div>
            <div className="w-12 h-12 rounded-full bg-surface shadow-extruded flex items-center justify-center mb-6 text-tertiary">
              <span className="material-symbols-outlined ms-fill">psychology</span>
            </div>
            <h3 className="text-headline-md text-on-background mb-2">Recommended Action</h3>
            {recommendation ? (
              <>
                <p className="text-body-md text-on-surface-variant mb-6">{recommendation}</p>
                <div className="bg-surface shadow-injected p-4 mb-6 border-l-4 border-secondary">
                  <h4 className="text-label-md font-bold text-on-background">Next step</h4>
                  <p className="text-body-md text-secondary mt-1">
                    {states.find((s) => s.state === "NEEDS_REVIEW" || s.state === "DEVELOPING")?.concept_name ?? "Continue studying"}
                  </p>
                </div>
              </>
            ) : (
              <p className="text-body-md text-on-surface-variant mb-6">
                ARIA will adapt Study when the evidence supports a useful change.
              </p>
            )}
          </div>
          <Link
            href="/app/learn"
            className="w-full bg-secondary text-on-secondary text-label-md font-bold py-4 rounded-full shadow-extruded btn-extruded flex items-center justify-center gap-2"
          >
            Begin Session
            <span className="material-symbols-outlined">arrow_forward</span>
          </Link>
        </div>
      </div>

      {/* Evidence log */}
      <div className="bg-surface rounded-3xl p-6 md:p-8 shadow-extruded">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-headline-md text-on-background">Evidence Log</h3>
          <span className="text-label-sm text-on-surface-variant">{evidence.length} item{evidence.length === 1 ? "" : "s"}</span>
        </div>
        {evidence.length === 0 ? (
          <p className="text-body-md text-on-surface-variant">No learning signal yet. Complete an assessment to give ARIA evidence to work with.</p>
        ) : (
          <div className="flex flex-col gap-4">
            {evidence.map((item) => {
              const isCorrect = item.signal === "CORRECT" && item.valid;
              return (
                <div key={item.id} className="bg-surface shadow-injected p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${isCorrect ? "bg-tertiary/10 text-tertiary" : "bg-surface-container-high text-surface-tint"} shadow-extruded-sm`}>
                      <span className="material-symbols-outlined ms-fill">{isCorrect ? "check_circle" : "lightbulb"}</span>
                    </div>
                    <div>
                      <p className="text-body-md text-on-background">
                        {item.concept_name} — {isCorrect ? "answered correctly" : item.valid ? "incorrect (review)" : "challenged result"}
                      </p>
                      <p className="text-label-sm text-on-surface-variant mt-1">{new Date(item.created_at).toLocaleString()}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-3 py-1 rounded-full text-label-sm font-semibold ${
                        isCorrect
                          ? "bg-tertiary-container/30 border border-tertiary/20 text-tertiary"
                          : item.valid
                            ? "bg-surface-container-high border border-outline-variant text-surface-tint"
                            : "bg-surface-variant text-on-surface-variant"
                      }`}
                    >
                      {isCorrect ? "Strong Evidence" : item.valid ? "Growth Area" : "Challenged"}
                    </span>
                    {item.valid && (
                      <button
                        onClick={() => void invalidate(item.id, context.id)}
                        className="px-3 py-1 rounded-full text-label-sm text-error hover:underline"
                      >
                        This result looks wrong
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {error && <p className="text-label-md text-error" role="alert">{error}</p>}
    </div>
  );
}
