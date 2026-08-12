"use client";

import { useEffect, useState } from "react";

import { api } from "../lib/api";

type ConceptState = {
  concept_id: string;
  concept_name: string;
  state: string;
  confidence: number;
  reason: string;
};

type Decision = { concept_id: string | null; decision_type: string; reason: string };

function nodeStyle(state: string): { ring: string; icon: string; iconColor: string; progress: string } {
  switch (state) {
    case "SUPPORTED":
      return { ring: "border-2 border-tertiary opacity-60", icon: "check_circle", iconColor: "text-tertiary", progress: "bg-tertiary" };
    case "NEEDS_REVIEW":
      return { ring: "border-2 border-error opacity-40", icon: "warning", iconColor: "text-error", progress: "bg-error" };
    case "DEVELOPING":
      return { ring: "", icon: "memory", iconColor: "text-secondary", progress: "bg-secondary" };
    default:
      return { ring: "", icon: "radio_button_unchecked", iconColor: "text-on-surface-variant", progress: "bg-outline" };
  }
}

export function MapView({ contextId, contextTitle }: { contextId: string; contextTitle: string }) {
  const [states, setStates] = useState<ConceptState[]>([]);
  const [insight, setInsight] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ states: ConceptState[]; decisions: Decision[] }>(`/api/v1/contexts/${contextId}/adaptation`)
      .then((summary) => {
        setStates(summary.states);
        const focus = summary.decisions.find((d) => d.decision_type === "FOCUS_STUDY");
        setInsight(focus?.reason ?? "");
      })
      .catch((requestError: unknown) =>
        setError(requestError instanceof Error ? requestError.message : "Unable to load knowledge map")
      );
  }, [contextId]);

  const count = states.length;
  const radius = 32;

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-7rem)] overflow-hidden">
      {/* Canvas */}
      <div className="flex-grow relative overflow-auto lg:overflow-hidden bg-grid">
        <h2 className="text-headline-lg text-on-surface absolute top-6 left-6 z-10 pointer-events-none">Neural Topology Map</h2>
        {count === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-body-md text-on-surface-variant max-w-sm text-center px-6">
              No concepts yet. Add material and generate an assessment so ARIA can discover and track concepts.
            </p>
          </div>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center min-w-[720px] min-h-[520px]">
            <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
              {states.map((state, index) => {
                const angle = (index / count) * Math.PI * 2 - Math.PI / 2;
                const x1 = 50;
                const y1 = 50;
                const x2 = 50 + radius * Math.cos(angle);
                const y2 = 50 + radius * Math.sin(angle);
                return <line key={state.concept_id} x1={`${x1}%`} y1={`${y1}%`} x2={`${x2}%`} y2={`${y2}%`} stroke="#d4dbe2" strokeWidth="2" />;
              })}
            </svg>
            {/* Central node */}
            <div
              className="absolute w-32 h-32 rounded-full bg-surface shadow-extruded flex flex-col items-center justify-center cursor-pointer hover:scale-105 transition-transform z-10"
              style={{ top: "50%", left: "50%", transform: "translate(-50%, -50%)" }}
            >
              <span className="material-symbols-outlined text-secondary text-4xl mb-1 ms-fill">hub</span>
              <span className="text-label-md text-on-surface text-center px-2">{contextTitle}</span>
            </div>
            {/* Satellite nodes */}
            {states.map((state, index) => {
              const angle = (index / count) * Math.PI * 2 - Math.PI / 2;
              const style = nodeStyle(state.state);
              return (
                <div
                  key={state.concept_id}
                  className="absolute w-24 h-24 rounded-full bg-surface shadow-extruded flex flex-col items-center justify-center cursor-pointer hover:scale-105 transition-transform z-10"
                  style={{
                    top: `${50 + radius * Math.sin(angle)}%`,
                    left: `${50 + radius * Math.cos(angle)}%`,
                    transform: "translate(-50%, -50%)",
                  }}
                >
                  <div className={`absolute inset-0 rounded-full ${style.ring}`}></div>
                  <span className={`material-symbols-outlined text-2xl mb-1 ${style.iconColor} ${state.state === "SUPPORTED" ? "ms-fill" : ""}`}>{style.icon}</span>
                  <span className="text-label-sm text-on-surface text-center px-1 leading-tight">{state.concept_name}</span>
                  {state.state === "DEVELOPING" && (
                    <div className="w-10 h-1 mt-1 bg-surface shadow-injected rounded-full overflow-hidden">
                      <div className={`h-full ${style.progress}`} style={{ width: `${state.confidence}%` }}></div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Conceptual mastery sidebar */}
      <aside className="w-full lg:w-80 bg-surface border-t lg:border-l border-outline-variant p-6 flex flex-col gap-6 overflow-y-auto shrink-0">
        <div>
          <h3 className="text-headline-md text-on-surface mb-1">Conceptual Mastery</h3>
          <p className="text-body-md text-on-surface-variant">Your current learning topology.</p>
        </div>
        {insight && (
          <div className="bg-surface shadow-extruded rounded-xl p-5 border-l-4 border-secondary">
            <div className="flex items-center gap-2 mb-2">
              <span className="material-symbols-outlined text-secondary ms-fill">psychology</span>
              <h4 className="text-label-md text-secondary">AI Insight</h4>
            </div>
            <p className="text-body-md text-on-surface">{insight}</p>
          </div>
        )}
        <div className="flex flex-col gap-4 mt-2">
          {states.map((state) => {
            const style = nodeStyle(state.state);
            const percent = Math.min(100, Math.max(0, state.confidence));
            return (
              <div key={state.concept_id}>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-label-md text-on-surface">{state.concept_name}</span>
                  <span className={`text-label-sm font-bold ${style.iconColor}`}>{percent}%</span>
                </div>
                <div className="w-full h-3 bg-surface shadow-injected rounded-full overflow-hidden">
                  <div className={`h-full ${style.progress} rounded-full`} style={{ width: `${percent}%` }}></div>
                </div>
              </div>
            );
          })}
          {count === 0 && <p className="text-body-md text-on-surface-variant">No concepts to show yet.</p>}
        </div>
        {error && <p className="text-label-md text-error" role="alert">{error}</p>}
      </aside>
    </div>
  );
}
