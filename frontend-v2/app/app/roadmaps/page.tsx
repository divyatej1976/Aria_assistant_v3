"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icons";
import { api, ApiError } from "@/lib/api";
import { useActiveContext } from "@/components/use-active-context";
import { buildRoadmap, tickExplanation, type Roadmap, type RoadmapTopic } from "@/lib/roadmap";
import { toast } from "@/lib/toast";
import { ErrorState, Loading } from "@/components/states";

type ConceptState = {
  concept_id: string;
  concept_name: string;
  state: string;
  confidence: number;
  reason: string;
};
type Preference = { key: string; value: string };
type Prereq = { prerequisite_concept_id: string };

const LEVELS = ["Beginner", "Intermediate", "Advanced"];
const PREF_GOAL = "roadmap_goal";
const PREF_LEVEL = "roadmap_level";
const PREF_TARGET = "roadmap_target";

export default function RoadmapsPage() {
  const { context } = useActiveContext();
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [open, setOpen] = useState(false);
  const [goal, setGoal] = useState("");
  const [level, setLevel] = useState("Beginner");
  const [targetDate, setTargetDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [openTiers, setOpenTiers] = useState<Record<string, boolean>>({});
  const [selected, setSelected] = useState<RoadmapTopic | null>(null);

  const load = useCallback(async (cid: string) => {
    const [prefs, adaptation] = await Promise.all([
      api<Preference[]>("/api/v1/me/preferences"),
      api<{ states: ConceptState[] }>(`/api/v1/contexts/${cid}/adaptation`),
    ]);
    const goalPref = prefs.find((p) => p.key === PREF_GOAL)?.value;
    const levelPref = prefs.find((p) => p.key === PREF_LEVEL)?.value ?? "Beginner";
    const targetPref = prefs.find((p) => p.key === PREF_TARGET)?.value;

    if (!goalPref) {
      setRoadmap(null);
      return;
    }

    const concepts = await api<{ id: string; name: string }[]>(`/api/v1/contexts/${cid}/concepts`);
    const prerequisiteMap: Record<string, string[]> = {};
    await Promise.all(
      concepts.map(async (c) => {
        try {
          const prereqs = await api<Prereq[]>(`/api/v1/contexts/${cid}/concepts/${c.id}/prerequisites`);
          prerequisiteMap[c.id] = prereqs.map((p) => p.prerequisite_concept_id);
        } catch {
          prerequisiteMap[c.id] = [];
        }
      }),
    );

    const built = buildRoadmap({
      goal: goalPref,
      level: levelPref,
      targetDate: targetPref || undefined,
      states: adaptation.states,
      prerequisites: prerequisiteMap,
    });
    setRoadmap(built);
    if (built) setOpenTiers((o) => ({ ...o, [built.tiers[0]?.name ?? ""]: true }));
  }, []);

  useEffect(() => {
    if (!context) return;
    let cancelled = false;
    (async () => {
      try {
        await load(context.id);
      } catch {
        if (!cancelled) setFailed(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [context, load]);

  const create = async () => {
    if (!context) return;
    if (!goal.trim()) {
      toast("Please enter a learning goal.");
      return;
    }
    setBusy(true);
    try {
      await Promise.all([
        api<Preference>("/api/v1/me/preferences", {
          method: "PUT",
          body: JSON.stringify({ key: PREF_GOAL, value: goal.trim() }),
        }),
        api<Preference>("/api/v1/me/preferences", {
          method: "PUT",
          body: JSON.stringify({ key: PREF_LEVEL, value: level }),
        }),
        targetDate
          ? api<Preference>("/api/v1/me/preferences", {
              method: "PUT",
              body: JSON.stringify({ key: PREF_TARGET, value: targetDate }),
            })
          : Promise.resolve(),
      ]);
      setOpen(false);
      toast("Roadmap created.");
      await load(context.id);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Could not create the roadmap.");
    } finally {
      setBusy(false);
    }
  };

  const remainingPct = roadmap && roadmap.total ? Math.round((roadmap.done / roadmap.total) * 100) : 0;

  if (loading) {
    return <Loading label="your roadmap" />;
  }
  if (failed) {
    return <ErrorState message="This screen could not be loaded." onRetry={() => window.location.reload()} />;
  }

  return (
    <div>
      <div className="section-head">
        <div>
          <h1 className="pg-title">Roadmaps</h1>
          <p className="pg-sub">Your path from where you are to where you want to be — topics auto-complete as you learn them.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setOpen(true)}>
          <Icon name="route" /> Create Roadmap
        </button>
      </div>

      {roadmap === null ? (
        <div className="empty-state">
          <Icon name="route" size={30} />
          <p style={{ margin: "10px 0 14px", fontSize: 14, color: "var(--text-1)" }}>
            No roadmap yet. Set a learning goal and ARIA will build a tiered path from the concepts in your context.
          </p>
          <button className="btn btn-primary" onClick={() => setOpen(true)} style={{ justifyContent: "center" }}>
            <Icon name="route" /> Create Roadmap
          </button>
        </div>
      ) : selected ? (
        <div className="card card-pad" style={{ maxWidth: 720 }}>
          <button className="btn btn-ghost mb-2" onClick={() => setSelected(null)}>
            <Icon name="back" /> All topics
          </button>
          <h2 style={{ fontSize: 24, fontWeight: 800, marginBottom: 4 }}>{selected.title}</h2>
          <div style={{ fontSize: 13, color: "var(--text-3)", marginBottom: 16 }}>
            {roadmap.goal} · {roadmap.level}
          </div>

          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 18 }}>
            <span className={`tag-chip${selected.ticked ? " tag-chip-selected" : ""}`}>
              {selected.ticked ? "Ticked" : selected.state}
            </span>
            <span className="tag-chip">{selected.confidence}% confidence</span>
            {selected.prereqNames.length > 0 && (
              <span className="tag-chip">Prerequisites: {selected.prereqNames.join(", ")}</span>
            )}
          </div>

          <div className="banner" style={{ margin: 0 }}>
            <span style={{ color: "var(--accent)", display: "inline-flex" }}><Icon name="sparkles" size={20} /></span>
            <div>
              <b>Why this tick state?</b>
              <p style={{ marginTop: 2 }}>{tickExplanation(selected)}</p>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-start", gap: 10, marginTop: 18 }}>
            <Link href="/app/learn" className="btn btn-primary" style={{ justifyContent: "center" }}>
              <Icon name="message" /> Study this
            </Link>
          </div>
        </div>
      ) : (
        <>
          <div style={{ maxWidth: 200, margin: "0 auto 22px", textAlign: "center" }}>
            <div className="ring" style={{ "--p": remainingPct, "--r": "42px" } as React.CSSProperties}>
              <span className="r-n" style={{ color: "var(--accent)" }}>{remainingPct}%</span>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-2)", marginTop: 10, fontWeight: 700 }}>
              {roadmap.goal} · {roadmap.done} / {roadmap.total} done
            </div>
          </div>

          {roadmap.tiers.map((tier) => (
            <div key={tier.name} style={{ marginBottom: 14 }}>
              <button
                type="button"
                className="ws-row"
                onClick={() => setOpenTiers((o) => ({ ...o, [tier.name]: !o[tier.name] }))}
                style={{ justifyContent: "flex-start", gap: 10, width: "100%", textAlign: "left", background: "none", border: "none", cursor: "pointer", color: "inherit", padding: "10px 12px" }}
                aria-expanded={!!openTiers[tier.name]}
                aria-controls={`tier-${tier.name}`}
              >
                <Icon name={tier.icon} size={16} />
                <b style={{ flex: 1 }}>{tier.name}</b>
                <span style={{ fontSize: 11, color: "var(--text-3)" }}>
                  {tier.topics.filter((t) => t.ticked).length}/{tier.topics.length}
                </span>
              </button>
              {openTiers[tier.name] && (
                <div id={`tier-${tier.name}`} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 12, paddingLeft: 8 }}>
                  {tier.topics.map((topic) => (
                    <button
                      type="button"
                      className="card card-pad card-hover"
                      key={topic.key}
                      style={{ padding: 16, cursor: "pointer", textAlign: "left", background: "var(--card-bg, var(--bg-2))", border: "1px solid var(--border)" }}
                      onClick={() => setSelected(topic)}
                      aria-label={`View ${topic.title} details`}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <b style={{ fontSize: 13.5 }}>{topic.title}</b>
                        <span
                          style={{
                            width: 9,
                            height: 9,
                            borderRadius: "50%",
                            background: topic.ticked ? "var(--success)" : "var(--bg-4)",
                            boxShadow: topic.ticked ? "0 0 8px var(--success)" : undefined,
                          }}
                        />
                      </div>
                      <div className="bar" style={{ height: 5, marginTop: 10 }}>
                        <i style={{ width: `${Math.min(100, topic.confidence)}%` }} />
                      </div>
                      <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 6 }}>
                        {topic.ticked ? "Completed" : `${topic.state} · auto-tracked`}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}

          <p style={{ fontSize: 12, color: "var(--text-3)", marginTop: 18 }}>
            <Icon name="sparkles" size={13} /> Topics tick automatically as concepts reach &quot;Supported&quot; in your Knowledge Map.
          </p>
        </>
      )}

      {/* create modal */}
      <div className="modal-bg show" style={{ display: open ? "flex" : "none" }}>
        <div className="modal">
          <div className="m-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: 14, marginBottom: 18 }}>
            <h3 className="m-title" style={{ fontSize: 20, fontWeight: 800 }}><Icon name="route" size={20} /> Create Roadmap</h3>
            <button className="btn btn-ghost" style={{ padding: 6 }} onClick={() => setOpen(false)} aria-label="Close"><Icon name="x" size={16} /></button>
          </div>
          <div className="form-group">
            <label className="field-label" htmlFor="roadmap-goal">Learning Goal</label>
            <input id="roadmap-goal" className="input" value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="Master Python for data analysis" />
          </div>
          <div className="form-group">
            <label className="field-label">Level</label>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {LEVELS.map((l) => (
                <button
                  type="button"
                  key={l}
                  className={`tag-chip${level === l ? " tag-chip-selected" : ""}`}
                  onClick={() => setLevel(l)}
                  style={{ border: "none", background: "none", cursor: "pointer" }}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
          <div className="form-group">
            <label className="field-label" htmlFor="roadmap-target">Target Date (optional)</label>
            <input id="roadmap-target" type="date" className="input" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} />
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, borderTop: "1px solid var(--border)", paddingTop: 18, marginTop: 16 }}>
            <button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={create} disabled={busy}>
              Create Roadmap <Icon name="arrow" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}